from __future__ import annotations

import unittest

from xiyou_solo import engine


class DiceTests(unittest.TestCase):
    def test_d20_range(self) -> None:
        engine.set_seed(42)
        for _ in range(200):
            out = engine.roll_d20("normal")
            self.assertGreaterEqual(out["d20"], 1)
            self.assertLessEqual(out["d20"], 20)

    def test_3d6_range(self) -> None:
        engine.set_seed(43)
        for _ in range(200):
            total, _rolls = engine.gen_stat_3d6()
            self.assertGreaterEqual(total, 3)
            self.assertLessEqual(total, 18)

    def test_4d6_drop_lowest_range(self) -> None:
        engine.set_seed(44)
        for _ in range(200):
            total, _rolls = engine.gen_stat_4d6_drop_lowest()
            self.assertGreaterEqual(total, 3)
            self.assertLessEqual(total, 18)

    def test_advantage_logic(self) -> None:
        engine.set_seed(2026)
        adv = engine.roll_d20("adv")
        self.assertEqual(adv["d20"], max(adv["rolls"]))

        engine.set_seed(2026)
        dis = engine.roll_d20("dis")
        self.assertEqual(dis["d20"], min(dis["rolls"]))

    def test_passive_check_formula(self) -> None:
        # 12 -> mod +1, passive 11, plus bonus 2 => total 13.
        out = engine.resolve_check(stat=12, dc=13, bonus=2, use_passive=True)
        self.assertTrue(out["passive"])
        self.assertEqual(out["mod"], 1)
        self.assertEqual(out["total"], 13)
        self.assertTrue(out["success"])

    def test_ability_mod_reference_values(self) -> None:
        self.assertEqual(engine.ability_mod(10), 0)
        self.assertEqual(engine.ability_mod(12), 1)
        self.assertEqual(engine.ability_mod(8), -1)


if __name__ == "__main__":
    unittest.main()
