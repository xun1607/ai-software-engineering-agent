from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class AgentState(BaseModel):
    user_context: Dict[str, str]
    plan: List[str] = []
    history: List[Dict] = []
    reflexion: List[str] = []
    
    current_step_idx: int = 0
    current_task: Optional[str] = None
    
    selected_skill: Optional[str] = None
    last_thought: Optional[str] = None
    last_observation: Optional[str] = None
    is_finished: bool = False
    retry_count: int = 0
    final_answer: Optional[str] = None
    
def process_initial_input(code: str, stacktrace: Optional[str], message: str, user_input: str) -> AgentState:
    """ Chuan hoa du lieu dau vao thanh state ban dau"""
    return AgentState(
        user_context={
        "code": code,
        "stacktrace": stacktrace or "",
        "message": message,
        "user_input": user_input},
        plan=[],
        history=[],
        reflexion=[]
)