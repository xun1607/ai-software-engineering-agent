from sentence_transformers import SentenceTransformer, util
from typing import Dict, List, Optional, Tuple, Any
import time

MODEL_NAME = "all-MiniLM-L6-v2"
class SkillSemanticRegistry:
    def __init__(self, model_name: str = MODEL_NAME):
        try:
            self.model = SentenceTransformer(model_name, local_files_only=True)
            print(f"✅ Loaded SentenceTransformer '{model_name}' from local cache.")
        except Exception:
            print(f"⚠️ Local cache not found for '{model_name}'. Fetching from Hugging Face Hub...")
            self.model = SentenceTransformer(model_name)
        self._embeddings = None
        self.name_to_id_map = {}
        self.capabilities_manifest = ""
        self._skills_cache: list[str] = []  # Luu tru ten skill
        
        # Summary and Detail caching layers (TASK_2A)
        self._summary_cache: Dict[str, Dict[str, Any]] = {}
        self._detail_cache: Dict[str, Dict[str, Any]] = {}
        self.last_refresh_time: Optional[float] = None
        
    def build_index(self, tools_data: list):
        """Tao index vector cho skill list tu cache Tieu de (Summary)"""
        if not tools_data:
            return
        self._skills_cache = []
        self._summary_cache = {}
        summary_texts = []
        lines = ["### SYSTEM AVAILABLE TOOLS AND CAPABILITIES ###"]
        
        for tool in tools_data:
            if isinstance(tool, dict):
                tool_dict = tool
            elif hasattr(tool, "model_dump"):
                tool_dict = tool.model_dump()
            elif hasattr(tool, "dict"):
                tool_dict = tool.dict()
            else:
                tool_dict = getattr(tool, "__dict__", {})
            
            name = tool_dict.get("name")
            skill_id = tool_dict.get("skill_id") or tool_dict.get("id")
            desc = tool_dict.get("description") or tool_dict.get("metadata", {}).get("description", "")
            tags = tool_dict.get("tags", [])
            category = tool_dict.get("category", "")
            level = tool_dict.get("level", "atomic")
            updated_at = tool_dict.get("updated_at")
            
            # Store in Summary Cache
            self._summary_cache[name] = {
                "id": skill_id,
                "name": name,
                "description": desc,
                "tags": tags,
                "category": category,
                "level": level,
                "updated_at": updated_at
            }
            self.name_to_id_map[name] = skill_id
            self._skills_cache.append(name)
            
            text_context = f"{name} {desc}"
            summary_texts.append(text_context.lower())
            
            # Format metadata tóm tắt cho Planner (TASK_3A)
            lines.append(f"- Tool Name: {name} (ID: {skill_id})")
            lines.append(f"  Description: {desc}")
            lines.append(f"  Category: {category} | Tags: {', '.join(tags) if isinstance(tags, list) else str(tags)}")
            
        self.capabilities_manifest = "\n".join(lines)
        self._embeddings = self.model.encode(summary_texts, convert_to_tensor=True)
        print(f"✅ [REGISTRY] Đã nạp thành công và xây dựng ma trận Vector cho {len(tools_data)} kỹ năng từ Cache Tầng 1.")
        
    def search(self, query: str, top_k: int = 1) -> list[tuple[str, float]]:
        if self._embeddings is None or not self._skills_cache:
            return []
        query_embedding = self.model.encode(query.lower(), convert_to_tensor=True)
        hits = util.semantic_search(query_embedding, self._embeddings, top_k=top_k)[0]
        results = []
        for hit in hits:
            idx = hit['corpus_id']
            score = hit['score']
            results.append((self._skills_cache[idx], score))
        return results
    
    async def get_skill_detail(self, skill_name_or_id: str) -> dict:
        """Tải lười (Lazy Load) chi tiết kỹ năng từ Cache Tầng 2 hoặc gọi AG1"""
        skill_id = self.get_id_by_name(skill_name_or_id) or skill_name_or_id
        if skill_id in self._detail_cache:
            return self._detail_cache[skill_id]
            
        url = f"http://127.0.0.1:8001/skills/{skill_id}"
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=5.0)
                if resp.status_code == 200:
                    detail = resp.json()
                    self._detail_cache[skill_id] = detail
                    return detail
        except Exception as e:
            print(f"⚠️ [REGISTRY] Lazy load skill detail thất bại cho {skill_id}: {e}")
            
        # Trả về summary metadata nếu không tải được detail
        summary_val = next((v for k, v in self._summary_cache.items() if v["id"] == skill_id or k == skill_name_or_id), None)
        return summary_val or {}
        
    async def refresh_cache(self, tools_data: list = None):
        """Hook làm mới cache (TASK_2A)"""
        if tools_data:
            self.build_index(tools_data)
        self.last_refresh_time = time.time()
        print("🔄 [REGISTRY] Cache refresh hook triggered.")

    def get_all_tools(self) -> list[str]:
        return self._skills_cache
    
    def get_id_by_name(self, name: str) -> str:
        return self.name_to_id_map.get(name)

semantic_registry = SkillSemanticRegistry()