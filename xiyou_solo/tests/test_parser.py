from __future__ import annotations

import unittest

from parser import ALLOWED_ATTR, ALLOWED_DC, parse_dm_output


class ParserTests(unittest.TestCase):
    def test_parse_with_json_codeblock(self) -> None:
        text = """Part A: Narrative
Something happened.

```json
{
  "need_check": true,
  "check": {"attribute": "Mind", "dc": 15, "reason": "inspect"},
  "enter_combat": false
}
```
"""
        narrative, directive = parse_dm_output(text)
        self.assertNotIn('"need_check"', narrative)
        self.assertNotIn("```json", narrative.lower())
        self.assertIn("need_check", directive)
        self.assertIn("check", directive)
        self.assertIn("enter_combat", directive)
        self.assertIn(directive["check"]["attribute"], ALLOWED_ATTR)
        self.assertIn(directive["check"]["dc"], ALLOWED_DC)

    def test_parse_without_codeblock_partb_balanced(self) -> None:
        text = """Part A: Narrative
你看到 {古旧符箓}，风声忽紧。
Part B: Directive JSON
{
  "need_check": false,
  "check": {"attribute": "Body", "dc": 10, "reason": "steady"},
  "enter_combat": false
}
"""
        _narrative, directive = parse_dm_output(text)
        self.assertFalse(directive["need_check"])
        self.assertEqual(directive["check"]["attribute"], "Body")
        self.assertEqual(directive["check"]["dc"], 10)

    def test_parse_invalid_json_fallback(self) -> None:
        text = """Part A: Narrative
Part B: Directive JSON
{"need_check": true, "check": {"attribute": "Mind", "dc": 15, "reason": "x"}, "enter_combat": false
"""
        _narrative, directive = parse_dm_output(text)
        self.assertFalse(directive["need_check"])
        self.assertEqual(directive["check"]["attribute"], "Luck")
        self.assertEqual(directive["check"]["dc"], 15)

    def test_guardrail_filters_illegal_fields(self) -> None:
        text = """Part B: Directive JSON
{
  "need_check": true,
  "check": {"attribute": "Mind", "dc": 15, "reason": "x"},
  "enter_combat": false,
  "gold_change": 999,
  "hp_change": -100,
  "state_update": {"inventory_change": ["god_item"]}
}
"""
        _narrative, directive = parse_dm_output(text)
        self.assertNotIn("gold_change", directive)
        self.assertNotIn("hp_change", directive)
        self.assertNotIn("state_update", directive)
        self.assertNotIn("inventory_change", directive)

    def test_attribute_dc_coercion(self) -> None:
        text = """Part B: Directive JSON
{
  "need_check": true,
  "check": {"attribute": "Intelligence", "dc": 13, "reason": "x"},
  "enter_combat": false
}
"""
        _narrative, directive = parse_dm_output(text)
        self.assertEqual(directive["check"]["attribute"], "Luck")
        self.assertEqual(directive["check"]["dc"], 15)


if __name__ == "__main__":
    unittest.main()
