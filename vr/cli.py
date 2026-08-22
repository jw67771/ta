"""VR 적립식 중계 CLI.

  시즌 시작 : python3 -m vr.cli init --multiplier 1 --pool 200 --week 1 --v 174.05
  체결 반영 : python3 -m vr.cli trade --price 71.90 --qty 1
  다음 사이클: python3 -m vr.cli cycle --price 72.30
  현재 상태 : python3 -m vr.cli status
"""

from __future__ import annotations

import argparse
import json
import pathlib
from dataclasses import asdict

from vr.engine import VRAccount

DEFAULT_STATE = pathlib.Path(__file__).parent / "state" / "tqqq_vr7.json"


def load(path):
    d = json.loads(path.read_text())
    log = d.pop("log", [])
    acc = VRAccount(**d)
    acc.log = log
    return acc


def save(acc, path, entry=None):
    d = asdict(acc)
    if entry:
        d["log"] = list(acc.log) + [entry]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description="라오어 VR 적립식 중계")
    ap.add_argument("--state", default=str(DEFAULT_STATE))
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="시즌 시작")
    p.add_argument("--multiplier", type=float, default=1.0)
    p.add_argument("--pool", type=float, required=True, help="현재 예수금")
    p.add_argument("--shares", type=int, default=0)
    p.add_argument("--week", type=int, default=0)
    p.add_argument("--v", type=float, default=0.0, help="현재 사이클 V")
    p.add_argument("--invested", type=float, default=0.0, help="누적 투자원금")

    p = sub.add_parser("trade", help="체결 반영 (매수 +, 매도 -)")
    p.add_argument("--price", type=float, required=True)
    p.add_argument("--qty", type=int, required=True)
    p.add_argument("--date", default="")

    p = sub.add_parser("cycle", help="다음 사이클 V/밴드 계산 후 확정")
    p.add_argument("--price", type=float, required=True, help="사이클 마지막 종가")
    p.add_argument("--dry-run", action="store_true", help="계산만 하고 저장하지 않음")

    sub.add_parser("status", help="현재 상태")

    args = ap.parse_args(argv)
    path = pathlib.Path(args.state)

    if args.cmd == "init":
        acc = VRAccount(multiplier=args.multiplier, pool=args.pool, shares=args.shares,
                        week=args.week, V=args.v, total_invested=args.invested)
        save(acc, path, {"event": "init", "pool": args.pool, "week": args.week, "V": args.v})
        print(f"VR {acc.multiplier:g}배 시작 · Pool ${acc.pool:,.2f} · 보유 {acc.shares}주 "
              f"· {acc.week}주차 · V {acc.V:,.2f}")
        return 0

    acc = load(path)

    if args.cmd == "trade":
        acc.trade(args.price, args.qty)
        save(acc, path, {"event": "trade", "date": args.date,
                         "price": args.price, "qty": args.qty})
        print(f"반영 완료 · 보유 {acc.shares}주 · Pool ${acc.pool:,.2f}")
    elif args.cmd == "cycle":
        c = acc.next_cycle(args.price)
        print(f"■ {acc.ticker} VR {acc.multiplier:g}배 · {c.week}주차\n"
              f"   직전 종가        {args.price:,.2f}\n"
              f"   보유 / 평가금    {acc.shares}주 / ${acc.value(args.price):,.2f}\n"
              f"   적립금           +${c.contribution:,.2f}\n"
              f"   다음 V           ${c.V:,.2f}\n"
              f"   최소 (V x 0.85)  ${c.low:,.2f}   ← 평가금이 여기 아래면 매수\n"
              f"   최대 (V x 1.15)  ${c.high:,.2f}   ← 평가금이 여기 위면 매도\n"
              f"   사이클 시작 Pool ${c.pool_start:,.2f}")
        if not args.dry_run:
            acc.apply_cycle(c, args.price)
            save(acc, path, {"event": "cycle", "week": c.week, "V": c.V,
                             "low": c.low, "high": c.high, "pool": c.pool_start})
    elif args.cmd == "status":
        print(f"{acc.ticker} VR {acc.multiplier:g}배 · {acc.week}주차\n"
              f"  보유 {acc.shares}주 · Pool ${acc.pool:,.2f}\n"
              f"  현재 V ${acc.V:,.2f} (최소 ${acc.V*0.85:,.2f} / 최대 ${acc.V*1.15:,.2f})\n"
              f"  누적 투자원금 ${acc.total_invested:,.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
