from typing import TypedDict, Annotated, List, Optional, Any, Dict
import operator

from pydantic import BaseModel


class AgentState(BaseModel):
    user_context: Dict[str, str]
    plan: list[str] = []
    history: list[Dict[str, Any]] = []
    reflection: list[str] = []
    
    current_step_idx: int = 0
    current_task: Optional[str] = None
    
    selected_skill: Optional[str] = None
    last_thought: Optional[str] = None
    last_observation: Optional[str] = None
    is_finished: bool = False
    retry_count: int = 0
    final_answer: Optional[str] = None
    
    goal: Optional[str] = None  
    missing_skills_log: list[str] = []
    # exception
    replan_count: int = 0
    max_replans: int = 3
    
    max_total_steps: int = 12
    step_count: int = 0
    