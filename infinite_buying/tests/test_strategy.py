"""라오어가 공개한 중계표 4개를 그대로 재현하는지 검증한다.

출처: '2040무매 8/18 낮기준' (2026-08-17 종가 기준) 및 '무한매수법 이용안내'.
표에 찍힌 매수평단/1회매수시도는 소수 둘째자리로 반올림된 값이라
가격 비교에는 1센트 오차를 허용한다. 수량과 사다리 가격은 정확히 일치해야 한다.
"""

import unittest

from infinite_buying.strategy import Position


def position_from_table(ticker, splits, limit_pct, cash, unit_budget, avg, shares):
    """표에 찍힌 잔금/1회매수시도로부터 T 를 역산해 상태를 만든다."""
    progress = splits - cash / unit_budget
    pos = Position(
        ticker=ticker,
        splits=splits,
        limit_sell_pct=limit_pct,
        cash=cash,
        shares=shares,
        cost_basis=avg * shares,
        progress=progress,
    )
    return pos


class TestPublishedTables(unittest.TestCase):
    def assert_plan(self, plan, star_pct, star, limit, buys, sells):
        self.assertAlmostEqual(plan.star_pct * 100, star_pct, places=1)
        self.assertAlmostEqual(plan.star_price, star, delta=0.011)
        self.assertAlmostEqual(plan.limit_price, limit, delta=0.011)

        got_buys = [(o.price, o.qty) for o in plan.buys][: len(buys)]
        for (gp, gq), (ep, eq) in zip(got_buys, buys):
            self.assertAlmostEqual(gp, ep, delta=0.011)
            self.assertEqual(gq, eq)
        self.assertEqual(len(got_buys), len(buys))

        got_sells = [(o.price, o.qty) for o in plan.sells]
        for (gp, gq), (ep, eq) in zip(got_sells, sells):
            self.assertAlmostEqual(gp, ep, delta=0.011)
            self.assertEqual(gq, eq)
        self.assertEqual(len(got_sells), len(sells))

    def test_tqqq_20_splits(self):
        pos = position_from_table("TQQQ", 20, 0.15, 8633.53, 545.32, 71.16, 30)
        self.assertAlmostEqual(pos.progress, 4.17, places=2)
        plan = pos.plan(76.40)
        self.assert_plan(
            plan,
            star_pct=8.75,
            star=77.39,
            limit=81.84,
            buys=[(77.38, 3), (71.16, 4), (68.16, 1), (60.59, 1)],
            sells=[(77.39, 7), (81.84, 23)],
        )

    def test_tqqq_40_splits(self):
        pos = position_from_table("TQQQ", 40, 0.15, 16853.87, 544.18, 71.63, 63)
        self.assertAlmostEqual(pos.progress, 9.03, places=2)
        plan = pos.plan(76.40)
        self.assert_plan(
            plan,
            star_pct=8.23,
            star=77.52,
            limit=82.37,
            buys=[(77.51, 3), (71.63, 4), (68.02, 1), (60.46, 1)],
            sells=[(77.52, 15), (82.37, 48)],
        )

    def test_soxl_20_splits(self):
        pos = position_from_table("SOXL", 20, 0.20, 5749.72, 538.45, 148.24, 33)
        self.assertAlmostEqual(pos.progress, 9.32, places=2)
        plan = pos.plan(151.53)
        self.assert_plan(
            plan,
            star_pct=1.36,
            star=150.25,
            limit=177.89,
            buys=[(150.24, 1), (148.24, 2), (134.61, 1)],
            sells=[(150.25, 8), (177.89, 25)],
        )

    def test_soxl_40_splits(self):
        pos = position_from_table("SOXL", 40, 0.20, 15628.89, 655.26, 151.52, 67)
        self.assertAlmostEqual(pos.progress, 16.15, places=2)
        plan = pos.plan(151.53)
        self.assert_plan(
            plan,
            star_pct=3.85,
            star=157.36,
            limit=181.83,
            buys=[(157.35, 2), (151.52, 2), (131.05, 1), (109.20, 1)],
            sells=[(157.36, 16), (181.83, 51)],
        )

    def test_ladder_matches_soxl_20_tail(self):
        """SOXL 20분할 사다리 꼬리: 59.82 / 53.84 / 48.94 / 44.87 / 41.41."""
        pos = position_from_table("SOXL", 20, 0.20, 5749.72, 538.45, 148.24, 33)
        prices = [o.price for o in pos.plan(151.53, ladder_rungs=10).buys]
        for expected in (59.82, 53.84, 48.94, 44.87, 41.41):
            self.assertTrue(any(abs(p - expected) <= 0.011 for p in prices),
                            f"{expected} 없음: {prices}")

    def test_star_pct_is_zero_at_half_way(self):
        """전반전이 끝나는 지점(T = 분할수/2)에서 별지점은 평단과 같아진다."""
        pos = Position(splits=40, progress=20.0, cash=5000.0, shares=50, cost_basis=50 * 70)
        self.assertAlmostEqual(pos.star_pct, 0.0, places=9)
        self.assertFalse(pos.first_half)

    def test_star_pct_starts_at_limit_pct(self):
        pos = Position(splits=40, progress=0.0)
        self.assertAlmostEqual(pos.star_pct, 0.15, places=9)


