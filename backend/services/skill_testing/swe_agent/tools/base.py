from abc import ABC, abstractmethod
from typing import Any, Type
from pydantic import BaseModel

class BaseAgentTool(ABC):
    """
    Abstract base class representing an Agent Tool.
    """
    name: str
    description: str
    args_schema: Type[BaseModel]

    @abstractmethod
    def execute(self, sandbox, **kwargs) -> Any:
        """
        Execute the tool inside the sandbox runtime.
        """
        pass
