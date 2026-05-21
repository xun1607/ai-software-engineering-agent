from pydantic import BaseModel, Field
from typing import Any, List
from pydantic import BaseModel, Field
from enum import Enum

class SkillOutputFormat(str, Enum):
    RAW = "raw"       # Văn bản thô từ LLM hoặc kết quả thô của API
    JSON = "json"     # JSON Object để Selector hoặc Planner đọc cấu trúc
    
class TaskStep(BaseModel):
    step_id: int = Field(description="Thứ tự thực hiện của bước")
    thought: str = Field(description="Lập luận logic (Chain-of-Thought) tại sao cần bước này")
    task_description: str = Field(description="Mô tả chi tiết công việc cụ thể cần xử lý ở bước này")
    status: str = Field(default="PENDING", description="Trạng thái thực thi (PENDING, RUNNING, COMPLETED, FAILED)")

# Cấu trúc danh sách kế hoạch tổng thể để LLM trả về đúng format
class ExecutionPlan(BaseModel):
    steps: List[TaskStep] = Field(description="Danh sách các bước tuần tự được lập ra để hoàn thành mục tiêu")


class StepOutput(BaseModel):
    step_id: int
    raw_output: Any = Field(description="Kết quả thô thu được từ việc thực thi Skill")
    output_format: SkillOutputFormat = Field(default=SkillOutputFormat.RAW)
    is_valid: bool = Field(default=True, description="Kết quả từ Evaluator đánh giá xem bước này đạt chuẩn chưa")
    feedback: str | None = Field(default=None, description="Phản hồi từ Evaluator nếu bước này bị lỗi để Planner tái lập kế hoạch")