from typing import Dict, List, Optional
from .base import AgentSkill

class SkillRegistry:
    """
    Registry managing the lifecycle and retrieval of Agent Skills.
    Registers and provides candidate skills to the CASS optimizer.
    """
    def __init__(self):
        self._skills: Dict[str, AgentSkill] = {}

    def register(self, skill: AgentSkill):
        """
        Register a new skill into the system.
        """
        if skill.name in self._skills:
            print(f"⚠️ Warning: Skill '{skill.name}' already exists. Overwriting...")
        self._skills[skill.name] = skill

    def get_skill(self, name: str) -> Optional[AgentSkill]:
        """
        Retrieve a registered skill by its name.
        """
        return self._skills.get(name)

    def get_all_skills(self) -> List[AgentSkill]:
        """
        Return all registered skills as a list.
        """
        return list(self._skills.values())

    def __len__(self):
        return len(self._skills)