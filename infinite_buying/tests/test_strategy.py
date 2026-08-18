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
            self.assertIn(expected, prices)

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
