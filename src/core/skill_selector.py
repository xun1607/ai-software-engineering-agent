from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class SkillSelection:
    skill_id: Optional[str]
    confidence: float
    reason: str
    alternatives: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SkillSelector:
    """Selects an AG1 skill for a task without executing it."""

    def __init__(self, registry=None, built_in_skills: Optional[Dict[str, Any]] = None):
        self.registry = registry
        self.built_in_skills = built_in_skills or {}

    def select(self, task: Dict[str, Any]) -> SkillSelection:
        requested = task.get("skill_id")
        if requested:
            if requested in self.built_in_skills or self._registry_has(requested):
                return SkillSelection(requested, 1.0, "task pinned explicit skill")
            return SkillSelection(requested, 0.6, "task requested skill not registered; bridge fallback allowed")

        query = " ".join(str(part) for part in [task.get("capability"), task.get("description")] if part)
        if self.registry:
            matches = self.registry.search(query, top_k=3)
            if matches:
                alternatives = [skill.name for skill, _ in matches[1:]]
                return SkillSelection(matches[0][0].name, matches[0][1], "semantic AG1 registry match", alternatives)

        for skill_id in self.built_in_skills:
            if skill_id in query:
                return SkillSelection(skill_id, 0.8, "capability matched built-in skill")

        return SkillSelection(None, 0.0, "no skill matched")

    def _registry_has(self, skill_id: str) -> bool:
        return bool(self.registry and self.registry.get(skill_id))
