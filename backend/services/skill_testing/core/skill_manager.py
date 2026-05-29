from typing import List
from shared.schemas import SkillRead

class SkillManager:
    @staticmethod
    def get_capabilities(skills: List[SkillRead]) -> str:
        if not skills:
            return "No skills available. Please check the skill management service."
        categories = {}
        for s in skills:
            cat = s.category if s.category else "General"
            if cat not in categories:
                categories[cat] = []

            desc = ""
            if isinstance(s.metadata, dict):
                desc = s.metadata.get('description', '')
            elif hasattr(s, 'metadata_json') and isinstance(s.metadata_json, dict):
                desc = s.metadata_json.get('description', '')

            short_desc = (desc[:80] + '...') if len(desc) > 80 else desc
            categories[cat].append(f"- {s.name}: {short_desc}")

        lines = ["### SYSTEM CAPABILITIES AND CATEGORIES ###"]
        for cat, skill_list in categories.items():
            lines.append(f"\n[{cat.upper()}]")
            lines.extend(skill_list)
            
        return "\n".join(lines)