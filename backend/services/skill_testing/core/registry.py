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
        self._skills_cache: list[str] = []  #Luu tru ten skill
        
    def build_index(self, skills: list[str]):
        """Tao index vector cho skill list"""
        if not skills:
            return
        self._skills_cache = skills
        summary_texts = [s.replace("_", " ").lower() for s in skills]
        self._embeddings = self.model.encode(summary_texts, convert_to_tensor=True)
        print(f"Built semantic index for {len(skills)} skills")
        
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
    
    def all_skills(self) -> list[str]:
        return self._skills_cache
    
    def get_skill_by_name(self, name: str) -> Optional[str]:
        if name in self._skills_cache:
            return name
        return None
    
semantic_registry = SkillSemanticRegistry()