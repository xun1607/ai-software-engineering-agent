
from backend.services.skill_management.skill_library.registry.registry import SkillRegistry


class SkillManager:
    @staticmethod
    def get_capabilities(registry: SkillRegistry) -> str:
        if not registry:
            return "No skills available"
        all_skills = registry.all_skills()
        categories = {}
        for s in all_skills:
            cat = s.category
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(f"- {s.name}: {s.description}")
        lines = ["SYSTEM CAPABILITIES AND CATEGORIES"]
        for cat, skills in categories.items():
            lines.append(f"\n[{cat.upper()}]")
            lines.extend(skills)
        return "\n".join(lines)