class TestFills(unittest.TestCase):
    def test_buy_keeps_unit_budget_stable(self):
        pos = Position(splits=40, cash=10_000.0)
        unit = pos.unit_budget
        self.assertAlmostEqual(unit, 250.0)
        pos.apply_fills(close=76.0, bought=3)
        self.assertAlmostEqual(pos.unit_budget, unit, places=6)
        self.assertEqual(pos.shares, 3)
        self.assertAlmostEqual(pos.cash, 10_000 - 228)
        self.assertAlmostEqual(pos.progress, 228 / 250)

    def test_profitable_sell_grows_unit_budget(self):
        pos = Position(splits=40, cash=10_000.0)
        pos.apply_fills(close=70.0, bought=3)
        before = pos.unit_budget
        pos.apply_fills(close=80.0, sold_loc=1)
        self.assertGreater(pos.unit_budget, before)
        self.assertAlmostEqual(pos.realized_total, 10.0)

    def test_full_exit_resets_cycle(self):
        pos = Position(splits=40, cash=10_000.0)
        pos.apply_fills(close=70.0, bought=3)
        res = pos.apply_fills(close=80.5, sold_loc=3)
        self.assertTrue(res["cycle_closed"])
        self.assertEqual(pos.shares, 0)
        pos.start_new_cycle()
        self.assertEqual(pos.cycle, 2)
        self.assertEqual(pos.progress, 0.0)
        self.assertAlmostEqual(pos.cycle_start_cash, 10_000 + 3 * 10.5)

    def test_cannot_sell_more_than_held(self):
        pos = Position(splits=40, cash=10_000.0)
        pos.apply_fills(close=70.0, bought=2)
        with self.assertRaises(ValueError):
            pos.apply_fills(close=80.0, sold_loc=3)


if __name__ == "__main__":
    unittest.main()


class TestInitWithExistingPosition(unittest.TestCase):
    """기존 보유분을 편입해도 1회매수금액은 원금/분할수 그대로여야 한다."""

    def test_unit_budget_unchanged(self):
        total, splits, shares, avg = 10_000.0, 40, 2, 77.91
        cost = shares * avg
        pos = Position(
            splits=splits,
            cycle_start_cash=total,
            cash=total - cost,
            shares=shares,
            cost_basis=cost,
            progress=cost / (total / splits),
        )
        self.assertAlmostEqual(pos.unit_budget, total / splits, places=6)
        self.assertAlmostEqual(pos.avg_price, avg, places=6)
        self.assertAlmostEqual(pos.progress, cost / 250.0, places=6)


