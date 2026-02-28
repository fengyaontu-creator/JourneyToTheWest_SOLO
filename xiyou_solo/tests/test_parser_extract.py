from __future__ import annotations

import unittest

from xiyou_solo.parser import parse_dm_output


class ParserExtractTests(unittest.TestCase):
    def test_extract_from_json_code_block(self) -> None:
        text = """Part A: Narrative
hello

```json
{"need_check": true, "check": {"attribute": "Mind", "dc": 15, "reason": "ok"}, "enter_combat": false}
```
"""
        _, directive = parse_dm_output(text)
        self.assertTrue(directive["need_check"])
        self.assertEqual(directive["check"]["attribute"], "Mind")
        self.assertEqual(directive["check"]["dc"], 15)

    def test_extract_from_part_b_without_code_block(self) -> None:
        text = """Part A: Narrative
something
Part B: Directive JSON
{"need_check": false, "check": {"attribute": "Body", "dc": 10, "reason": "ok"}, "enter_combat": false}
"""
        _, directive = parse_dm_output(text)
        self.assertFalse(directive["need_check"])
        self.assertEqual(directive["check"]["attribute"], "Body")
        self.assertEqual(directive["check"]["dc"], 10)

    def test_narrative_braces_do_not_break_extract(self) -> None:
        text = """Part A: Narrative
你看到 {古旧符箓}，风声忽紧。
Part B: Directive JSON
{"need_check": true, "check": {"attribute": "Spirit", "dc": 20, "reason": "ok"}, "enter_combat": false}
"""
        _, directive = parse_dm_output(text)
        self.assertTrue(directive["need_check"])
        self.assertEqual(directive["check"]["attribute"], "Spirit")
        self.assertEqual(directive["check"]["dc"], 20)


if __name__ == "__main__":
    unittest.main()
