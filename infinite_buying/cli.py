"""무한매수법 중계 CLI.

  주문표 뽑기 : python3 -m infinite_buying.cli plan  --close 76.40 --date 8/17
  체결 반영   : python3 -m infinite_buying.cli fill  --close 75.10 --bought 3
  현재 상태   : python3 -m infinite_buying.cli status
  새 사이클   : python3 -m infinite_buying.cli new-cycle
"""

from __future__ import annotations

import argparse
import json
import pathlib
from dataclasses import asdict

from infinite_buying.strategy import Position

STATE_DIR = pathlib.Path(__file__).parent / "state"
DEFAULT_STATE = STATE_DIR / "tqqq_40.json"


def load(path: pathlib.Path) -> Position:
    data = json.loads(path.read_text())
    log = data.pop("log", [])
    pos = Position(**data)
    pos._log = log  # type: ignore[attr-defined]
    return pos


def save(pos: Position, path: pathlib.Path, entry: dict | None = None) -> None:
    data = asdict(pos)
    log = list(getattr(pos, "_log", []))
    if entry:
        log.append(entry)
    data["log"] = log
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def money(x: float) -> str:
    return f"${x:,.2f}"


def render(pos: Position, plan) -> str:
    L = []
    half = "전반전" if plan.first_half else "후반전"
    L.append(f"■ {plan.ticker} 무한매수법 {plan.splits}분할 · {pos.cycle}차 사이클 · {half}")
    if plan.close_date:
        L.append(f"   직전 종가({plan.close_date}) {plan.close:.2f}")
    else:
        L.append(f"   직전 종가 {plan.close:.2f}")
    L.append("")
    L.append(f"   현재 회차 T      {plan.progress:.2f} / {plan.splits}")
    L.append(f"   1+별%            {(1 + plan.star_pct) * 100:.2f}%")
    L.append(f"   매수평단         {plan.avg_price:.2f}" if plan.avg_price else "   매수평단         -")
    L.append(f"   보유개수         {plan.shares}주")
    L.append(f"   잔금             {money(plan.cash)}")
    L.append(f"   1회 매수금액     {money(plan.unit_budget)}")
    if plan.shares:
        L.append(f"   보유수익률       {plan.eval_pnl_pct:+.2f}%")
    L.append("")
    L.append("   ── 매수점 (전부 LOC) ─────────────────")
    if plan.buys:
        for o in plan.buys:
            L.append(f"     {o.price:>8.2f}  x {o.qty:>2}주   {o.note}")
    else:
        L.append("     (없음 — 잔금 소진)")
    L.append("")
    L.append("   ── 매도점 ────────────────────────────")
    if plan.sells:
        for o in plan.sells:
            L.append(f"     {o.price:>8.2f}  x {o.qty:>2}주   {o.kind} · {o.note}")
    else:
        L.append("     (없음 — 보유 0주)")
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="라오어 무한매수법 V4.0 중계")
    ap.add_argument("--state", default=str(DEFAULT_STATE), help="상태 파일 경로")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="새 시즌 시작")
    p.add_argument("--ticker", default="TQQQ")
    p.add_argument("--splits", type=int, default=40)
    p.add_argument("--limit-pct", type=float, default=0.15)
    p.add_argument("--cash", type=float, required=True)

    p = sub.add_parser("plan", help="오늘 걸 주문표")
    p.add_argument("--close", type=float, required=True, help="직전 종가")
    p.add_argument("--date", default="", help="직전 종가 날짜 (표시용)")
    p.add_argument("--rungs", type=int, default=None, help="사다리 칸수 고정")

    p = sub.add_parser("fill", help="그날 체결 반영")
    p.add_argument("--close", type=float, required=True, help="그날 종가")
    p.add_argument("--date", default="")
    p.add_argument("--bought", type=int, default=0)
    p.add_argument("--sold-loc", type=int, default=0, help="별지점 LOC 매도 체결 수량")
    p.add_argument("--sold-limit", type=int, default=0, help="지정가 매도 체결 수량")
    p.add_argument("--limit-price", type=float, default=None)

    sub.add_parser("status", help="현재 상태")
    sub.add_parser("new-cycle", help="보유 0 상태에서 다음 사이클 시작")

    args = ap.parse_args(argv)
    path = pathlib.Path(args.state)

    if args.cmd == "init":
        pos = Position(
            ticker=args.ticker,
            splits=args.splits,
            limit_sell_pct=args.limit_pct,
            cycle_start_cash=args.cash,
            cash=args.cash,
        )
        save(pos, path, {"event": "init", "cash": args.cash})
        print(f"{args.ticker} {args.splits}분할 시즌 시작 · 원금 {money(args.cash)}")
        return 0

    pos = load(path)

    if args.cmd == "plan":
        print(render(pos, pos.plan(args.close, args.date, ladder_rungs=args.rungs)))
    elif args.cmd == "fill":
        res = pos.apply_fills(
            close=args.close,
            bought=args.bought,
            sold_loc=args.sold_loc,
            sold_limit=args.sold_limit,
            limit_price=args.limit_price,
        )
        save(
            pos,
            path,
            {
                "event": "fill",
                "date": args.date,
                "close": args.close,
                "bought": args.bought,
                "sold_loc": args.sold_loc,
                "sold_limit": args.sold_limit,
                "realized": round(res["realized"], 2),
            },
        )
        print(
            f"반영 완료 · 보유 {pos.shares}주 · 평단 {pos.avg_price:.2f} · "
            f"잔금 {money(pos.cash)} · T {pos.progress:.2f} · "
            f"당일 실현 {money(res['realized'])}"
        )
        if res["cycle_closed"]:
            print("★ 보유 0주 — 사이클 종료. new-cycle 로 다음 사이클을 시작하세요.")
    elif args.cmd == "status":
        print(
            f"{pos.ticker} {pos.splits}분할 · {pos.cycle}차 사이클\n"
            f"  보유 {pos.shares}주 · 평단 {pos.avg_price:.2f}\n"
            f"  잔금 {money(pos.cash)} · 사이클시작 {money(pos.cycle_start_cash)}\n"
            f"  T {pos.progress:.2f}/{pos.splits} · 1회매수금액 {money(pos.unit_budget)}\n"
            f"  시즌 누적 실현손익 {money(pos.realized_total)}"
        )
    elif args.cmd == "new-cycle":
        pos.start_new_cycle()
        save(pos, path, {"event": "new-cycle", "cash": pos.cash})
        print(f"{pos.cycle}차 사이클 시작 · 원금 {money(pos.cycle_start_cash)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
