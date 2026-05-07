from __future__ import annotations

import time
from typing import Any, Dict


COST_PER_1K_TOKENS = 0.02


def calculate_cost(tokens: int) -> float:
    return (tokens / 1000) * COST_PER_1K_TOKENS


def estimate_tokens(value: Any) -> int:
    text = str(value)
    return max(1, len(text.split()))


def initial_metrics(existing: Dict[str, Any] | None = None) -> Dict[str, Any]:
    metrics = dict(existing or {})
    metrics.setdefault("total_tokens", 0)
    metrics.setdefault("estimated_cost", 0.0)
    metrics.setdefault("start_time", time.time())
    metrics.setdefault("total_retries", 0)
    metrics.setdefault("replan_count", 0)
    return metrics


def add_token_usage(metrics: Dict[str, Any], tokens: int) -> Dict[str, Any]:
    updated = initial_metrics(metrics)
    updated["total_tokens"] += tokens
    updated["estimated_cost"] = calculate_cost(updated["total_tokens"])
    return updated
