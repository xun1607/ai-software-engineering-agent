from typing import Any, Dict, List, Optional, Set

from models.task import Task


def htn_recursive_decompose(
    recipe_id: str,
    lookup_table: Dict[str, Dict[str, Any]],
    visited: Optional[Set[str]] = None,
    depends_on: Optional[List[str]] = None,
) -> List[Task]:
    """Recursively decompose a recipe into dependency-aware primitive tasks."""
    visited = visited or set()
    depends_on = depends_on or []
    if recipe_id in visited:
        raise ValueError(f"Cyclic HTN recipe dependency detected: {recipe_id}")

    recipe = lookup_table.get(recipe_id)
    if not recipe:
        raise KeyError(f"Missing recipe referenced by HTN tree: {recipe_id}")

    visited.add(recipe_id)

    if recipe.get("type") == "primitive":
        visited.remove(recipe_id)
        return [Task.from_recipe(recipe_id, recipe, depends_on=depends_on)]

    primitive_tasks: List[Task] = []
    current_dependencies = list(depends_on)
    for sub_id in recipe.get("subtasks", []):
        child_tasks = htn_recursive_decompose(sub_id, lookup_table, visited, current_dependencies)
        primitive_tasks.extend(child_tasks)
        if child_tasks:
            current_dependencies = [child_tasks[-1].id]

    visited.remove(recipe_id)
    return primitive_tasks
