import asyncio
import json
from typing import List, Dict, Any

from langgraph.graph import StateGraph, END

# Import các thành phần trong Project của bạn
from services.skill_testing.state import AgentState
from services.skill_testing.core.registry import semantic_registry
from services.skill_testing.core.skill_client import SkillExecutionClient

# Import các Node đã refactor
from services.skill_testing.core.plan_node import plan_node
from services.skill_testing.core.select_skill_node import select_skill_node
from services.skill_testing.core.execute_node import execute_node
from services.skill_testing.core.evaluate_node import evaluate_node

# 1. Khai báo dữ liệu Mock của bạn AG1 cung cấp khi hệ thống khởi động
MOCK_SKILLS_DATA = {
    "items": [
        {
            "id": "5b1b2974-03c6-4b40-9d03-dae25a370b3d",
            "name": "run-python-test",
            "category": "python/testing",
            "tags": ["python", "testing", "validation", "pytest"],
            "metadata": {
                "description": "Dùng để thực thi các đoạn code Python và kiểm tra xem chúng có vượt qua các bài unit test hay không.",
                "input": {
                    "type": "object",
                    "required": ["code_snippet", "test_case"],
                    "properties": {
                        "test_case": {"type": "string"},
                        "code_snippet": {"type": "string"}
                    }
                }
            }
        },
        {
            "id": "1434afbe-602a-468e-aa6d-a844a6ab5629",
            "name": "debug-java-null-pointer",
            "category": "java/debugging",
            "tags": ["java", "debug", "null-pointer", "pipeline"],
            "metadata": {
                "description": "Full pipeline to debug a Java NullPointerException. Analyzes the stacktrace and provides actionable fix suggestions.",
                "input": {
                    "type": "object",
                    "required": ["stacktrace", "source_path"],
                    "properties": {
                        "stacktrace": {"type": "string"},
                        "source_path": {"type": "string"}
                    }
                }
            }
        },
        {
            "id": "abaa3845-b359-4b4b-90bd-ea7cf4488b95",
            "name": "suggest-java-fix",
            "category": "java/debugging",
            "tags": ["java", "fix", "null-pointer"],
            "metadata": {
                "description": "Suggests a concrete Java fix pattern for a NullPointerException given the file location and the null variable.",
                "input": {
                    "type": "object",
                    "required": ["file", "line", "variable"],
                    "properties": {
                        "file": {"type": "string"},
                        "line": {"type": "integer"},
                        "variable": {"type": "string"}
                    }
                }
            }
        },
        {
            "id": "60a0da02-1c33-4d97-a574-9b736e6ed860",
            "name": "analyze-stacktrace",
            "category": "universal/debugging",
            "tags": ["stacktrace", "debug", "troubleshooting"],
            "metadata": {
                "description": "Analyzes an exception stacktrace to pinpoint the exact source file, line number, and the variable or root cause.",
                "input": {
                    "type": "object",
                    "required": ["stacktrace", "source_path"],
                    "properties": {
                        "stacktrace": {"type": "string"},
                        "source_path": {"type": "string"}
                    }
                }
            }
        },
        {
            "id": "c4b90445-960e-4ff9-a2cf-a09f8632e3bd",
            "name": "read-code-context",
            "category": "universal/debugging",
            "tags": ["system", "file-io", "context"],
            "metadata": {
                "description": "Reads source code around a specific line to provide context for debugging.",
                "input": {
                    "type": "object",
                    "required": ["file", "line"],
                    "properties": {
                        "file": {"type": "string"},
                        "line": {"type": "integer"}
                    }
                }
            }
        }
    ]
}

# 2. Mock Model Client để test không tốn token của người dùng lúc chạy thử nghiệm (Happy Path)
class MockModelClient:
    def call(self, system_prompt: str, user_prompt: str) -> str:
        # Giả lập LLM Planner trả về kế hoạch sử dụng các kỹ năng thực tế của hệ thống
        if "expert Software Engineer AI" in system_prompt:
            return '{"plan": ["analyze-stacktrace", "read-code-context", "suggest-java-fix"]}'
            
        # Giả lập LLM Executor trích xuất tham số đầu vào JSON phù hợp cho từng Skill
        elif "Parameter Extractor" in system_prompt:
            if "analyze-stacktrace" in system_prompt:
                return '{"stacktrace": "NullPointerException at LoginService:42", "source_path": "src/LoginService.java"}'
            elif "read-code-context" in system_prompt:
                return '{"file": "src/LoginService.java", "line": 42}'
            else:
                return '{"file": "src/LoginService.java", "line": 42, "variable": "user"}'
                
        # Giả lập LLM QA Evaluator chấm điểm thành công cho mỗi lượt chạy
        elif "Quality Assurance Engineer" in system_prompt:
            return '{"is_success": true, "analysis": "Step execution matches expected criteria. Goal met."}'
            
        return '{"is_success": true}'

