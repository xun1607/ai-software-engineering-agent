# from typing import List, Dict, Any, Optional, Annotated
# from pydantic import BaseModel
# import operator

# class AgentState(BaseModel):
#     task: str
#     plan: List[Dict[str, Any]]
#     current_step_index: int = 0
#     past_steps: Annotated[List[tuple], operator.add]
#     status: str = "init"
#     final_result: Optional[Any] = None
#     error: Optional[str] = None
    
from typing import TypedDict, Annotated, List, Optional, Any, Dict
import operator

class AgentState(TypedDict):
    """
    State quản lý toàn bộ luồng thực thi của Agent Orchestrator.
    """
    task: str
    plan: Optional[List[Any]]
    current_step_index: int
    # Lưu kết quả các bước đã chạy: [(action_name, observation_result)]
    past_steps: Annotated[List[tuple[str, str]], operator.add]
    # Trạng thái hiện tại: 'planning', 'awaiting_approval', 'executing', 'completed', 'error'
    status: str
    final_result: Optional[str]
    error: Optional[str]
