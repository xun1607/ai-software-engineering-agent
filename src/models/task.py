from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Literal, Optional


TaskStatus = Literal["pending", "running", "success", "failed", "skipped"]

@dataclass(frozen=True)
class Task:
    """Primitive execution unit produced by AG2 and executed through AG1."""

    id: str
    description: str
    capability: str
    recipe_id: Optional[str] = None
    skill_id: Optional[str] = None
    status: TaskStatus = "pending"
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_recipe(cls, recipe_id: str, recipe: Dict[str, Any]) -> "Task":
        skill_id = recipe.get("skill_id")
        capability = recipe.get("capability") or skill_id or recipe_id
        return cls(
            id=recipe_id,
            recipe_id=recipe_id,
            skill_id=skill_id,
            capability=capability,
            description=recipe.get("description", recipe_id),
            metadata={
                "source": "recipe",
                "recipe_type": recipe.get("type", "primitive"),
            },
        )

    @classmethod
    def from_user_goal(cls, goal: str) -> "Task":
        return cls(
            id="llm_plan_step_1",
            capability="general-software-development",
            description=goal,
            metadata={"source": "llm_fallback"},
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)