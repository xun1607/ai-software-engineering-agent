from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class ExecutionRecord:
    """Represents a single raw execution event of a skill"""
    session_id: str
    skill_name: str
    latency_ms: float
    cost: float
    success: bool
    error_message: Optional[str] = None

class AbstractTelemetryStore(ABC):
    """Interface for saving raw, detailed execution logs."""
    
    @abstractmethod
    def save_log(self, record: ExecutionRecord) -> None:
        """Save a detailed log of a skill execution."""
        pass

    @abstractmethod
    def get_recent_logs(self, skill_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieves recent logs for debugging / analysis"""
        pass

class AbstractSkillMetricsStore(ABC):
    """Interface for managing aggregated performance scores (The 'Reputation' layer)"""

    @abstractmethod
    def get_metrics(self, skill_names: List[str]) -> Dict[str, Dict[str, Any]]:
        """Fetches Bayesian parameters (alpha, beta) and averages for a list of skills"""
        pass
        
    @abstractmethod
    def update_metrics(self, skill_name: str, latency_ms: float, cost: float, success: bool) -> None:
        """Updates the cumulative scores using incremental moving averages and Beta distribution"""
        pass