import operator
from typing import Any, Dict, List, Literal, Optional, TypedDict

from typing_extensions import Annotated


ExecutionStatus = Literal["planning", "running", "completed", "failed", "replanning"]


class ExecutionResult(TypedDict, total=False):
    task_id: str
    skill_id: Optional[str]
    capability: str
    input: Dict[str, Any]
    output: Any
    success: bool
    error: Optional[str]
    evaluation: Dict[str, Any]
    token_usage: int


class ContextMemory(TypedDict, total=False):
    user_goal: str
    route_decision: Dict[str, Any]
    task_results: Dict[str, ExecutionResult]
    facts: Dict[str, Any]
    last_output: Any


class SchedulerState(TypedDict, total=False):
    current_step: int
    retry_count: int
    max_retries: int
    next_action: str
    replan_reason: Optional[str]


class AgentState(TypedDict, total=False):
    input: str
    plan: Dict[str, Any]
    matched_recipe_id: Optional[str]
    planning_strategy: str
    status: ExecutionStatus
    results: Annotated[List[ExecutionResult], operator.add]
    context_memory: ContextMemory
    artifacts: Dict[str, Any]
    errors: Annotated[List[str], operator.add]
    scheduler: SchedulerState
    retry_count: int
    last_error: str
    metrics: Dict[str, Any]
    is_replanned: bool