class TestPublishedTables0819(unittest.TestCase):
    """'2040무매 8/19 낮기준' — 8/18 종가(TQQQ 72.53 / SOXL 129.10) 기준 표."""

    def assert_orders(self, orders, expected):
        """수량은 정확히, 가격은 1센트 오차까지 (표의 잔금·1회매수금액이 반올림값)."""
        self.assertEqual(len(expected), len(orders[: len(expected)]))
        for order, (price, qty) in zip(orders, expected):
            self.assertAlmostEqual(order.price, price, delta=0.011)
            self.assertEqual(order.qty, qty)

    def test_tqqq_20_splits(self):
        pos = position_from_table("TQQQ", 20, 0.15, 8415.94, 548.92, 71.29, 33)
        self.assertAlmostEqual(pos.progress, 4.67, places=2)
        plan = pos.plan(72.53)
        self.assertAlmostEqual((1 + plan.star_pct) * 100, 108.00, places=1)
        self.assertTrue(plan.two_line)
        self.assert_orders(plan.buys, [(76.98, 3), (71.29, 4), (68.61, 1),
                                       (60.99, 1), (54.89, 1), (49.90, 1)])
        self.assert_orders(plan.sells, [(76.99, 8), (81.98, 25)])

    def test_tqqq_40_splits(self):
        pos = position_from_table("TQQQ", 40, 0.15, 16636.28, 545.97, 71.67, 66)
        self.assertAlmostEqual(pos.progress, 9.53, places=2)
        plan = pos.plan(72.53)
        self.assertAlmostEqual((1 + plan.star_pct) * 100, 107.85, places=1)
        self.assert_orders(plan.buys, [(77.29, 3), (71.67, 4), (68.24, 1),
                                       (60.66, 1), (54.59, 1), (49.63, 1)])
        self.assert_orders(plan.sells, [(77.30, 16), (82.42, 50)])

    def test_soxl_20_splits_second_half(self):
        """후반전(T 10.32) — 별%가 음수가 되고 평단 줄이 사라진다."""
        pos = position_from_table("SOXL", 20, 0.20, 5233.32, 540.72, 146.17, 37)
        self.assertAlmostEqual(pos.progress, 10.32, places=2)
        self.assertFalse(pos.first_half)
        plan = pos.plan(129.10)
        self.assertAlmostEqual((1 + plan.star_pct) * 100, 99.36, places=1)
        self.assertLess(plan.star_pct, 0)
        self.assertFalse(plan.two_line)  # 평단(146.17) > 상단 줄(144.59)
        self.assert_orders(plan.buys, [(144.59, 3), (135.18, 1), (108.14, 1),
                                       (90.12, 1), (77.24, 1)])
        self.assert_orders(plan.sells, [(145.23, 9), (175.41, 28)])

    def test_soxl_40_splits_avg_above_big_number(self):
        """전반전이지만 급락으로 평단(149.97)이 큰수(144.59) 위 — 평단 줄 없음."""
        pos = position_from_table("SOXL", 40, 0.20, 14983.39, 655.68, 149.97, 72)
        self.assertAlmostEqual(pos.progress, 17.15, places=2)
        self.assertTrue(pos.first_half)
        plan = pos.plan(129.10)
        self.assertAlmostEqual((1 + plan.star_pct) * 100, 102.85, places=1)
        self.assertFalse(plan.two_line)
        self.assert_orders(plan.buys, [(144.59, 4), (131.13, 1), (109.28, 1),
                                       (93.66, 1), (81.96, 1)])
        self.assert_orders(plan.sells, [(154.24, 18), (179.96, 54)])


class TestProgressTransition(unittest.TestCase):
    """8/18 표에서 하루 매수 후 8/19 표의 회차·잔금·1회매수금액이 나와야 한다.

    회차는 체결 금액이 아니라 체결된 줄 수로 센다. TQQQ 는 평단이 종가보다
    낮아 상단 줄만 체결되어 +0.5, SOXL 은 두 줄 다 체결되어 +1.0 이다.
    """

    CASES = [
        # 종목, 분할, 지정가율, 8/18(잔금, u, 평단, 보유), 종가, 매수, 8/19(T, 잔금, u)
        ("TQQQ", 20, 0.15, (8633.53, 545.32, 71.16, 30), 76.40, 72.53, 3, (4.67, 8415.94, 548.92)),
        ("TQQQ", 40, 0.15, (16853.87, 544.18, 71.63, 63), 76.40, 72.53, 3, (9.53, 16636.28, 545.97)),
        ("SOXL", 20, 0.20, (5749.72, 538.45, 148.24, 33), 151.53, 129.10, 4, (10.32, 5233.32, 540.72)),
        ("SOXL", 40, 0.20, (15628.89, 655.26, 151.52, 67), 151.53, 129.10, 5, (17.15, 14983.39, 655.68)),
    ]

    def test_transitions(self):
        for ticker, splits, pct, before, prev_close, close, bought, after in self.CASES:
            with self.subTest(f"{ticker} {splits}분할"):
                cash, unit, avg, shares = before
                pos = position_from_table(ticker, splits, pct, cash, unit, avg, shares)
                res = pos.apply_fills(close=close, bought=bought, prev_close=prev_close)
                self.assertIsNone(res["mismatch"], res["mismatch"])
                exp_T, exp_cash, exp_unit = after
                self.assertAlmostEqual(pos.progress, exp_T, places=2)
                self.assertAlmostEqual(pos.cash, exp_cash, delta=0.02)
                self.assertAlmostEqual(pos.unit_budget, exp_unit, delta=0.05)

    def test_progress_steps_are_half_or_whole(self):
        for ticker, splits, pct, before, prev_close, close, bought, after in self.CASES:
            cash, unit, avg, shares = before
            pos = position_from_table(ticker, splits, pct, cash, unit, avg, shares)
            step = pos.plan(prev_close).buy_progress(close)
            self.assertIn(step, (0.5, 1.0))

    def test_qty_mismatch_is_reported(self):
        pos = position_from_table("TQQQ", 20, 0.15, 8633.53, 545.32, 71.16, 30)
        res = pos.apply_fills(close=72.53, bought=7, prev_close=76.40)
        self.assertEqual(res["mismatch"], "계획상 3주 / 신고 7주")


