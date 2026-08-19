"""라오어 무한매수법 V4.0 계산 엔진.

공개 중계표(TQQQ 20/40분할, SOXL 20/40분할의 8/18·8/19 두 회차)에서
역산해 검증한 규칙:

    별% (star_pct)   = 지정가매도율 x (1 - T / (분할수/2))
    1회매수금액 (u)  = 잔금 / (분할수 - T)
    별지점            = 매수평단 x (1 + 별%)
    지정가매도        = 매수평단 x (1 + 지정가매도율)
    큰수              = 직전종가 x 1.12
    상단 줄 가격      = min(별지점 - 0.01, 큰수)

매수 (전부 LOC)

    평단이 상단 줄보다 싸면 두 줄로 나눈다 (예산 절반씩):
        상단 줄  floor((u/2) / 상단가격) 주
        평단 줄  floor(u / 직전종가) - 상단 줄 수량
    평단이 상단 줄보다 비싸면 (후반전이거나 급락 직후) 평단 줄이 사라지고
    예산 전부가 상단 줄로 간다:
        상단 줄  floor(u / 상단가격) 주
    그 아래로 u/k (k = 총수량+1, +2, ...) 가격에 1주씩 사다리를 건다.

매도 (전·후반 공통)

    보유수량의 1/4 (내림) 을 별지점에 LOC 매도, 나머지 전량을 지정가 매도.

회차 T 는 체결 '금액' 이 아니라 체결된 '줄' 로 센다. 두 줄인 날은 한 줄당
0.5, 상단 줄 하나뿐인 날은 1.0. 사다리 체결은 회차를 올리지 않는다
(같은 예산으로 더 많은 수량을 사는 것이므로). 이 규칙은 8/18 -> 8/19
전이 4건에서 ΔT 가 정확히 0.500 / 1.000 으로 나오는 것으로 확인했다.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

BIG_NUMBER_RATIO = 1.12  # 큰수 = 직전종가 * 1.12
LADDER_FLOOR_RATIO = 0.80  # "대충 직전종가 대비 -20% 지점까지 걸면 됩니다"
LADDER_EXTRA_RUNGS = 3  # -20% 아래로 참고용 몇 칸 더
SELL_LOC_DIVISOR = 4  # 보유수량의 1/4 을 별지점 LOC 매도


def round2(value: float) -> float:
    """호가 반올림 (소수 둘째자리)."""
    return math.floor(value * 100 + 0.5) / 100


def floor2(value: float) -> float:
    """호가 내림 (소수 둘째자리)."""
    return math.floor(value * 100) / 100


def ladder_price(budget: float, count: int) -> float:
    """1회매수금액으로 count 개를 살 수 있는 가격 (센트 단위 내림).

    중계표에 딱 떨어지는 값이 1센트 낮게 찍힌 경우가 있는데, 그건 표에
    표시된 1회매수금액이 반올림된 값이라 생긴 착시다. 정확한 예산으로
    계산하면 단순 내림이 맞다 (8/19 표의 655.68/6=109.28, 548.92/9=60.99).
    """
    return floor2(budget / count)


@dataclass
class Order:
    kind: str  # 'LOC매수' | 'LOC매도' | '지정가매도'
    price: float
    qty: int
    note: str = ""


@dataclass
class Plan:
    ticker: str
    close: float
    close_date: str
    splits: int
    progress: float  # 현재 회차 T
    star_pct: float  # 별% (소수, 0.0875 = 8.75%)
    unit_budget: float  # 1회매수금액
    avg_price: float
    shares: int
    cash: float
    star_price: float
    limit_price: float
    big_number: float
    first_half: bool
    upper_price: float = 0.0  # 상단 매수 줄 가격
    two_line: bool = True  # 평단 줄이 살아 있는가
    buys: list[Order] = field(default_factory=list)
    sells: list[Order] = field(default_factory=list)

    @property
    def eval_pnl_pct(self) -> float:
        if not self.shares or not self.avg_price:
            return 0.0
        return (self.close / self.avg_price - 1) * 100

    def expected_buy_qty(self, close: float) -> int:
        """종가가 close 로 마감했을 때 체결됐어야 할 매수 수량."""
        return sum(o.qty for o in self.buys if close <= o.price)

    def buy_progress(self, close: float) -> float:
        """그날 매수로 늘어나는 회차."""
        if self.two_line:
            return 0.5 * (close <= self.upper_price) + 0.5 * (
                close <= round2(self.avg_price)
            )
        return 1.0 * (close <= self.upper_price)


@dataclass
class Position:
    """한 사이클의 상태."""

    ticker: str = "TQQQ"
    splits: int = 40
    limit_sell_pct: float = 0.15  # TQQQ 15%, SOXL 20%
    cycle: int = 1
    cycle_start_cash: float = 10_000.0
    cash: float = 10_000.0
    shares: int = 0
    cost_basis: float = 0.0  # 보유분 매수원금 총액
    progress: float = 0.0  # 현재 회차 T
    realized_total: float = 0.0  # 시즌 누적 실현손익

    @property
    def avg_price(self) -> float:
        return self.cost_basis / self.shares if self.shares else 0.0

    @property
    def unit_budget(self) -> float:
        """1회매수금액 = 잔금 / 남은 회차."""
        remaining = self.splits - self.progress
        if remaining <= 0:
            return 0.0
        return self.cash / remaining

    @property
    def star_pct(self) -> float:
        """별% — 전반전이면 +, 후반전이면 -."""
        return self.limit_sell_pct * (1 - self.progress / (self.splits / 2))

    @property
    def first_half(self) -> bool:
        return self.progress < self.splits / 2

    def plan(
        self, close: float, close_date: str = "", ladder_rungs: int | None = None
    ) -> Plan:
        """직전 종가를 받아 오늘 걸 주문표를 만든다.

        ladder_rungs 를 주면 사다리를 정확히 그만큼 만든다.
        기본값은 직전종가 -20% 지점까지 + 참고용 몇 칸.
        """
        unit = self.unit_budget
        avg = self.avg_price
        big = floor2(close * BIG_NUMBER_RATIO)
        star_price = round2(avg * (1 + self.star_pct)) if avg else 0.0
        limit_price = round2(avg * (1 + self.limit_sell_pct)) if avg else 0.0
        upper = min(round2(star_price - 0.01), big) if avg else big

        plan = Plan(
            ticker=self.ticker,
            close=close,
            close_date=close_date,
            splits=self.splits,
            progress=self.progress,
            star_pct=self.star_pct,
            unit_budget=unit,
            avg_price=avg,
            shares=self.shares,
            cash=self.cash,
            star_price=star_price,
            limit_price=limit_price,
            big_number=big,
            first_half=self.first_half,
            upper_price=upper,
            two_line=bool(self.shares) and 0 < round2(avg) < upper,
        )

        if plan.two_line:
            n_total = int(unit // close) if close > 0 else 0
            n_upper = int((unit / 2) // upper)
            n_lower = max(n_total - n_upper, 0)
            label = "별지점-0.01" if upper < big else "큰수"
            if n_upper:
                plan.buys.append(Order("LOC매수", upper, n_upper, label))
            if n_lower:
                plan.buys.append(Order("LOC매수", round2(avg), n_lower, "매수평단"))
            n = n_upper + n_lower
        else:
            n = int(unit // upper) if upper > 0 else 0
            if n:
                note = "큰수 (첫 매수)" if not self.shares else "별지점-0.01 or 큰수"
                plan.buys.append(Order("LOC매수", upper, n, note))

        # 큰수 사다리: 1회매수금액/k 가격에 1개씩
        must_floor = close * LADDER_FLOOR_RATIO
        optional = 0
        k = n + 1
        while unit > 0:
            price = ladder_price(unit, k)
            if price <= 0:
                break
            if ladder_rungs is None:
                if price < must_floor:
                    optional += 1
                    if optional > LADDER_EXTRA_RUNGS:
                        break
                    note = f"사다리 1/{k} (-20% 아래, 선택)"
                else:
                    note = f"사다리 1/{k}"
            else:
                if k - n > ladder_rungs:
                    break
                note = f"사다리 1/{k}" if price >= must_floor else f"사다리 1/{k} (선택)"
            plan.buys.append(Order("LOC매수", price, 1, note))
            k += 1

        if self.shares:
            loc_qty = self.shares // SELL_LOC_DIVISOR
            limit_qty = self.shares - loc_qty
            if loc_qty:
                plan.sells.append(Order("LOC매도", star_price, loc_qty, "별지점 (보유 1/4)"))
            if limit_qty:
                pct = int(round(self.limit_sell_pct * 100))
                plan.sells.append(Order("지정가매도", limit_price, limit_qty, f"평단 +{pct}%"))

        return plan

    # ------------------------------------------------------------------
    # 체결 반영
    # ------------------------------------------------------------------
    def apply_fills(
        self,
        close: float,
        bought: int = 0,
        sold_loc: int = 0,
        sold_limit: int = 0,
        limit_price: float | None = None,
        prev_close: float | None = None,
    ) -> dict:
        """그날 실제 체결을 반영해 상태를 갱신한다.

        LOC 매수/매도는 종가에, 지정가 매도는 지정가에 체결된다.
        prev_close (그날 주문표를 뽑은 기준 종가) 를 주면 회차를 중계표와
        같은 방식으로 세고, 체결 수량이 계획과 맞는지도 대조한다.
        """
        unit = self.unit_budget
        avg_before = self.avg_price
        realized = 0.0
        mismatch = None

        if sold_loc + sold_limit > self.shares:
            raise ValueError("매도 수량이 보유 수량보다 많습니다")

        plan = self.plan(prev_close) if prev_close else None
        if plan:
            expected = plan.expected_buy_qty(close)
            if expected != bought:
                mismatch = f"계획상 {expected}주 / 신고 {bought}주"

        if bought:
            amount = bought * close
            self.cash -= amount
            self.cost_basis += amount
            self.shares += bought
            if plan:
                self.progress += plan.buy_progress(close)
            elif unit:
                self.progress += amount / unit

        for qty, price in ((sold_loc, close), (sold_limit, limit_price or 0.0)):
            if not qty:
                continue
            if not price:
                raise ValueError("지정가 매도 체결가를 알려주세요 (--limit-price)")
            cost = qty * avg_before
            self.cash += qty * price
            self.cost_basis -= cost
            self.shares -= qty
            realized += qty * (price - avg_before)
            if unit:
                # 매도쪽 되감기는 공개 표에 매도가 찍힌 날이 아직 없어 미검증이다.
                # 1회차 = 1회매수금액 이라는 정의에 맞춰 원가 기준으로 되돌린다.
                self.progress -= cost / unit

        if self.shares == 0:
            self.cost_basis = 0.0
        self.progress = max(self.progress, 0.0)
        self.realized_total += realized

        cycle_closed = self.shares == 0 and bought == 0 and (sold_loc or sold_limit)
        return {
            "realized": realized,
            "cycle_closed": bool(cycle_closed),
            "mismatch": mismatch,
        }

    def start_new_cycle(self) -> None:
        """보유 0 이 되면 잔금 전액으로 새 사이클을 시작한다 (복리)."""
        if self.shares:
            raise ValueError("보유 수량이 남아 있으면 새 사이클을 시작할 수 없습니다")
        self.cycle += 1
        self.cycle_start_cash = self.cash
        self.cost_basis = 0.0
        self.progress = 0.0
