from typing import Annotated, List, Dict, Any, TypedDict, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]  #chat history
    iteration_count: int
    current_file: Optional[str]
    
    is_valid: bool
    feedback: Optional[str]
    
    telemetry: Dict[str, Any]