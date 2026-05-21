from typing import List, Dict, Any, TypedDict
from pydantic import BaseModel, Field

class AgentState(TypedDict):
    user_goal: str
    chat_history: str
    
    execution_plan: List[Dict[str, Any]]
    current_step_index: int              # Chỉ số của bước hiện tại đang xử lý (0, 1, 2...)
    
    current_selected_skill_id: str | None
    current_selected_skill_name: str | None
    
    latest_step_output: Dict[str, Any] | None
    accumulated_context: Dict[str, Any] 
    
    latest_error_feedback: str | None
    current_retry_count: int
    
    extracted_arguments: Dict[str, Any] | None
    
    final_response: str | None