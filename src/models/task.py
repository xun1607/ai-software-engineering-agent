from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Literal, Optional


TaskStatus = Literal["pending", "running", "success", "failed", "skipped"]
PlanStatus = Literal["created", "running", "completed", "failed", "replanning"]


@dataclass(frozen=True)
class Task:
    """Capability-first primitive execution unit produced by AG2."""

    id: str
    description: str
    capability: str
    recipe_id: Optional[str] = None
    skill_id: Optional[str] = None
    inputs_required: List[str] = field(default_factory=list)
    expected_outputs: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    status: TaskStatus = "pending"
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_recipe(
        cls,
        recipe_id: str,
        recipe: Dict[str, Any],
        depends_on: Optional[List[str]] = None,
    ) -> "Task":
        skill_id = recipe.get("skill_id")
        capability = recipe.get("capability") or skill_id or recipe_id
        return cls(
            id=recipe_id,
            recipe_id=recipe_id,
            skill_id=skill_id,
            capability=capability,
            description=recipe.get("description", recipe_id),
            inputs_required=recipe.get("inputs_required", []),
            expected_outputs=recipe.get("expected_outputs", []),
            depends_on=depends_on or recipe.get("depends_on", []),
            metadata={
                "source": "recipe",
                "recipe_type": recipe.get("type", "primitive"),
            },
        )

    @classmethod
    def from_user_goal(cls, goal: str) -> "Task":
        return cls(
            id="fallback_plan_step_1",
            capability="llm-software-engineering",
            skill_id="llm-software-engineer-skill",
            description=goal,
            expected_outputs=["answer"],
            metadata={"source": "llm_fallback"},
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Plan:
    id: str
    goal: str
    tasks: List[Task]
    strategy: str
    route: Dict[str, Any] = field(default_factory=dict)
    status: PlanStatus = "created"

    @property
    def task_count(self) -> int:
        return len(self.tasks)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["tasks"] = [task.to_dict() for task in self.tasks]
        return data
