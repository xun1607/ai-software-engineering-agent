from typing import Dict, Any
from openai import OpenAI
MODEL_NAME = "gpt-4o"
class LLMSkillExecutor:
    def __init__(self, client: OpenAI, model_name: str = MODEL_NAME):
        self.client = client
        self.model_name = model_name

    def execute(self, skill_name: str, extracted_arguments: Dict[str, Any], task_description: str, accumulated_context: Dict[str, Any]) -> str:
        """
        Đóng vai trò Runtime Engine: Đóng gói Prompt và ép LLM xử lý logic 
        dựa trên các tham số cấu trúc thu được.
        """
        system_prompt = f"""Bạn là Công cụ Thực thi Kỹ năng (Skill Executor Runtime).
Nhiệm vụ của bạn là đóng vai và vận hành kỹ năng [{skill_name}] để giải quyết công việc được giao.
THAM SỐ ĐẦU VÀO ĐÃ ĐƯỢC ĐỊNH TUYẾN CHÍNH XÁC (ARGUMENTS):
{extracted_arguments}
BỐI CẢNH DỮ LIỆU TÍCH LŨY TRƯỚC ĐÓ:
{accumulated_context}
YÊU CẦU BẮT BUỘC:
- Hãy xử lý bài toán một cách chuyên sâu bám sát vào các tham số đầu vào.
- Trả về kết quả thực thi (Output) rõ ràng, minh bạch (Ví dụ: Nếu sinh code sửa lỗi, hãy đưa ra giải thích ngắn và đoạn code snippet hoàn chỉnh)."""

        user_prompt = f"Yêu cầu thực hiện bước việc: \"{task_description}\""

        # Gọi LLM sinh kết quả thật
        completion = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2
        )
        
        return completion.choices[0].message.content