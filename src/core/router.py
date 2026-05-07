from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Literal, Optional, Tuple


FallbackMode = Literal["none", "llm_plan"]
TOKEN_TOP_K = 3
SEMANTIC_THRESHOLD = 0.65


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


def route_recipe(
    user_input: str,
    recipes: Dict[str, Dict[str, Any]],
    threshold: float = SEMANTIC_THRESHOLD,
) -> RouteDecision:
    """Hybrid route user intent to a recipe or explicit fallback planning mode."""
    token_candidates = _top_token_candidates(user_input, recipes)
    if not token_candidates:
        return RouteDecision(None, 0.0, "no token candidates; using LLM planning", "llm_plan")

    best_token_recipe, best_token_score = token_candidates[0]
    if best_token_score == 1.0:
        return RouteDecision(
            best_token_recipe["recipe_id"],
            best_token_score,
            "perfect token match; skipped semantic rerank",
            "none",
        )

    try:
        semantic_recipe, semantic_score = _semantic_rerank(user_input, token_candidates)
    except Exception as exc:
        return RouteDecision(
            None,
            best_token_score,
            f"semantic rerank unavailable ({exc}); using LLM planning",
            "llm_plan",
        )

    if semantic_recipe and semantic_score >= threshold:
        return RouteDecision(
            semantic_recipe["recipe_id"],
            semantic_score,
            "semantic embedding rerank match",
            "none",
        )

    return RouteDecision(
        None,
        semantic_score,
        "semantic score below threshold; using LLM planning",
        "llm_plan",
    )


def _top_token_candidates(
    user_input: str,
    recipes: Dict[str, Dict[str, Any]],
    top_k: int = TOKEN_TOP_K,
) -> List[Tuple[Dict[str, Any], float]]:
    query_tokens = _tokens(user_input)
    if not query_tokens:
        return []

    scored: List[Tuple[Dict[str, Any], float]] = []
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
        if query_tokens.issubset(recipe_tokens):
            score = 1.0
        if score > 0:
            scored.append((recipe, score))

    return sorted(scored, key=lambda item: item[1], reverse=True)[:top_k]


def _semantic_rerank(
    user_input: str,
    token_candidates: List[Tuple[Dict[str, Any], float]],
) -> Tuple[Optional[Dict[str, Any]], float]:
    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    user_vector = embeddings.embed_query(user_input)
    descriptions = [recipe.get("description", "") for recipe, _ in token_candidates]
    description_vectors = embeddings.embed_documents(descriptions)

    best_index = -1
    best_score = 0.0
    for index, description_vector in enumerate(description_vectors):
        score = _cosine_similarity(user_vector, description_vector)
        if score > best_score:
            best_score = score
            best_index = index

    if best_index < 0:
        return None, 0.0
    return token_candidates[best_index][0], best_score


def _cosine_similarity(left: List[float], right: List[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def _tokens(text: str) -> set[str]:
    tokens = set()
    for token in re.findall(r"[\w]+", text.lower(), re.UNICODE):
        tokens.add(token)
        if len(token) > 3 and token.endswith("s"):
            tokens.add(token[:-1])
    return tokens


def _candidate_recipes(recipes: Iterable[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
    for recipe in recipes:
        if recipe.get("type") == "composite":
            yield recipe
