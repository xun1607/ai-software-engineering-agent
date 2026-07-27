from typing import List, Dict, Any, Callable
from .storage.db_manager import SQLiteDBManager
from .context.context_manager import CASSContextManager
from .filter.skills_filter import CASSSkillsFilter
from .filter.constraint import ConstraintFilterStrategy
from .filter.semantic import SemanticFilterStrategy
from .ranker.ranker import CASSRanker
from .observer.performance_observer import PerformanceObserver
from .proxy.skill_proxy import CASSSkillProxy

class CASS:
    """
    The main Framework Orchestrator
    Provides a simplified interface for Agent Frameworks to use CASS
    """
    def __init__(self, db_path: str = "cass_vault.db"):
        # 1. Infrastructure
        self.db_manager = SQLiteDBManager(db_path)
        self.context_manager = CASSContextManager()
        self.observer = PerformanceObserver(self.db_manager, self.db_manager)

        # 2. Filtering Pipeline
        self.filter_pipeline = CASSSkillsFilter([
            ConstraintFilterStrategy(),
            SemanticFilterStrategy(top_n=10)
        ])

        # 3. Ranking Engine
        self.ranker = CASSRanker(self.db_manager)

    def get_optimized_skills(self, 
                            all_skills: List[Dict[str, Any]], 
                            session_id: str, 
                            subtask: str, 
                            top_k: int = 3) -> List[Dict[str, Any]]:
        """
        The core workflow: Context -> Filter -> Rank -> Top K.
        """
        # Get current environment and session state
        context = self.context_manager.get_full_context(session_id, subtask)
        
        # Step 1: Coarse Filtering (OS, RAM, Blacklist, Semantic)
        candidates = self.filter_pipeline.execute(all_skills, context)
        
        final_skills = self.ranker.rank(candidates, top_k=top_k)
        return final_skills

    def get_optimized_skills_with_details(self, 
                                          all_skills: List[Dict[str, Any]], 
                                          session_id: str, 
                                          subtask: str, 
                                          top_k: int = 3) -> Dict[str, Any]:
        """
        Retrieves optimized skills along with detailed filtering and ranking diagnostics.
        """
        context = self.context_manager.get_full_context(session_id, subtask)
        candidates = self.filter_pipeline.execute(all_skills, context)
        dropped = [s for s in all_skills if s not in candidates]
        final_skills = self.ranker.rank(candidates, top_k=top_k)
        
        return {
            "context": context,
            "all_skills": all_skills,
            "candidates": candidates,
            "dropped_skills": dropped,
            "final_skills": final_skills
        }

    def wrap_skill(self, skill_func: Callable, session_id: str) -> CASSSkillProxy:
        """
        Wraps a real tool function with a CASS Proxy for telemetry.
        """
        return CASSSkillProxy(skill_func, session_id, self.observer)

    def mark_failure(self, session_id: str, skill_name: str):
        """Manual override to blacklist a skill in current session if needed."""
        self.context_manager.register_session_failure(session_id, skill_name)