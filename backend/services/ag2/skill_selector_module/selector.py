import httpx
import torch
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
from openai import OpenAI
from .schemas import SkillSelectionResult

MODEL_NAME = "gpt-4o-mini"

class ContextBasedSkillSelector:
    # Chỉ load lên RAM 1 lần duy nhất
    _embedder: Optional[SentenceTransformer] = None

    def __init__(self, client: OpenAI, skill_registry_url: str, model_name: str = MODEL_NAME):
        self.client = client
        self.skill_registry_url = skill_registry_url
        self.model_name = model_name
        
        # Singleton pattern cho Embedder
        if ContextBasedSkillSelector._embedder is None:
            print("💾 [System] Đang tải Model Embedding 'all-MiniLM-L6-v2' lên RAM...")
            ContextBasedSkillSelector._embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        
        self.embedder = ContextBasedSkillSelector._embedder
        
        # Bộ nhớ Cache lưu danh sách kỹ năng
        self._skills_cache: Optional[List[Dict[str, Any]]] = None

    def _fetch_skills_with_cache(self) -> List[Dict[str, Any]]:
        """Cơ chế Caching: Chỉ gọi API sang AG1 1 lần duy nhất"""
        if self._skills_cache is not None:
            return self._skills_cache
        try:
            with httpx.Client() as http_client:
                response = http_client.get(f"{self.skill_registry_url}/skills/tools", timeout=5.0)
                if response.status_code == 200:
                    self._skills_cache = response.json()
                    return self._skills_cache
                return []
        except Exception as e:
            print(f"⚠️ Lỗi kết nối Registry: {e}")
            return []

    def select_best_skill(self, current_task_description: str, accumulated_context: Dict[str, Any], similarity_threshold: float = 0.3) -> Optional[SkillSelectionResult]:
        available_skills = self._fetch_skills_with_cache()
        if not available_skills:
            return None

        # TẦNG 1: SEMANTIC FILTERING & THRESHOLD CHECK
        corpus = [f"{skill['name']}: {skill['description']}" for skill in available_skills]
        corpus_embeddings = self.embedder.encode(corpus, convert_to_tensor=True)
        query_embedding = self.embedder.encode(current_task_description, convert_to_tensor=True)
        
        similarity_scores = self.embedder.similarity(query_embedding, corpus_embeddings)[0]
        
        max_score = torch.max(similarity_scores).item()
        print(f"DEBUG max score = {max_score}")
        if max_score < similarity_threshold:
            print(f"⚠️ [Selector] Điểm tương đồng thấp nhất đạt {max_score:.4f} < {similarity_threshold}. Không tìm thấy skill phù hợp!")
            return None # Trả về None để Orchestrator biết đường kích hoạt Replan/Error handler

        top_k = min(2, len(available_skills))
        scores, indices = torch.topk(similarity_scores, k=top_k)
        filtered_skills = [available_skills[idx] for idx in indices]

        # TẦNG 2: LLM TARGETED SELECTION
        # Cắt giảm bớt context nếu accumulated_context quá lớn để tránh làm nhiễu việc trích xuất tham số
        truncated_context = {k: v for k, v in accumulated_context.items() if k in ["stacktrace", "source_path", "file", "line", "variable", "error_type"]}

        system_prompt = f"""Bạn là Bộ định tuyến Kỹ năng chuyên dụng.
Hãy phân tích bước việc và chọn ra duy nhất MỘT công cụ phù hợp từ danh sách rút gọn sau:
{filtered_skills}
QUY TẮC: Trích xuất tham số chính xác từ bối cảnh và map vào cấu trúc 'input_schema'."""
        user_prompt = f"""Công việc: "{current_task_description}"\nBối cảnh: {truncated_context}"""
        
        completion = self.client.beta.chat.completions.parse(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format=SkillSelectionResult,
        )
        return completion.choices[0].message.parsed