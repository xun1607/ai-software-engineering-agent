import httpx
from typing import Dict, Any

class BackendClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()

    async def call_skill(self, skill_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/skills/{skill_id}/execute"
        async with self.client as client:
            response = await client.post(url, json=input_data)
            response.raise_for_status()
            return response.json()

    async def close(self):
        await self.client.aclose()