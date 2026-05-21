from typing import Dict, List, Any
from pydantic import BaseModel, Field
from openai import OpenAI 
from .schemas import TaskStep, StepOutput, SkillOutputFormat, ExecutionPlan

MODAL_NAME = "gpt-4o"

############
# Sau sẽ thay chat_history bằng một hàm xử lý tóm tắt hoặc cắt tỉa lịch sử trước khi nạp vào Planner
# sau sẽ gọi API lấy danh sách skill (chỉ phần name trong metadata) từ Skill Registry Service để nạp vào Planner giúp nó lập kế hoạch dựa trên những skill có sẵn
##########
class PlannerModule:
    def __init__(self, client: OpenAI, model_name: str = MODAL_NAME):
        self.client = client
        self.model_name = model_name

    def generate_plan(self, 
                    user_goal: str, 
                    chat_history: str,
                    available_skills: List[Dict[str, Any]], # Nhận danh sách skill gọi từ API của bạn kia
        error_feedback: str | None = None) -> ExecutionPlan:
        """
        Nhận vào mục tiêu và lịch sử, dùng Chain-of-Thought để sinh ra Kế hoạch dạng JSON cấu trúc.
        """
        system_prompt = """Bạn là bộ não Lập kế hoạch (Planner). Nhiệm vụ của bạn là rã yêu cầu của user thành các bước thực thi logic.
DỰA VÀO DANH SÁCH CÁC KỸ NĂNG CÓ SẴN SAU ĐÂY ĐỂ LÊN KẾ HOẠCH PHÙ HỢP:
{available_skills}
Hãy sử dụng tư duy Chain-of-Thought (CoT) để:
1. Phân tích sâu sắc mục tiêu cốt lõi của người dùng.
2. Suy luận từng bước (Thought) xem cần phải làm gì trước, làm gì sau.
3. Rã mục tiêu thành một chuỗi các bước hành động cụ thể, rạch ròi.
Lưu ý: cần vạch ra 'Mô tả công việc cần làm ở từng bước' """

        user_prompt = f"""Lịch sử hội thoại: {chat_history}
Yêu cầu người dùng cần giải quyết: {user_goal}
Hãy lập kế hoạch thực hiện!"""

        if error_feedback:
            system_prompt += f"\n\n⚠️ LƯU Ý LỖI CỦA LƯỢT CHẠY TRƯỚC (Hãy đọc để tự sửa sai - Reflexion):\n{error_feedback}"
        user_prompt = f"Lịch sử: {chat_history}\nYêu cầu mới từ người dùng: {user_goal}\nHãy xuất bản kế hoạch dạng JSON."

        # structured output API để parse thẳng về ExecutionPlan (TaskStep[])
        completion = self.client.beta.chat.completions.parse(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format=ExecutionPlan,
        )
        
        return completion.choices[0].message.parsed

######################################################
# Phát triển replan sau khi có feedback lỗi từ Evaluator 
    def replan_on_failure(self, current_plan: ExecutionPlan, failed_step_id: int, error_feedback: str) -> ExecutionPlan:
        """
        [Tính năng nâng cao từ ReAct/Reflexion]
        Tái lập kế hoạch khi một bước bị Evaluator báo lỗi.
        """
        # Code logic nạp lại plan cũ + vết lỗi từ Evaluator vào LLM để sinh Plan mới cải tiến.
        pass