"""VR 7기 적립식 1주차 공개 자료를 그대로 재현하는지 검증한다."""

import unittest

from vr.engine import VRAccount


class TestVR7Week1(unittest.TestCase):
    """8/21 종가 71.17 에 1개 매수, Pool 100 -> 28.83 인 상태에서
    1주차 V = 174.05, 최소 147.94, 최대 200.16 이 나와야 한다."""

    def account(self, multiplier=1.0):
        acc = VRAccount(multiplier=multiplier, G=10.0)
        acc.pool = 100.0 * multiplier
        acc.V = 0.0
        acc.shares = 0
        acc.trade(price=71.17, qty=int(1 * multiplier))
        return acc

    def test_first_buy_leaves_expected_pool(self):
        acc = self.account()
        self.assertEqual(acc.shares, 1)
        self.assertAlmostEqual(acc.pool, 28.83, places=2)

    def test_week1_V_and_band(self):
        acc = self.account()
        acc.V = 71.17  # 0주차 V = 첫 매수 평가금
        c = acc.next_cycle(last_price=71.17)
        self.assertAlmostEqual(c.V, 174.05, places=2)
        self.assertAlmostEqual(c.low, 147.94, places=2)
        self.assertAlmostEqual(c.high, 200.16, places=2)
        self.assertAlmostEqual(c.pool_start, 128.83, places=2)

    def test_band_is_15_percent(self):
        acc = self.account()
        acc.V = 71.17
        c = acc.next_cycle(71.17)
        self.assertAlmostEqual(c.low / c.V, 0.85, places=4)
        self.assertAlmostEqual(c.high / c.V, 1.15, places=4)

    def test_multiplier_scales_everything(self):
        for n in (2, 4, 10):
            with self.subTest(n=n):
                acc = self.account(multiplier=n)
                acc.V = 71.17 * n
                c = acc.next_cycle(71.17)
                self.assertAlmostEqual(c.V, 174.05 * n, delta=0.02 * n)
                self.assertAlmostEqual(c.low, 147.94 * n, delta=0.02 * n)
                self.assertAlmostEqual(c.pool_start, 128.83 * n, delta=0.02 * n)
                self.assertEqual(acc.shares, n)

    def test_E_above_V_pushes_V_up(self):
        """평가금이 V 보다 크면 다음 V 가 더 올라간다 (상승분의 일부를 따라간다)."""
        acc = self.account()
        acc.V = 71.17
        flat = acc.next_cycle(71.17).V
        up = acc.next_cycle(80.00).V
        self.assertGreater(up, flat)
        self.assertAlmostEqual(up - flat, (80.00 - 71.17) / (2 * 10 ** 0.5), places=2)

    def test_pool_cannot_go_negative(self):
        acc = self.account()
        with self.assertRaises(ValueError):
            acc.trade(price=147.94, qty=1)  # Pool 28.83 뿐

    def test_apply_cycle_carries_state(self):
        acc = self.account()
        acc.V = 71.17
        c = acc.next_cycle(71.17)
        acc.apply_cycle(c, 71.17)
        self.assertEqual(acc.week, 1)
        self.assertAlmostEqual(acc.V, 174.05, places=2)
        self.assertAlmostEqual(acc.pool, 128.83, places=2)
        self.assertAlmostEqual(acc.total_invested, 100.0, places=2)


if __name__ == "__main__":
    unittest.main()


class TestOrderLadders(unittest.TestCase):
    """VR 6기 3주차 공개 주문표를 그대로 재현하는지 검증한다.

    V=263.69, 최소 224.14, 최대 303.24, 보유 3주, 처음 Pool 144.40.
    """

    def account(self):
        acc = VRAccount(multiplier=1.0, G=10.0)
        acc.shares, acc.pool, acc.V, acc.week = 3, 144.40, 263.69, 3
        return acc

    def test_week3_V_and_band(self):
        """직전 V 158.73, Pool 44.40, E 162.00 -> V 263.69."""
        acc = VRAccount(multiplier=1.0, G=10.0)
        acc.V, acc.pool, acc.shares = 158.73, 44.40, 3
        c = acc.next_cycle(last_price=162.00 / 3)
        self.assertAlmostEqual(c.V, 263.69, places=2)
        self.assertAlmostEqual(c.low, 224.14, places=2)
        self.assertAlmostEqual(c.high, 303.24, places=2)
        self.assertAlmostEqual(c.pool_start, 144.40, places=2)

    def test_buy_ladder_matches_published_table(self):
        rungs = self.account().buy_ladder(low=224.14)
        self.assertEqual(len(rungs), 2)  # 3번째(44.83)는 Pool 13.65 로 못 산다
        self.assertAlmostEqual(rungs[0].price, 74.71, places=2)
        self.assertAlmostEqual(rungs[0].pool_after, 69.69, places=2)
        self.assertEqual(rungs[0].shares_after, 4)
        self.assertAlmostEqual(rungs[1].price, 56.04, places=2)
        self.assertAlmostEqual(rungs[1].pool_after, 13.65, places=2)
        self.assertEqual(rungs[1].shares_after, 5)

    def test_sell_ladder_matches_published_table(self):
        rungs = self.account().sell_ladder(high=303.24)
        self.assertAlmostEqual(rungs[0].price, 101.08, places=2)
        self.assertAlmostEqual(rungs[0].pool_after, 245.48, places=2)
        self.assertEqual(rungs[0].shares_after, 2)
        self.assertAlmostEqual(rungs[1].price, 151.62, places=2)
        self.assertAlmostEqual(rungs[1].pool_after, 397.10, places=2)
        self.assertEqual(rungs[1].shares_after, 1)

    def test_ladder_price_puts_value_exactly_on_the_band(self):
        """매수점에서 보유 평가금이 최소값과 같아진다."""
        acc = self.account()
        for rung in acc.buy_ladder(low=224.14):
            shares_before = rung.shares_after - 1
            self.assertAlmostEqual(rung.price * shares_before, 224.14, delta=0.03)
        for rung in acc.sell_ladder(high=303.24):
            shares_before = rung.shares_after + 1
            self.assertAlmostEqual(rung.price * shares_before, 303.24, delta=0.03)

    def test_vr7_week1_ladder_is_unaffordable(self):
        """VR 7기 1주차는 매수점 147.94 가 Pool 128.83 을 넘어 한 칸도 못 건다.
        라오어가 '표는 무시하라' 고 한 상황이 이것이다."""
        acc = VRAccount(multiplier=1.0, G=10.0)
        acc.shares, acc.pool = 1, 128.83
        self.assertEqual(acc.buy_ladder(low=147.94), [])
        self.assertAlmostEqual(acc.next_buy_price(147.94), 147.94, places=2)

    def test_buy_ladder_stops_when_pool_empty(self):
        acc = self.account()
        acc.pool = 80.0
        rungs = acc.buy_ladder(low=224.14)
        self.assertEqual(len(rungs), 1)
        self.assertGreaterEqual(rungs[0].pool_after, 0)
