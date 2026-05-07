import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


def default_recipe_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "recipes.json"


@lru_cache(maxsize=4)
def load_recipes(path: str | None = None) -> Dict[str, Dict[str, Any]]:
    recipe_path = Path(path) if path else default_recipe_path()
    with recipe_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    return {item["recipe_id"]: item for item in data}


def get_recipe(recipe_id: str, recipes: Optional[Dict[str, Dict[str, Any]]] = None) -> Optional[Dict[str, Any]]:
    return (recipes or load_recipes()).get(recipe_id)


def iter_recipes(recipes: Optional[Dict[str, Dict[str, Any]]] = None) -> Iterable[Dict[str, Any]]:
    return (recipes or load_recipes()).values()
