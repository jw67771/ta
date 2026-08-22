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
