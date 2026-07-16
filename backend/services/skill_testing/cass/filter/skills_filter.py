from typing import List, Dict, Any
from .base import AbstractFilterStrategy

class CASSSkillsFilter:
    """The Pipeline Orchestrator for filtering skills."""
    def __init__(self, strategies: List[AbstractFilterStrategy]):
        self.strategies = strategies

    def execute(self, all_skills: List[Dict[str, Any]], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        candidates = all_skills
        for strategy in self.strategies:
            candidates = strategy.filter(candidates, context)
        return candidates