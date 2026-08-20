import unittest

from infinite_buying.dip_ladder import DipLadder


def soxl():
    return DipLadder(
        ticker="SOXL", step_pct=0.15, base_amount=500.0, increment=100.0,
        cash=9169.33, shares=6, cost_basis=830.67, last_buy_price=129.10,
    )


class TestDipLadder(unittest.TestCase):
    def test_first_rung_is_15_percent_below_last_buy(self):
        rung = soxl().next_rung()
        self.assertAlmostEqual(rung.price, 109.73, places=2)
        self.assertEqual(rung.qty, 4)  # $500 / 109.73
        self.assertEqual(rung.step, 1)

    def test_each_rung_is_15_percent_below_the_previous(self):
        rungs = soxl().plan(max_steps=7)
        self.assertEqual(len(rungs), 7)
        self.assertAlmostEqual(rungs[0].price, 109.73, places=2)
        for prev, cur in zip(rungs, rungs[1:]):
            self.assertAlmostEqual(cur.price / prev.price, 0.85, places=3)

    def test_amount_grows_by_increment(self):
        rungs = soxl().plan(max_steps=5)
        self.assertEqual([r.amount for r in rungs], [500, 600, 700, 800, 900])

    def test_increment_is_configurable(self):
        ladder = soxl()
        ladder.increment = 250.0
        self.assertEqual([r.amount for r in ladder.plan(max_steps=4)], [500, 750, 1000, 1250])

    def test_ladder_reaches_ten_steps_on_this_budget(self):
        """완만한 증액이라 잔금 $9,169 로 -80% 까지 10단계가 나온다."""
        rungs = soxl().plan(max_steps=20)
        self.assertEqual(len(rungs), 10)
        self.assertAlmostEqual(rungs[-1].price, 25.38, places=2)
        self.assertGreaterEqual(rungs[-1].cash_after, 0)

    def test_average_falls_monotonically(self):
        ladder = soxl()
        prev = ladder.avg_price
        for rung in ladder.plan(max_steps=7):
            self.assertLess(rung.avg_after, prev)
            prev = rung.avg_after

    def test_ladder_fits_in_cash(self):
        rungs = soxl().plan(max_steps=7)
        self.assertGreater(rungs[-1].cash_after, 0)
        self.assertAlmostEqual(sum(r.spend for r in rungs), 9169.33 - rungs[-1].cash_after, places=2)

    def test_gap_down_fill_reanchors_next_rung(self):
        """계획가 109.73 인데 100.00 에 체결되면 다음 단계는 100 기준으로 잡힌다."""
        ladder = soxl()
        ladder.apply_fill(price=100.00, qty=5)
        self.assertEqual(ladder.step, 1)
        self.assertAlmostEqual(ladder.last_buy_price, 100.00)
        self.assertAlmostEqual(ladder.next_rung().price, 85.00, places=2)
        self.assertEqual(ladder.next_rung().amount, 600)  # 2단계 금액

    def test_fill_updates_average(self):
        ladder = soxl()
        ladder.apply_fill(price=109.73, qty=4)
        self.assertEqual(ladder.shares, 10)
        self.assertAlmostEqual(ladder.avg_price, (830.67 + 4 * 109.73) / 10, places=4)
        self.assertAlmostEqual(ladder.cash, 9169.33 - 4 * 109.73, places=2)

    def test_cannot_overspend(self):
        ladder = soxl()
        with self.assertRaises(ValueError):
            ladder.apply_fill(price=100.0, qty=200)

    def test_ladder_stops_when_cash_runs_out(self):
        """$300 이면 109.73 에 2주($219)만 되고, 남은 $80 으로는 93.27 을 못 산다."""
        ladder = soxl()
        ladder.cash = 300.0
        rungs = ladder.plan(max_steps=8)
        self.assertEqual(len(rungs), 1)
        self.assertEqual(rungs[0].qty, 2)
        self.assertLess(rungs[0].cash_after, 93.27)


if __name__ == "__main__":
    unittest.main()