class TestPublishedTables0820(TestPublishedTables0819):
    """'2040무매 8/20 낮기준' — 8/19 종가 72.06 기준. SOXL 은 사용자가 철회해 TQQQ 만."""

    def test_tqqq_20_splits(self):
        pos = position_from_table("TQQQ", 20, 0.15, 8199.76, 552.85, 71.35, 36)
        self.assertAlmostEqual(pos.progress, 5.17, places=2)
        plan = pos.plan(72.06)
        self.assertAlmostEqual((1 + plan.star_pct) * 100, 107.25, places=1)
        self.assert_orders(plan.buys, [(76.51, 3), (71.35, 4), (69.10, 1),
                                       (61.42, 1), (55.28, 1), (50.25, 1)])
        self.assert_orders(plan.sells, [(76.52, 9), (82.05, 27)])

    def test_tqqq_40_splits(self):
        pos = position_from_table("TQQQ", 40, 0.15, 16420.10, 547.87, 71.69, 69)
        self.assertAlmostEqual(pos.progress, 10.03, places=2)
        plan = pos.plan(72.06)
        self.assertAlmostEqual((1 + plan.star_pct) * 100, 107.48, places=1)
        self.assert_orders(plan.buys, [(77.04, 3), (71.69, 4), (68.48, 1),
                                       (60.87, 1), (54.78, 1)])
        self.assert_orders(plan.sells, [(77.05, 17), (82.44, 52)])

    def test_soxl_20_splits_second_half(self):
        self.skipTest("SOXL 철회")

    def test_soxl_40_splits_avg_above_big_number(self):
        self.skipTest("SOXL 철회")


class TestProgressTransition0820(unittest.TestCase):
    """8/19 표 -> 8/20 표. 평단이 종가보다 낮아 상단 줄만 체결 → ΔT = +0.5."""

    CASES = [
        # 분할, 8/19(잔금, u, 평단, 보유), 전날기준종가, 종가, 매수, 8/20(T, 잔금, u, 평단, 보유)
        (20, (8415.94, 548.92, 71.29, 33), 72.53, 72.06, 3, (5.17, 8199.76, 552.85, 71.35, 36)),
        (40, (16636.28, 545.97, 71.67, 66), 72.53, 72.06, 3, (10.03, 16420.10, 547.87, 71.69, 69)),
    ]

    def test_transitions(self):
        for splits, before, prev_close, close, bought, after in self.CASES:
            with self.subTest(f"TQQQ {splits}분할"):
                cash, unit, avg, shares = before
                pos = position_from_table("TQQQ", splits, 0.15, cash, unit, avg, shares)
                res = pos.apply_fills(close=close, bought=bought, prev_close=prev_close)
                self.assertIsNone(res["mismatch"], res["mismatch"])
                exp_T, exp_cash, exp_unit, exp_avg, exp_shares = after
                self.assertAlmostEqual(pos.progress, exp_T, places=2)
                self.assertAlmostEqual(pos.cash, exp_cash, delta=0.02)
                self.assertAlmostEqual(pos.unit_budget, exp_unit, delta=0.05)
                self.assertAlmostEqual(pos.avg_price, exp_avg, delta=0.011)
                self.assertEqual(pos.shares, exp_shares)

    def test_only_upper_line_filled(self):
        """종가 72.06 이 평단(71.29/71.67) 보다 위라 평단 줄은 미체결."""
        for splits, before, prev_close, close, _, _ in self.CASES:
            cash, unit, avg, shares = before
            pos = position_from_table("TQQQ", splits, 0.15, cash, unit, avg, shares)
            plan = pos.plan(prev_close)
            self.assertEqual(plan.buy_progress(close), 0.5)
            self.assertGreater(close, round(plan.avg_price, 2))
