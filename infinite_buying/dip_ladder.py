"""직전 매수가 대비 일정 폭 하락할 때마다 사는 분할매수 사다리.

무한매수법과 달리 매도 규칙이 없다. 내려갈 때마다 정해진 금액을 넣어
평단을 낮추고, 반등을 기다리는 단순 전략이다.

    다음 매수가 = 마지막 매수가 x (1 - 하락폭)
    회당 금액   = 기본금액 + 증액 x (지금까지 채운 단계수)

체결가는 계획한 가격보다 낮을 수 있다 (갭하락). 그 경우 다음 단계는
계획가가 아니라 '실제 체결가' 기준으로 다시 잡는다.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from infinite_buying.strategy import floor2


@dataclass
class Rung:
    step: int
    price: float
    amount: float  # 배정 금액
    qty: int
    spend: float
    shares_after: int
    avg_after: float
    cash_after: float
    drop_from_start: float  # 시작 매수가 대비 하락률


@dataclass
class DipLadder:
    ticker: str = "SOXL"
    step_pct: float = 0.15  # 한 단계 하락폭
    base_amount: float = 500.0  # 1단계 매수금액
    increment: float = 250.0  # 단계마다 늘리는 금액
    cash: float = 0.0
    shares: int = 0
    cost_basis: float = 0.0
    last_buy_price: float = 0.0
    step: int = 0  # 지금까지 채운 단계 수
    log: list = field(default_factory=list)

    @property
    def avg_price(self) -> float:
        return self.cost_basis / self.shares if self.shares else 0.0

    def amount_for(self, step: int) -> float:
        """step 단계(1부터)에 배정할 금액."""
        return self.base_amount + self.increment * (step - 1)

    def plan(self, max_steps: int = 8) -> list[Rung]:
        """남은 잔금으로 채울 수 있는 다음 매수 지점들."""
        rungs: list[Rung] = []
        price = self.last_buy_price
        shares, cost, cash = self.shares, self.cost_basis, self.cash
        start = self.last_buy_price
        for i in range(1, max_steps + 1):
            step = self.step + i
            price = floor2(price * (1 - self.step_pct))
            if price <= 0:
                break
            amount = min(self.amount_for(step), cash)
            qty = int(amount // price)
            if qty <= 0:
                break
            spend = qty * price
            shares += qty
            cost += spend
            cash -= spend
            rungs.append(
                Rung(
                    step=step,
                    price=price,
                    amount=self.amount_for(step),
                    qty=qty,
                    spend=spend,
                    shares_after=shares,
                    avg_after=cost / shares,
                    cash_after=cash,
                    drop_from_start=price / start - 1 if start else 0.0,
                )
            )
        return rungs

    def next_rung(self) -> Rung | None:
        rungs = self.plan(max_steps=1)
        return rungs[0] if rungs else None

    def apply_fill(self, price: float, qty: int) -> None:
        """실제 체결을 반영한다. 다음 단계는 이 체결가 기준으로 다시 잡힌다."""
        if qty <= 0:
            raise ValueError("체결 수량은 1주 이상이어야 합니다")
        spend = qty * price
        if spend > self.cash + 1e-9:
            raise ValueError(f"잔금 부족: 필요 ${spend:,.2f} / 보유 ${self.cash:,.2f}")
        self.cash -= spend
        self.cost_basis += spend
        self.shares += qty
        self.last_buy_price = price
        self.step += 1
        self.log.append(
            {"step": self.step, "price": price, "qty": qty, "avg": round(self.avg_price, 4)}
        )
