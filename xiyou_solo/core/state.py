from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class GameState:
    session_id: str
    player_id: Optional[str] = None
    language: str = "zh"
    mode: str = "fast15"
    threat: int = 0
    player_name: str = "hero"
    race_id: str = "human"
    class_id: str = "martial"
    stats: Dict[str, int] = field(default_factory=lambda: {"body": 10, "wit": 10, "spirit": 10, "luck": 10})
    hp: int = 12
    max_hp: int = 12
    gold: int = 50
    inventory: List[str] = field(default_factory=list)
    location: Dict[str, str] = field(default_factory=lambda: {"zh": "路边茶摊", "en": "Roadside Tea Stall"})
    quest_title: Dict[str, str] = field(default_factory=lambda: {"zh": "旅途初章", "en": "First Chapter"})
    current_goal: Dict[str, str] = field(default_factory=lambda: {"zh": "观察局势并收集线索", "en": "Observe and collect clues"})
    turn: int = 0
    progress: int = 0
    threat_level: int = 1
    flags: List[str] = field(default_factory=list)
    combat_state: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "player_id": self.player_id,
            "language": self.language,
            "mode": self.mode or "fast15",
            "threat": int(self.threat),
            "player": {
                "name": self.player_name,
                "race_id": self.race_id,
                "class_id": self.class_id,
                "stats": dict(self.stats),
                "hp": int(self.hp),
                "max_hp": int(self.max_hp),
                "gold": int(self.gold),
                "inventory": list(self.inventory),
            },
            "story": {
                "location": dict(self.location),
                "quest_title": dict(self.quest_title),
                "current_goal": dict(self.current_goal),
                "turn": int(self.turn),
                "progress": int(self.progress),
                "threat_level": int(self.threat_level),
                "flags": list(self.flags),
            },
            "combat_state": dict(self.combat_state) if isinstance(self.combat_state, dict) else {},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GameState":
        player = data.get("player", {}) if isinstance(data.get("player"), dict) else {}
        story = data.get("story", {}) if isinstance(data.get("story"), dict) else {}
        raw_stats = player.get("stats", {})
        stats = {"body": 10, "wit": 10, "spirit": 10, "luck": 10}
        if isinstance(raw_stats, dict):
            for key in stats:
                val = raw_stats.get(key, stats[key])
                stats[key] = int(val) if isinstance(val, (int, float)) else stats[key]

        mode = str(data.get("mode", "fast15")).strip() or "fast15"
        raw_threat = data.get("threat", 0)
        try:
            threat = int(raw_threat)
        except (TypeError, ValueError):
            threat = 0

        return cls(
            session_id=str(data.get("session_id", "")).strip(),
            player_id=(str(data.get("player_id", "")).strip() or None),
            language=str(data.get("language", "zh")),
            mode=mode,
            threat=max(0, threat),
            player_name=str(player.get("name", "hero")),
            race_id=str(player.get("race_id", "human")),
            class_id=str(player.get("class_id", "martial")),
            stats=stats,
            hp=int(player.get("hp", 12)),
            max_hp=int(player.get("max_hp", 12)),
            gold=int(player.get("gold", 50)),
            inventory=[str(x) for x in player.get("inventory", [])] if isinstance(player.get("inventory", []), list) else [],
            location=story.get("location", {"zh": "路边茶摊", "en": "Roadside Tea Stall"})
            if isinstance(story.get("location"), dict)
            else {"zh": "路边茶摊", "en": "Roadside Tea Stall"},
            quest_title=story.get("quest_title", {"zh": "旅途初章", "en": "First Chapter"})
            if isinstance(story.get("quest_title"), dict)
            else {"zh": "旅途初章", "en": "First Chapter"},
            current_goal=story.get("current_goal", {"zh": "观察局势并收集线索", "en": "Observe and collect clues"})
            if isinstance(story.get("current_goal"), dict)
            else {"zh": "观察局势并收集线索", "en": "Observe and collect clues"},
            turn=int(story.get("turn", 0)),
            progress=int(story.get("progress", 0)),
            threat_level=int(story.get("threat_level", 1)),
            flags=[str(x) for x in story.get("flags", [])] if isinstance(story.get("flags", []), list) else [],
            combat_state=data.get("combat_state", {}) if isinstance(data.get("combat_state"), dict) else {},
        )


def new_game_state(session_id: str, player_id: Optional[str] = None, language: str = "zh") -> GameState:
    return GameState(
        session_id=session_id,
        player_id=player_id,
        language=language if language in {"zh", "en"} else "zh",
        mode="fast15",
        threat=0,
    )
