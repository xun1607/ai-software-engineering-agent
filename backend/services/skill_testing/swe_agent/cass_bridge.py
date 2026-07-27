from typing import List, Any
from swe_agent.skills.base import AgentSkill
from cass.core import CASS
from cass.adapter.unified_adapter import UnifiedSkillAdapter

class CASSBridge:
    """
    Bridge connecting the SWE Agent components to the CASS Orchestration Layer.
    """
    def __init__(self, db_path: str = "cass_swe_skills.db"):
        self.cass = CASS(db_path)

    def get_optimized_skills(self, skills: List[AgentSkill], session_id: str, subtask: str) -> List[AgentSkill]:
        """
        Filter and rank candidate skills based on subtask context and telemetry.
        """
        skill_map = {s.name: s for s in skills}
        
        # Convert skills to CASS profiles
        profiles = []
        for s in skills:
            profile = UnifiedSkillAdapter.python_to_cass_profile(
                s.execute,
                category=getattr(s, "category", "universal/generic"),
                tags=getattr(s, "tags", []),
                overrides={
                    "name": s.name, 
                    "description": s.description,
                    "version": getattr(s, "version", "1.0.0"),
                    "level": getattr(s, "level", "atomic"),
                    "constraints": s.constraints
                }
            )
            profiles.append(profile)

        # 2. Perform CASS selection logic
        optimized_profiles = self.cass.get_optimized_skills(
            all_skills=profiles,
            session_id=session_id,
            subtask=subtask,
            top_k=3
        )

        return [skill_map[p['name']] for p in optimized_profiles]

    def get_optimized_skills_with_details(self, skills: List[AgentSkill], session_id: str, subtask: str, top_k: int = 3) -> dict:
        """
        Filter and rank candidate skills and return full diagnostic selection report.
        """
        skill_map = {s.name: s for s in skills}
        profiles = []
        for s in skills:
            profile = UnifiedSkillAdapter.python_to_cass_profile(
                s.execute,
                category=getattr(s, "category", "universal/generic"),
                tags=getattr(s, "tags", []),
                overrides={
                    "name": s.name, 
                    "description": s.description,
                    "version": getattr(s, "version", "1.0.0"),
                    "level": getattr(s, "level", "atomic"),
                    "constraints": s.constraints
                }
            )
            profiles.append(profile)

        details = self.cass.get_optimized_skills_with_details(
            all_skills=profiles,
            session_id=session_id,
            subtask=subtask,
            top_k=top_k
        )

        return {
            "context": details["context"],
            "all_skills": [skill_map[p['name']] for p in details["all_skills"] if p['name'] in skill_map],
            "candidates": [skill_map[p['name']] for p in details["candidates"] if p['name'] in skill_map],
            "dropped_skills": [skill_map[p['name']] for p in details["dropped_skills"] if p['name'] in skill_map],
            "selected_skills": [skill_map[p['name']] for p in details["final_skills"] if p['name'] in skill_map]
        }

    def wrap_skill_execution(self, skill_fn: Any, session_id: str) -> Any:
        """
        Wrap skill execution with a Telemetry Proxy to capture latency and success rate.
        """
        return self.cass.wrap_skill(skill_fn, session_id)