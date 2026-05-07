from typing import TypedDict, List
import operator
from typing_extensions import Annotated


class AgentState(TypedDict):
    input: str
    plan: List[str]
    results: Annotated[List[str], operator.add]
    current_step: int
    context: dict