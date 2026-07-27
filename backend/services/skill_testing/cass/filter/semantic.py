from typing import List, Dict, Any
from .base import AbstractFilterStrategy

class SemanticFilterStrategy(AbstractFilterStrategy):
    """
    semantic filtering. 
    In a real system, this would use Vector Embeddings.
    For the MVP, it uses keyword-based relevance scoring.
    """
    def __init__(self, top_n: int = 10):
        self.top_n = top_n

    def filter(self, skills: List[Dict[str, Any]], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        subtask = context.get("current_subtask", "").lower()
        if not subtask:
            return skills[:self.top_n]

        scored_skills = []
        subtask_words = set(subtask.split())

        for skill in skills:
            # Simple keyword overlap score
            desc = skill.get("description", "").lower()
            name = skill.get("name", "").lower()
            combined = desc + " " + name
            
            score = sum(1 for word in subtask_words if word in combined)
            scored_skills.append((skill, score))

        # Sort by score descending
        scored_skills.sort(key=lambda x: x[1], reverse=True)
        return [item[0] for item in scored_skills[:self.top_n]]