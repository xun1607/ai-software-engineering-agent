from typing import Dict, Any
from pydantic import BaseModel, Field

class SkillSelectionResult(BaseModel):
    selected_skill_id: str = Field(description="ID (UUID) của skill được chọn cuối cùng từ danh sách rút gọn")
    skill_name: str = Field(description="Tên của skill được chọn")
    reasoning: str = Field(description="Lập luận ngắn gọn tại sao chọn công cụ này")
    # ĐỔI THÀNH STR: Ép OpenAI trả về chuỗi JSON hộ, tránh quy tắc nghiêm ngặt của Dict
    extracted_arguments: str = Field(
        default="{}", 
        description="Chuỗi JSON (stringified JSON object) chứa các tham số trích xuất từ accumulated_context để nạp vào skill, ví dụ: '{\"file\": \"main.py\", \"line\": 10}'"
    )