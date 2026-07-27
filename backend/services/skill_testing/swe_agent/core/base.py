from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class SandboxResponse(BaseModel):
    """response schema from the sandbox execution"""
    stdout: str
    stderr: str
    exit_code: int
    metadata: Dict[str, Any] = {}

class AbstractSandbox(ABC):
    """Interface for the isolated execution environment"""
    
    @abstractmethod
    def execute_command(self, command: str, timeout: int = 60) -> SandboxResponse:
        pass

    @abstractmethod
    def write_file(self, path: str, content: str) -> None:
        pass

    @abstractmethod
    def read_file(self, path: str) -> str:
        pass

    @abstractmethod
    def get_environment_info(self) -> Dict[str, Any]:
        """Provide data for CASS (OS, RAM, etc.)."""
        pass