import os
import re
import yaml
import time
from typing import Dict, List, Optional, Tuple, Any
from sentence_transformers import SentenceTransformer, util

MODEL_NAME = "all-MiniLM-L6-v2"
class SkillSemanticRegistry:
    def __init__(self, model_name: str = MODEL_NAME):
        try:
            self.model = SentenceTransformer(model_name, local_files_only=True)
            print(f"[REGISTRY] Loaded SentenceTransformer '{model_name}' from local cache.")
        except Exception:
            print(f"[REGISTRY] Local cache not found for '{model_name}'. Fetching from Hugging Face Hub...")
            self.model = SentenceTransformer(model_name)
        self._embeddings = None
        self.name_to_id_map = {}
        self.capabilities_manifest = ""
        self._skills_cache: list[str] = []  # Luu tru ten skill
        
        # Summary and Detail caches for skill metadata
        self._summary_cache: Dict[str, Dict[str, Any]] = {}
        self._detail_cache: Dict[str, Dict[str, Any]] = {}
        self.last_refresh_time: Optional[float] = None

    def _normalize_tool(self, tool) -> dict:
        if isinstance(tool, dict):
            return tool
        if hasattr(tool, "model_dump"):
            return tool.model_dump()
        if hasattr(tool, "dict"):
            return tool.dict()
        return getattr(tool, "__dict__", {})

    def scan_local_skills(self) -> list:
        """Quét và phân tích cú pháp các SOP kỹ năng tại thư mục local skills/"""
        local_tools = []
        skills_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "skills"))
        if not os.path.exists(skills_dir):
            print(f"[REGISTRY] Skills directory does not exist: {skills_dir}")
            return []
            
        print(f"[REGISTRY] Scanning SOP skills at: {skills_dir}")
        for item in os.listdir(skills_dir):
            item_path = os.path.join(skills_dir, item)
            if os.path.isdir(item_path):
                skill_md_path = os.path.join(item_path, "SKILL.md")
                if os.path.exists(skill_md_path):
                    try:
                        with open(skill_md_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        
                        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
                        if match:
                            yaml_block = match.group(1)
                            instructions = match.group(2)
                            metadata = yaml.safe_load(yaml_block) or {}
                            
                            # Lấy thông tin cơ bản
                            name = metadata.get("name", item)
                            skill_id = metadata.get("skill_id") or name
                            desc = metadata.get("description", "")
                            
                            # Cache chi tiết đầy đủ
                            detail_info = {
                                "id": skill_id,
                                "name": name,
                                "description": desc,
                                "metadata": metadata,
                                "input": metadata.get("input", {}),
                                "output": metadata.get("output", {}),
                                "raw_content": content,
                                "instructions": instructions
                            }
                            self._detail_cache[name] = detail_info
                            self._detail_cache[skill_id] = detail_info
                            
                            local_tools.append({
                                "id": skill_id,
                                "name": name,
                                "description": desc,
                                "tags": metadata.get("tags", []),
                                "category": metadata.get("category", ""),
                                "level": metadata.get("level", "atomic"),
                                "input": metadata.get("input", {}),
                                "output": metadata.get("output", {})
                            })
                            print(f"[REGISTRY] Scanned and loaded local SOP skill: {name}")
                    except Exception as e:
                        print(f"[REGISTRY] Error reading SOP skill at {item_path}: {e}")
        return local_tools
        
    def build_index(self, tools_data: list = None):
        """Tao index vector cho skill list tu local skills hoac tools_data"""
        self._skills_cache = []
        self._summary_cache = {}
        summary_texts = []
        lines = ["### SYSTEM AVAILABLE TOOLS AND CAPABILITIES ###"]
        
        # 1. Quét các local skills trước
        local_tools = self.scan_local_skills()
        combined_tools = []
        seen_names = set()
        
        for tool in local_tools:
            combined_tools.append(tool)
            seen_names.add(tool["name"])
            
        # 2. Nạp thêm từ tools_data nếu chưa tồn tại
        if tools_data:
            for tool in tools_data:
                tool_dict = self._normalize_tool(tool)
                name = tool_dict.get("name")
                if name and name not in seen_names:
                    combined_tools.append(tool_dict)
                    seen_names.add(name)
                    
        # 3. Xây dựng index và cache
        for tool_dict in combined_tools:
            name = tool_dict.get("name")
            skill_id = tool_dict.get("id") or tool_dict.get("skill_id")
            desc = tool_dict.get("description") or tool_dict.get("metadata", {}).get("description", "")
            tags = tool_dict.get("tags", [])
            category = tool_dict.get("category", "")
            level = tool_dict.get("level", "atomic")
            updated_at = tool_dict.get("updated_at")
            
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
            
            lines.append(f"- Tool Name: {name} (ID: {skill_id})")
            lines.append(f"  Description: {desc}")
            lines.append(f"  Category: {category} | Tags: {', '.join(tags) if isinstance(tags, list) else str(tags)}")
            
        self.capabilities_manifest = "\n".join(lines)
        if summary_texts:
            self._embeddings = self.model.encode(summary_texts, convert_to_tensor=True)
        print(f"[REGISTRY] Successfully loaded and indexed {len(combined_tools)} skills.")
        
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
        """Tải chi tiết kỹ năng từ cache hoặc API ngoài"""
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
            print(f"[REGISTRY] Lazy load skill detail failed for {skill_id}: {e}")
            
        summary_val = next((v for k, v in self._summary_cache.items() if v["id"] == skill_id or k == skill_name_or_id), None)
        return summary_val or {}
        
    async def refresh_cache(self, tools_data: list = None):
        self.build_index(tools_data)
        self.last_refresh_time = time.time()
        print("[REGISTRY] Cache refresh hook triggered.")

    def get_all_tools(self) -> list[str]:
        return self._skills_cache
    
    def get_id_by_name(self, name: str) -> str:
        return self.name_to_id_map.get(name)

semantic_registry = SkillSemanticRegistry()