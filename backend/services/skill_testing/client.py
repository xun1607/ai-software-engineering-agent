from asyncio.log import logger

import httpx
from typing import Dict, Any, List

from shared.schemas import SkillRead

class SkillManagementClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)

    async def fetch_all_skills(self) -> List[SkillRead]:
        try:
            response = await self.client.get("/api/v1/skills")
            response.raise_for_status()
            data = response.json()
            items = data.get("items", data)
            return [SkillRead(**item) for item in items]
        except httpx.HTTPStatusError as e:
            logger.error(f"Lỗi API từ Skill Management: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"Lỗi kết nối đến Skill Management: {str(e)}")
            raise
    async def close(self):
        await self.client.aclose()