"""라오어 무한매수법 V4.0 계산 엔진.

공개된 중계표(TQQQ 20/40분할, SOXL 20/40분할)에서 역산해 검증한 규칙:

    별% (star_pct)   = 지정가매도율 x (1 - T / (분할수/2))
    1회매수금액 (u)  = 잔금 / (분할수 - T)
    별지점            = 매수평단 x (1 + 별%)
    지정가매도        = 매수평단 x (1 + 지정가매도율)
    큰수              = 직전종가 x 1.12
    당일 매수 개수 n  = floor(1회매수금액 / 직전종가)
        - 별지점 -0.01 (또는 큰수, 둘 중 낮은 값) 에 floor(n/2) 개 LOC 매수
        - 매수평단에 ceil(n/2) 개 LOC 매수
        - 1회매수금액/k (k = n+1, n+2, ...) 가격에 1개씩 LOC 매수 (큰수 사다리)
    매도  - 보유수량의 1/4 (내림) 을 별지점에 LOC 매도
          - 나머지 전량을 지정가매도

T 는 진행 회차. 매수하면 (체결금액 / 그날의 1회매수금액) 만큼 늘고,
매도하면 (매도수량 x 매수평단 / 그날의 1회매수금액) 만큼 줄어든다.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

BIG_NUMBER_RATIO = 1.12  # 큰수 = 직전종가 * 1.12
LADDER_FLOOR_RATIO = 0.80  # "대충 직전종가 대비 -20% 지점까지 걸면 됩니다"
LADDER_EXTRA_RUNGS = 3  # -20% 아래로 참고용 몇 칸 더


def round2(value: float) -> float:
    """호가 반올림 (소수 둘째자리)."""
    return math.floor(value * 100 + 0.5) / 100


def floor2(value: float) -> float:
    """호가 내림 (소수 둘째자리)."""
    return math.floor(value * 100) / 100


def ladder_price(budget: float, count: int) -> float:
    """1회매수금액으로 count 개를 살 수 있는 가격.

    딱 떨어지면 1센트 낮춘다 (그 가격에 체결돼도 예산을 넘지 않도록).
    """
    exact = budget / count
    price = floor2(exact)
    if abs(price - exact) < 1e-9:
        price = round2(price - 0.01)
    return price


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
    buys: list[Order] = field(default_factory=list)
    sells: list[Order] = field(default_factory=list)

    @property
    def eval_pnl_pct(self) -> float:
        if not self.shares or not self.avg_price:
            return 0.0
        return (self.close / self.avg_price - 1) * 100


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
        )

        n = int(unit // close) if close > 0 else 0
        if n:
            if not self.shares:
                # 첫날: 평단이 없으니 큰수에 1회분 전량
                plan.buys.append(Order("LOC매수", big, n, "큰수 (첫 매수)"))
            elif self.first_half:
                upper = min(round2(star_price - 0.01), big)
                upper_qty, lower_qty = n // 2, n - n // 2
                if upper_qty:
                    label = "별지점-0.01" if upper < big else "큰수"
                    plan.buys.append(Order("LOC매수", upper, upper_qty, label))
                plan.buys.append(Order("LOC매수", round2(avg), lower_qty, "매수평단"))
            else:
                # 후반전: 큰수 매수를 접고 전량 평단에 (평단을 낮추는 구간)
                plan.buys.append(Order("LOC매수", round2(avg), n, "매수평단 (후반전)"))

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
            loc_qty = self.shares // 4
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
    ) -> dict:
        """그날 실제 체결을 반영해 상태를 갱신한다.

        LOC 매수/매도는 종가에, 지정가 매도는 지정가에 체결된다.
        """
        unit = self.unit_budget
        avg_before = self.avg_price
        realized = 0.0

        if sold_loc + sold_limit > self.shares:
            raise ValueError("매도 수량이 보유 수량보다 많습니다")

        if bought:
            amount = bought * close
            self.cash -= amount
            self.cost_basis += amount
            self.shares += bought
            if unit:
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
                self.progress -= cost / unit

        if self.shares == 0:
            self.cost_basis = 0.0
        self.progress = max(self.progress, 0.0)
        self.realized_total += realized

        cycle_closed = self.shares == 0 and bought == 0 and (sold_loc or sold_limit)
        return {"realized": realized, "cycle_closed": bool(cycle_closed)}

    def start_new_cycle(self) -> None:
        """보유 0 이 되면 잔금 전액으로 새 사이클을 시작한다 (복리)."""
        if self.shares:
            raise ValueError("보유 수량이 남아 있으면 새 사이클을 시작할 수 없습니다")
        self.cycle += 1
        self.cycle_start_cash = self.cash
        self.cost_basis = 0.0
        self.progress = 0.0
