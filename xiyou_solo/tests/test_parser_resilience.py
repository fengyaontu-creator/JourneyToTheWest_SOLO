from __future__ import annotations

import unittest

from parser import parse_dm_output


class ParserResilienceTests(unittest.TestCase):
    def test_empty_text_no_crash(self) -> None:
        narrative, directive = parse_dm_output("")
        self.assertEqual(narrative, "")
        self.assertIn("need_check", directive)
        self.assertIn("check", directive)
        self.assertIn("enter_combat", directive)

    def test_no_json_no_crash(self) -> None:
        narrative, directive = parse_dm_output("Only narrative text without any directive.")
        self.assertIn("Only narrative text", narrative)
        self.assertFalse(directive["need_check"])

    def test_large_braces_noise_still_fallback_safely(self) -> None:
        text = "Part A: {noise {nested} still noise}\nPart B: Directive JSON\n{invalid: json}"
        _narrative, directive = parse_dm_output(text)
        self.assertFalse(directive["need_check"])
        self.assertEqual(directive["check"]["dc"], 15)


if __name__ == "__main__":
    unittest.main()