# 3. Định nghĩa bộ Router Edge điều phối rẽ nhánh & Tối ưu chi phí (AG2 CORE LOGIC)
def route_decision(state: AgentState):
    # Nếu cờ báo kết thúc được bật từ Node Evaluator
    if state.is_finished:
        print(f"\n🏁 [SYSTEM END] -> Vòng lặp khép kín kết thúc!")
        print(f"📄 Kết quả cuối cùng: {state.final_answer}")
        print(f"📊 Chỉ số thực thi: Total Steps attempted: {state.step_count}")
        return END
        
    # Cơ chế Circuit Breaker tự động ngắt nếu số bước hành động vượt quá giới hạn an toàn
    if state.step_count >= state.max_total_steps:
        print(f"\n🚨 [CIRCUIT BREAKER] Cảnh báo lặp vô hạn! Ngắt luồng tại bước thứ {state.step_count} để bảo vệ ví của User.")
        return END

    # Nếu phát hiện lỗi và retry_count được kích hoạt -> Quay lại Executor chạy lại
    if state.retry_count > 0:
        print(f"🔄 [AG2 ROUTER] Phát hiện lỗi. Kích hoạt Retry vòng {state.retry_count}. Chuyển hướng quay lại Node Executor.")
        return "executor_node"

    # Happy Path: Chuyển sang Task tiếp theo trong Kế hoạch
    print(f"➡️ [AG2 ROUTER] Tác vụ hiện tại hoàn tất. Di chuyển tới bước tiếp theo trong kế hoạch.")
    return "select_skill_node"

# 4. Hàm điều hướng xây dựng Graph LangGraph
async def run_pipeline():
    print("=================================================================")
    print("⚡ BẮT ĐẦU CHẠY THỬ NGHIỆM HỆ THỐNG ĐIỀU PHỐI KHÉP KÍN (AG2) ⚡")
    print("=================================================================\n")

    # Bước A: Khởi tạo Registry và nạp dữ liệu Mock danh sách Skill của bạn AG1
    # Biến đổi định dạng dict sang Object mô phỏng của semantic_registry
    skills_list = []
    # class SimpleSkillObj:
    #     def __init__(self, data):
    #         self.id = data["id"]
    #         self.name = data["name"]
    #         self.category = data["category"]
    #         self.tags = data["tags"]
    #         self.metadata = data["metadata"]

    # for item in MOCK_SKILLS_DATA["items"]:
    #     skills_list.append(SimpleSkillObj(item))
    skills_list = [item["name"] for item in MOCK_SKILLS_DATA["items"]]
    # Xây dựng Index vector cục bộ cho Registry
    semantic_registry.build_index(skills_list)

    # Bước B: Khởi tạo State đầu vào mô phỏng một sự cố Java NullPointerException
    initial_state = AgentState(
        user_context={
            "code": "public class LoginService { ... user.login(); ... }",
            "stacktrace": "java.lang.NullPointerException: Cannot invoke 'User.login()' because 'user' is null at LoginService.java:42",
            "message": "Hãy gỡ lỗi và đề xuất bản vá giúp tôi."
        }
    )

    # Khởi tạo các mock clients
    mock_model_client = MockModelClient()
    mock_skill_client = SkillExecutionClient()

    # Bước C: Đóng gói các node của LangGraph bọc tham số client
    async def p_node(state):
        return plan_node(state, mock_model_client)

    def s_node(state):
        return select_skill_node(state)

    async def ex_node(state):
        return await execute_node(state, mock_model_client, mock_skill_client)

    def ev_node(state):
        return evaluate_node(state, mock_model_client)

    # Bước D: Ghép nối sơ đồ đồ thị LangGraph
    workflow = StateGraph(AgentState)
    
    workflow.add_node("plan_node", p_node)
    workflow.add_node("select_skill_node", s_node)
    workflow.add_node("executor_node", ex_node)
    workflow.add_node("evaluate_node", ev_node)

    # Thiết lập luồng kết nối tuần tự
    workflow.set_entry_point("plan_node")
    workflow.add_edge("plan_node", "select_skill_node")
    workflow.add_edge("select_skill_node", "executor_node")
    workflow.add_edge("executor_node", "evaluate_node")
    
    # Thiết lập Cạnh điều kiện từ Node Evaluator (Đóng vai trò Router AG2)
    workflow.add_conditional_edges("evaluate_node", route_decision)

    # Compile đồ thị
    app = workflow.compile()

    # Bước E: Khởi chạy luồng khép kín (Invoke)
    final_output = await app.ainvoke(initial_state)
    print("\n=========================================================")
    print("🎉 CHÚC MỪNG! HỆ THỐNG MVP HAPPY PATH ĐÃ CHẠY HOÀN TẤT THÀNH CÔNG")
    print("=========================================================")

if __name__ == "__main__":
    asyncio.run(run_pipeline())
