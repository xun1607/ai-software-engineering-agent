import operator
from typing import Any, Dict, List, Literal, Optional, TypedDict

from typing_extensions import Annotated


ExecutionStatus = Literal["planning", "running", "completed", "failed"]


class ExecutionResult(TypedDict, total=False):
    task_id: str
    skill_id: Optional[str]
    capability: str
    output: Any
    success: bool
    error: Optional[str]
    evaluation: Dict[str, Any]


class AgentState(TypedDict, total=False):
    input: str
    plan: List[Dict[str, Any]]
    current_step: int
    matched_recipe_id: Optional[str]
    planning_strategy: str
    status: ExecutionStatus
    results: Annotated[List[ExecutionResult], operator.add]
    context_data: Annotated[Dict[str, Any], operator.ior] # lưu dữ liệu thô, hội thoại,...
    artifacts: Annotated[Dict[str, str], operator.ior] # Lưu sản phẩm cuối (file code, test case) để báo cáo
    errors: Annotated[List[str], operator.add]
