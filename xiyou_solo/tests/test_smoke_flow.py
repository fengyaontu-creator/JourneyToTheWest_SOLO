from __future__ import annotations

import unittest

import engine
from parser import parse_dm_output


class SmokeFlowTests(unittest.TestCase):
    def test_parse_then_resolve_check_offline(self) -> None:
        text = """Part A: Narrative
You inspect the corridor.

```json
{
  "need_check": true,
  "check": {"attribute": "Mind", "dc": 15, "reason": "spot hidden trace"},
  "enter_combat": false,
  "offer_actions": ["Inspect", "Listen"]
}
```
"""
        _narrative, directive = parse_dm_output(text)
        self.assertTrue(directive["need_check"])
        self.assertEqual(directive["check"]["attribute"], "Mind")
        self.assertEqual(directive["check"]["dc"], 15)

        engine.set_seed(7)
        # Mind maps to wit in runtime; here we only verify check mechanics are executable.
        result = engine.resolve_check(stat=12, dc=directive["check"]["dc"], bonus=0, mode="normal")
        self.assertIn("total", result)
        self.assertIn("success", result)
        outcome = engine.outcome(result["total"], directive["check"]["dc"])
        self.assertIn(
            outcome,
            {"outcome_critical", "outcome_success", "outcome_partial", "outcome_fail", "outcome_fumble"},
        )


if __name__ == "__main__":
    unittest.main()
