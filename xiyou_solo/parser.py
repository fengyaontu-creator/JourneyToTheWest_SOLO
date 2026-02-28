"""Public re-export of directive parsing utilities.

Provides the stable import path ``xiyou_solo.parser`` used by tests and
external callers, backed by the implementation in ``llm.directive_parser``.
"""
from xiyou_solo.llm.directive_parser import ALLOWED_ATTR, ALLOWED_DC, parse_dm_output

__all__ = ["ALLOWED_ATTR", "ALLOWED_DC", "parse_dm_output"]
