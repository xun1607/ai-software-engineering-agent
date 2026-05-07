from __future__ import annotations
from typing import Any, Dict, Optional

def evaluate_result(task: Dict[str, Any], output: Any, error: Optional[str] = None) -> Dict[str, Any]:
    """Evaluate one task result for scheduler decisions."""
    success = error is None and output is not None
    return {
        "success": success,
        "retryable": bool(error),
        "score": 1.0 if success else 0.0,
        "reason": "completed" if success else error or "empty output",
        "task_id": task.get("id"),
    }