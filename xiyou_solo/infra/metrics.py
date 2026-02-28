from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class TurnMetric:
    latency_ms: int
    tokens: Optional[int] = None


@dataclass
class MetricsCollector:
    turns: List[TurnMetric] = field(default_factory=list)

    def record(self, latency_ms: int, tokens: Optional[int] = None) -> TurnMetric:
        metric = TurnMetric(latency_ms=int(latency_ms), tokens=tokens if tokens is None else int(tokens))
        self.turns.append(metric)
        return metric


def format_metric_line(latency_ms: int, tokens: Optional[int]) -> str:
    if tokens is None:
        return f"[metrics] latency={int(latency_ms)}ms tokens=n/a"
    return f"[metrics] latency={int(latency_ms)}ms tokens={int(tokens)}"

