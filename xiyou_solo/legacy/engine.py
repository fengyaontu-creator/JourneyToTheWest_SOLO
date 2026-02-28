from __future__ import annotations

# Compatibility shim: existing imports (`import engine`) still work.
try:
    from xiyou_solo.core.rules import *  # type: ignore # noqa: F401,F403
except ModuleNotFoundError:
    from core.rules import *  # type: ignore # noqa: F401,F403
