from abc import ABC, abstractmethod
from typing import Dict, Any, List, Type
from pydantic import BaseModel

class AgentSkill(ABC):
    """
    Abstract base class representing an Agent Skill.
    Aligns with the SKILL.md specification (YAML frontmatter).
    """
    name: str
    description: str
    version: str = "1.0.0"
    category: str = "universal/generic"
    level: str = "atomic"
    tags: List[str] = []
    args_schema: Type[BaseModel]
    
    constraints: Dict[str, Any] = {
        "host": {"os": []},
        "resources": {"memory": "128MB"}
    }

    @abstractmethod
    def execute(self,  sandbox: Any, **kwargs) -> Any:
        """
        Execute the skill with the given parameters inside the sandbox.
        """
        pass
    
    def to_openai_tool(self) -> Dict[str, Any]:
        """
        Convert the skill metadata to OpenAI JSON tool schema format for the LLM.
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.args_schema.model_json_schema()
            }
        }