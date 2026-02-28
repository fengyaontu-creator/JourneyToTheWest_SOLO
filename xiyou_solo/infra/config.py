from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class AppConfig:
    provider: str = "mock"
    openrouter_model: str = "openai/gpt-4o-mini"

    @classmethod
    def from_env(cls, provider: str = "mock") -> "AppConfig":
        model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini").strip() or "openai/gpt-4o-mini"
        return cls(provider=provider, openrouter_model=model)

