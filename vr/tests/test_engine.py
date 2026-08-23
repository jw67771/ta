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


class TestCycleChain(unittest.TestCase):
    """VR 6기 1~13주차와 VR 7기 0~1주차의 사이클 전이를 전부 재현한다.

    (직전 V, 마지막 Pool, 마지막 평가금 E) -> (다음 V, 최소, 최대).
    적립금 100, G 10 은 전 구간 동일.
    """

    TRANSITIONS = [
        # 라벨, 직전 V, 마지막 Pool, 마지막 평가금 E, 다음 V, 최소, 최대
        # 최소/최대가 None 이면 그 주차 자료에 밴드가 안 실려 V 만 검증한다.
        ("VR7 0->1주", 71.17, 28.83, 71.17, 174.05, 147.94, 200.16),
        ("VR6 1->3주", 158.73, 44.40, 162.00, 263.69, 224.14, 303.24),
        ("VR6 3->5주", 263.69, 34.20, 242.35, 363.74, 309.18, 418.30),
        ("VR6 5->7주", 363.74, 37.50, 346.64, 464.79, 395.07, 534.51),
        ("VR6 7->9주", 464.79, 41.14, 413.37, 560.77, 476.65, 644.89),
        ("VR6 9->11주", 560.77, 46.14, 426.58, 644.17, 547.54, 740.80),
        ("VR6 11->13주", 644.17, 33.14, 688.38, 754.47, 641.30, 867.64),
        ("VR6 13->15주", 754.47, 195.11, 813.28, 883.28, 750.79, 1015.77),
        ("VR6 15->17주", 883.28, 295.11, 991.64, 1029.92, 875.43, 1184.41),
        ("VR6 17->19주", 1029.92, 395.11, 1011.92, 1166.58, 991.59, 1341.57),
        ("VR6 19->21주", 1166.58, 418.83, 1022.70, 1285.71, 1092.85, 1478.57),
        ("VR6 21->23주", 1285.71, 300.81, 1408.79, 1435.25, 1219.96, 1650.54),
        ("VR6 23->25주", 1435.25, 331.52, 1320.30, 1550.23, None, None),
        ("VR6 25->27주", 1550.23, 226.04, 1418.13, 1651.95, 1404.16, 1899.74),
        ("VR6 27->29주", 1651.95, 75.79, 1615.50, 1753.77, 1490.70, 2016.84),
        ("VR6 29->31주", 1753.77, 175.79, 1919.75, 1897.59, 1612.95, 2182.23),
    ]

    def test_all_transitions(self):
        for name, V1, pool, E, exp_V, exp_lo, exp_hi in self.TRANSITIONS:
            with self.subTest(name):
                acc = VRAccount(multiplier=1.0, G=10.0)
                acc.V, acc.pool, acc.shares = V1, pool, 1
                c = acc.next_cycle(last_price=E)  # 1주 보유로 두면 평가금 = E
                self.assertAlmostEqual(c.V, exp_V, places=2)
                if exp_lo is not None:
                    self.assertAlmostEqual(c.low, exp_lo, places=2)
                    self.assertAlmostEqual(c.high, exp_hi, places=2)

    def test_pool_carries_contribution(self):
        for name, V1, pool, E, *_ in self.TRANSITIONS:
            with self.subTest(name):
                acc = VRAccount(multiplier=1.0, G=10.0)
                acc.V, acc.pool, acc.shares = V1, pool, 1
                self.assertAlmostEqual(acc.next_cycle(E).pool_start, pool + 100, places=2)


class TestDividend(unittest.TestCase):
    """VR 6기 11주차: Pool 146.14 - 거래액 113.67 + 배당 0.67 = 33.14."""

    def test_dividend_lands_in_pool(self):
        acc = VRAccount(multiplier=1.0, G=10.0)
        acc.pool, acc.shares = 146.14, 1
        acc.pool = round(acc.pool - 113.67, 2)  # 그 사이클 거래액
        acc.dividend(0.67)
        self.assertAlmostEqual(acc.pool, 33.14, places=2)

    def test_dividend_flows_into_next_V(self):
        """배당이 Pool 에 남아 다음 V 의 Pool/G 항을 키운다."""
        base = VRAccount(multiplier=1.0, G=10.0)
        base.V, base.pool, base.shares = 644.17, 33.14, 1
        without = base.next_cycle(688.38).V
        withdiv = VRAccount(multiplier=1.0, G=10.0)
        withdiv.V, withdiv.pool, withdiv.shares = 644.17, 33.14, 1
        withdiv.dividend(10.0)
        self.assertAlmostEqual(withdiv.next_cycle(688.38).V - without, 1.0, places=2)


class TestPoolChain(unittest.TestCase):
    """VR 6기 1~23주차 Pool 연결.

    처음 Pool + 거래액 + 배당 = 마지막 Pool, 거기에 적립금 100 을 더하면
    다음 사이클의 처음 Pool 이 된다. 매수(-)·매도(+)·무거래·배당이 모두 섞여 있다.
    """

    CHAIN = [
        # 주차, 처음 Pool, 거래액, 배당, 다음 사이클 처음 Pool
        (1, 145.86, -101.46, 0.0, 144.40),
        (3, 144.40, -110.20, 0.0, 134.20),
        (5, 134.20, -96.70, 0.0, 137.50),
        (7, 137.50, -96.36, 0.0, 141.14),
        (9, 141.14, -95.00, 0.0, 146.14),
        (11, 146.14, -113.67, 0.67, 133.14),  # 배당이 낀 사이클
        (13, 133.14, 61.97, 0.0, 295.11),  # 첫 매도
        (15, 295.11, 0.0, 0.0, 395.11),  # 밴드 안이라 거래 없음
        (17, 395.11, 0.0, 0.0, 495.11),
        (19, 495.11, -76.28, 0.0, 518.83),
        (21, 518.83, -218.02, 0.0, 400.81),
        (23, 400.81, -69.29, 0.0, 431.52),
        (25, 431.52, -205.48, 0.0, 326.04),
        (27, 326.04, -250.25, 0.0, 175.79),
        (29, 175.79, 0.0, 0.0, 275.79),
    ]

    def test_chain(self):
        for week, start, traded, div, next_start in self.CHAIN:
            with self.subTest(f"{week}주차"):
                acc = VRAccount(multiplier=1.0, G=10.0)
                acc.pool, acc.shares, acc.V = start, 1, 1000.0
                # 거래액은 매수면 음수 (Pool 감소), 매도면 양수 (Pool 증가)
                acc.pool = round(acc.pool + traded, 2)
                if div:
                    acc.dividend(div)
                self.assertAlmostEqual(
                    acc.next_cycle(last_price=1000.0).pool_start, next_start, places=2
                )

    def test_chain_covers_buy_sell_flat_and_dividend(self):
        kinds = {("매수" if t < 0 else "매도" if t > 0 else "무거래") for _, _, t, _, _ in self.CHAIN}
        self.assertEqual(kinds, {"매수", "매도", "무거래"})
        self.assertTrue(any(d for *_, d, _ in self.CHAIN))
