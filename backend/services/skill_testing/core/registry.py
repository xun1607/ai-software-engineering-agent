from click import Tuple

from sentence_transformers import SentenceTransformer, util

from typing import Dict, List, Optional

MODEL_NAME = "all-MiniLM-L6-v2"
# class SkillSemanticRegistry:
#     def __init__(self, model_name: str = MODEL_NAME):
#         self.model = SentenceTransformer(model_name)
#         self.index = None
#         self.skills_cache: List[SkillRead] = []
        
#     def build_index(self, skills: List[SkillRead]):
#         """Tao index vector cho skill list"""
#         if not skills:
#             return
#         self._skills_cache = skills
#         summary_texts = []
#         for s in skills:
#             desc = s.metadata.get('description', '') if isinstance(s.metadata, dict) else ""
#             text = f"{s.name} {s.category} {desc} {' '.join(s.tags)}"
#             summary_texts.append(text.lower())
#         self._embeddings = self.model.encode(summary_texts, convert_to_tensor=True)
        
#         print(f"Built semantic index for {len(skills)} skills")
#     def search(self, query: str, top_k: int = 5) -> List[tuple[SkillRead, float]]:
#         if self._embeddings is None or not self._skills_cache:
#             return []
#         query_embedding = self.model.encode(query.lower(), convert_to_tensor=True)
#         hits = util.semantic_search(query_embedding, self._embeddings, top_k=top_k)[0]
#         results = []
#         for hit in hits:
#             idx = hit['corpus_id']
#             score = hit['score']
#             results.append((self._skills_cache[idx], score))
#         return results
#     def all_skills(self) -> List[SkillRead]:
#         """Trả về danh sách kỹ năng đã lưu trong RAM"""
#         return self._skills_cache
    
#     def get_skill_by_name(self, name: str) -> Optional[SkillRead]:
#         """Tìm full thông tin skill dựa trên tên mà LLM đã chọn"""
#         for skill in self._skills_cache:
#             if skill.name == name:
#                 return skill
#         return None

class SkillSemanticRegistry:
    def __init__(self, model_name: str = MODEL_NAME):
        self.model = SentenceTransformer(model_name)
        self._embeddings = None
        self.name_to_id_map = {}
        self.capabilities_manifest = ""
        self._skills_cache: list[str] = []  #Luu tru ten skill
        
    def build_index(self, tools_data: list):
        """Tao index vector cho skill list"""
        if not tools_data:
            return
        self._skills_cache = []
        summary_texts = []
        lines = ["### SYSTEM AVAILABLE TOOLS AND CAPABILITIES ###"]
        for tool in tools_data:
            name = tool.get("name")
            skill_id = tool.get("skill_id") or tool.get("id")
            desc = tool.get("description", "")
            
            self.name_to_id_map[name] = skill_id
            self._skills_cache.append(name)
            
            text_context = f"{name} {desc}"
            summary_texts.append(text_context.lower())
            # Tạo chuỗi text ngắn cho Planner           
            lines.append(f"- Tool Name: {name} (ID: {skill_id})")
            lines.append(f"  Description: {desc[:100]}...")
        self.capabilities_manifest = "\n".join(lines)
        self._embeddings = self.model.encode(summary_texts, convert_to_tensor=True)
        print(f"✅ [REGISTRY] Đã nạp thành công và xây dựng ma trận Vector cho {len(tools_data)} kỹ năng.")
        
    def search(self, query: str, top_k: int = 1) -> list[tuple[str, float]]:
        if self._embeddings is None or not self._skills_cache:
            return[]
        query_embedding = self.model.encode(query.lower(), convert_to_tensor=True)
        hits = util.semantic_search(query_embedding, self._embeddings, top_k=top_k)[0]
        results = []
        for hit in hits:
            idx = hit['corpus_id']
            score = hit['score']
            results.append((self._skills_cache[idx], score))
        return results
    
    def get_all_tools(self) -> list[str]:
        return self._skills_cache
    
    def get_id_by_name(self, name: str) -> str:
        return self.name_to_id_map.get(name)
    
semantic_registry = SkillSemanticRegistry()