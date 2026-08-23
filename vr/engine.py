"""라오어 VR (Value Rebalancing) 적립식 계산 엔진.

공개된 VR 7기 1주차 자료에서 확인한 규칙:

                        Pool     (E - V1)
    V2  =  V1  +  ------  +  ----------  ±  적립금
                          G       2 * sqrt(G)

    최소값 = V2 x (1 - 밴드)      최대값 = V2 x (1 + 밴드)

주문표 (한 칸에 1주씩, 지정가)

    매수점 = 최소값 / 보유개수      살수록 보유개수가 늘어 다음 매수점이 낮아진다
    매도점 = 최대값 / 보유개수      팔수록 보유개수가 줄어 다음 매도점이 높아진다

    그 가격이 되면 보유 평가금이 정확히 밴드 끝에 닿는다. 한 주 사고팔아
    평가금을 밴드 안으로 되돌리는 것이 VR 의 리밸런싱이다.
    매수 사다리는 Pool 이 감당하는 데까지만 건다.

    V       목표 평가금 (Value). 계좌가 이 금액이 되도록 리밸런싱한다.
    E       직전 사이클 마지막 평가금
    Pool    직전 사이클 마지막 예수금 (적립금을 더하기 전 값)
    G       분모 상수. VR 7기는 10
    적립금   적립식이면 +, 인출식이면 -
    밴드     ±15%. 평가금이 최소값 아래면 매수, 최대값 위면 매도

N 배수로 굴리면 개수도 예수금도 적립금도 전부 N 배가 된다.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

DEFAULT_G = 10.0
DEFAULT_BAND = 0.15


def round2(value: float) -> float:
    return math.floor(value * 100 + 0.5) / 100


@dataclass
class Rung:
    """주문표 한 칸."""

    price: float
    qty: int  # 매수 +1, 매도 -1
    shares_after: int
    pool_after: float
    affordable: bool = True


@dataclass
class Cycle:
    """한 사이클(2주)의 계산 결과."""

    week: int
    V: float
    low: float  # 최소값
    high: float  # 최대값
    pool_start: float  # 적립금을 더한 뒤의 Pool
    contribution: float


@dataclass
class VRAccount:
    ticker: str = "TQQQ"
    multiplier: float = 1.0  # N 배수
    G: float = DEFAULT_G
    band: float = DEFAULT_BAND
    base_contribution: float = 100.0  # 1배 기준 2주당 적립금
    week: int = 0
    V: float = 0.0  # 직전 V
    pool: float = 0.0  # 마지막 Pool (적립금 더하기 전)
    shares: int = 0
    total_invested: float = 0.0
    log: list = field(default_factory=list)

    @property
    def contribution(self) -> float:
        return self.base_contribution * self.multiplier

    def value(self, price: float) -> float:
        """현재 주가 기준 보유 평가금."""
        return self.shares * price

    def next_cycle(self, last_price: float) -> Cycle:
        """직전 사이클 종가를 받아 다음 사이클의 V 와 밴드를 계산한다."""
        E = self.value(last_price)
        V2 = self.V + self.pool / self.G + (E - self.V) / (2 * math.sqrt(self.G))
        V2 += self.contribution
        # 밴드는 반올림한 V 에서 계산한다 (174.05 x 0.85 = 147.94 로 자료와 일치.
        # 반올림 전 174.053 을 쓰면 147.95 가 나와 1센트 어긋난다)
        V2 = round2(V2)
        return Cycle(
            week=self.week + 1,
            V=V2,
            low=round2(V2 * (1 - self.band)),
            high=round2(V2 * (1 + self.band)),
            pool_start=round2(self.pool + self.contribution),
            contribution=self.contribution,
        )

    def buy_ladder(self, low: float, max_rungs: int = 8) -> list[Rung]:
        """매수 주문표. 매수점 = 최소값 / 보유개수, 한 칸에 1주."""
        rungs: list[Rung] = []
        n, pool = self.shares, self.pool
        while n > 0 and len(rungs) < max_rungs:
            price = round2(low / n)
            if price > pool:
                break
            pool = round2(pool - price)
            n += 1
            rungs.append(Rung(price=price, qty=1, shares_after=n, pool_after=pool))
        return rungs

    def next_buy_price(self, low: float) -> float:
        """Pool 이 모자라 못 거는 경우까지 포함한 다음 매수점."""
        return round2(low / self.shares) if self.shares else 0.0

    def sell_ladder(self, high: float, max_rungs: int = 8) -> list[Rung]:
        """매도 주문표. 매도점 = 최대값 / 보유개수, 한 칸에 1주."""
        rungs: list[Rung] = []
        n, pool = self.shares, self.pool
        while n > 0 and len(rungs) < max_rungs:
            price = round2(high / n)
            pool = round2(pool + price)
            n -= 1
            rungs.append(Rung(price=price, qty=-1, shares_after=n, pool_after=pool))
        return rungs

    def apply_cycle(self, cycle: Cycle, last_price: float) -> None:
        """사이클을 확정한다. V 와 Pool 을 넘기고 주차를 올린다."""
        self.V = cycle.V
        self.pool = cycle.pool_start
        self.week = cycle.week
        self.total_invested += cycle.contribution
        self.log.append(
            {"week": cycle.week, "V": cycle.V, "low": cycle.low, "high": cycle.high,
             "pool": cycle.pool_start, "price": last_price, "shares": self.shares}
        )

    def trade(self, price: float, qty: int) -> None:
        """매수(+) / 매도(-) 체결을 Pool 에 반영한다."""
        if qty < 0 and -qty > self.shares:
            raise ValueError("매도 수량이 보유 수량보다 많습니다")
        cost = qty * price
        if cost > self.pool + 1e-9:
            raise ValueError(f"Pool 부족: 필요 ${cost:,.2f} / 보유 ${self.pool:,.2f}")
        self.pool = round2(self.pool - cost)
        self.shares += qty
