from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional


class ExecutionBridge:
    """AG2 boundary for selecting and invoking AG1 skills."""

    def __init__(self, skills_dir: str | Path | None = None, mock_mode: bool = True):
        self.skills_dir = Path(skills_dir) if skills_dir else Path(__file__).resolve().parents[2] / "skills"
        self.mock_mode = mock_mode
        self._registry = None
        self._executor = None
        self._load_ag1()

    def execute(self, task: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        skill_name = self.select_skill(task)
        if not skill_name:
            return {
                "success": False,
                "skill_id": None,
                "output": None,
                "error": f"No AG1 skill found for capability: {task.get('capability')}",
            }

        if self._registry and self._executor:
            skill = self._registry.get(skill_name)
            if skill:
                try:
                    output = self._executor.run(skill, self._build_input(task, state))
                    return {"success": True, "skill_id": skill_name, "output": output, "error": None}
                except Exception as exc:
                    return {"success": False, "skill_id": skill_name, "output": None, "error": str(exc)}

        return {
            "success": True,
            "skill_id": skill_name,
            "output": {"message": f"[MOCK] Executed {skill_name}", "task": task.get("description")},
            "error": None,
        }

    def select_skill(self, task: Dict[str, Any]) -> Optional[str]:
        requested = task.get("skill_id")
        if requested:
            return requested

        query = " ".join(
            str(part)
            for part in [task.get("capability"), task.get("description"), requested]
            if part
        )
        if self._registry:
            matches = self._registry.search(query, top_k=1)
            if matches:
                return matches[0][0].name

        return requested

    def _load_ag1(self) -> None:
        try:
            from data.skill_library.core.executor import SkillExecutor
            from data.skill_library.core.registry import SkillRegistry

            registry = SkillRegistry(self.skills_dir)
            registry.load_all()
            self._registry = registry
            self._executor = SkillExecutor(registry, mock_mode=self.mock_mode)
        except Exception:
            self._registry = None
            self._executor = None

    @staticmethod
    def _build_input(task: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "user_input": state.get("input", ""),
            "task": task,
            "context": state.get("context_data", {}),
        }
