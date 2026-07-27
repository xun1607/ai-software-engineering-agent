from services.skill_testing.core.registry import semantic_registry

class SkillLoader:
    """Tải thông tin chi tiết SOP của kỹ năng từ Thư viện Kỹ năng."""
    @staticmethod
    async def load(skill_name: str) -> dict:
        return await semantic_registry.get_skill_detail(skill_name)
