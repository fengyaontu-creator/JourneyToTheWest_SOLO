from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol


@dataclass
class LLMCallResult:
    narrative: str
    directive: Dict[str, Any]
    raw_text: str
    latency_ms: int
    tokens: Optional[int] = None


class LLMProvider(Protocol):
    def generate(self, dm_system: str, dm_context: str, player_input: str) -> LLMCallResult:
        ...

