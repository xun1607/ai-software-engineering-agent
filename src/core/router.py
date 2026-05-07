from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, Literal, Optional


FallbackMode = Literal["none", "llm_plan"]


@dataclass(frozen=True)
class RouteDecision:
    recipe_id: Optional[str]
    confidence: float
    reason: str
    fallback_mode: FallbackMode

    @property
    def matched(self) -> bool:
        return self.recipe_id is not None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def route_recipe(user_input: str, recipes: Dict[str, Dict[str, Any]], threshold: float = 0.12) -> RouteDecision:
    """Route user intent to a recipe or explicit fallback planning mode."""
    query_tokens = _tokens(user_input)
    if not query_tokens:
        return RouteDecision(None, 0.0, "empty input", "llm_plan")

    best_id: Optional[str] = None
    best_score = 0.0

    for recipe in _candidate_recipes(recipes.values()):
        recipe_tokens = _tokens(
            " ".join(
                [
                    recipe.get("recipe_id", ""),
                    recipe.get("description", ""),
                    " ".join(recipe.get("tags", [])),
                ]
            )
        )
        if not recipe_tokens:
            continue

        overlap = len(query_tokens & recipe_tokens)
        score = overlap / math.sqrt(len(query_tokens) * len(recipe_tokens))
        if score > best_score:
            best_score = score
            best_id = recipe["recipe_id"]

    if best_id and best_score >= threshold:
        return RouteDecision(best_id, best_score, "semantic recipe match", "none")
    return RouteDecision(None, best_score, "no recipe above threshold", "llm_plan")


def _tokens(text: str) -> set[str]:
    tokens = set()
    for token in re.findall(r"[a-zA-Z0-9_]+", text.lower()):
        tokens.add(token)
        if len(token) > 3 and token.endswith("s"):
            tokens.add(token[:-1])
    return tokens


def _candidate_recipes(recipes: Iterable[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
    for recipe in recipes:
        if recipe.get("type") == "composite":
            yield recipe
