from abc import ABC, abstractmethod
from typing import List, Dict, Any

class AbstractFilterStrategy(ABC):
    """
    Base class for all filtering logic. 
    Each strategy takes a list of skills and returns a subset.
    """
    @abstractmethod
    def filter(self, skills: List[Dict[str, Any]], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Filters skills based on specific criteria and the provided context."""
        pass