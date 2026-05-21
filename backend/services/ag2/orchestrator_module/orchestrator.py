from .state_schema import AgentState
from typing import Dict, Any
from .state_schema import AgentState 
from planner_module.planner import PlannerModule
from planner_module.schemas import ExecutionPlan, TaskStep
from skill_selector_module.selector import ContextBasedSkillSelector
from executor_module.executor import LLMSkillExecutor
import json
from langgraph.graph import StateGraph, END 

# hàm evaluate cho strict router lúc sau này sẽ cần thêm logic để quyết định có nên replan hay retry hay không dựa trên feedback lỗi và số lần retry đã thực hiện
def evaluate_conditional_router(self, state: AgentState) -> str:
        if state.get("latest_error_feedback") is not None:
        
            if state.get("current_retry_count", 0) < 2:
                state["current_retry_count"] += 1
                print(f"⚠️ Phát hiện lỗi thực thi. Tiến hành Retry lượt thứ {state['current_retry_count'] + 1}/2...")
                return "retry_route" # chạy lại executor
            else:
                print("🚨 Đã cạn số lần Retry (2/2) nhưng vẫn lỗi. Chuyển sang cơ chế Replan...")
                return "replan_route"
                
        # Nếu kết quả thành công hoàn toàn (Không có error feedback)
        if state["current_step_index"] < len(state["execution_plan"]):
            state["current_retry_count"] = 0 
            return "next_step_route" 
            
        return "final_response_route"
    
class OrchestratorGraph:
    def __init__(self, planner_module: PlannerModule, skill_selector: ContextBasedSkillSelector, executor_module: Any = None):
        self.planner = planner_module
        self.selector = skill_selector
        self.executor = executor_module
        self.workflow = StateGraph(AgentState)
        self._build_graph()

    def plan_node(self, state: AgentState) -> Dict[str, Any]:
        print("\n[Node 1: Planning] 🧠 Đang lập kế hoạch tổng thể...")      
        raw_skills = self.selector._fetch_skills_with_cache()
        minimal_skills = []
        for skill in raw_skills:
            minimal_skills.append({
                "name": skill.get("name"),
                "description": skill.get("description")
            })
            
        print(f"   📊 [Planner Log]: Đã nạp bối cảnh tinh gọn của {len(minimal_skills)} kỹ năng từ Registry Service.")
        
        plan_obj = self.planner.generate_plan(
            user_goal=state["user_goal"], 
            chat_history=state["chat_history"],
            available_skills=minimal_skills,
            error_feedback=state.get("latest_error_feedback") 
        )
        
        plan_dicts = [step.model_dump() for step in plan_obj.steps]
        for step in plan_obj.steps:
            print(f"     🔹 Bước {step.step_id}: {step.task_description}")
            
        return {
            "execution_plan": plan_dicts, 
            "current_step_index": 0,  
            "latest_error_feedback": None 
        }

    def select_skill_node(self, state: AgentState) -> Dict[str, Any]:
        idx = state["current_step_index"]
        current_step_dict = state["execution_plan"][idx]
        task_desc = current_step_dict['task_description']
        print(f"\n[Node 2: Selecting Skill] 🎯 Đang định tuyến kỹ năng cho Bước {idx+1}: {task_desc}")

        result = self.selector.select_best_skill(
            current_task_description=task_desc,
            accumulated_context=state["accumulated_context"]
        )
        
        # GIẢI MÃ CHUỖI STRING JSON THÀNH DICT THỰC TẾ
        try:
            parsed_args = json.loads(result.extracted_arguments)
        except Exception:
            parsed_args = {} 
            
        print(f"   💡 AI Quyết định chọn: {result.skill_name}")
        print(f"   💡 Lý do chọn: {result.reasoning}")
        print(f"   📦 Tham số trích xuất: {parsed_args}")
        
        # Lưu kết quả cấu trúc vào State Graph để chuyển tiếp sang execute_node
        return {
            "current_selected_skill_id": result.selected_skill_id,
            "current_selected_skill_name": result.skill_name, 
            "extracted_arguments": parsed_args
        }
        
    def execute_skill_node(self, state: AgentState) -> Dict[str, Any]:
        idx = state["current_step_index"]
        current_step_dict = state["execution_plan"][idx]
        
        skill_id = state.get("current_selected_skill_id")
        skill_name = state.get("current_selected_skill_name", "Unknown-Skill")
        extracted_args = state.get("extracted_arguments", {})

        print(f"\n[Node 3: Execution] ⚡ Khởi chạy Executor Module cho kỹ năng: {skill_name}")
        print(f"   📦 Arguments: {extracted_args}")

        real_output = self.executor.execute(
            skill_name=skill_name,
            extracted_arguments=extracted_args,
            task_description=current_step_dict["task_description"],
            accumulated_context=state["accumulated_context"]
        )
        print(f"   📥 [Executor Log]: Thực thi thành công! Kết quả đã ghi nhận vào Context.")

        # Cập nhật kết quả vào bộ nhớ tích lũy
        new_context = dict(state["accumulated_context"])
        new_context[f"step_{idx+1}_{skill_name}_output"] = real_output

        return {
            "latest_step_output": {"result": real_output},
            "accumulated_context": new_context
        }

    def evaluate_node(self, state: AgentState) -> Dict[str, Any]:
        print("[Node 3.5: Evaluating] 🔍 Đang kiểm tra chất lượng kết quả...")
        
        # Logic giả định: Mặc định là thành công (Pass)
        # Nếu muốn test luồng Replan, bạn có thể chuyển thành: "latest_error_feedback": "Lỗi định dạng JSON đầu ra"
        return {
            "latest_error_feedback": None, 
            "current_step_index": state["current_step_index"] + 1 
        }

    def respond_node(self, state: AgentState) -> Dict[str, Any]:
        print("\n[Node 4: Respond] 📝 Tổng hợp kết quả và trả lời người dùng...")
        final_text = f"Hệ thống đã xử lý xong yêu cầu của bạn thông qua các bước dữ liệu: {state['accumulated_context']}"
        return {"final_response": final_text}

    def evaluate_conditional_router(self, state: AgentState) -> str:
        if state.get("latest_error_feedback") is not None:
            return "replan_route"
        if state["current_step_index"] < len(state["execution_plan"]):
            return "next_step_route"
        return "final_response_route"

    def _build_graph(self):
        """Hàm dựng khung xương đồ thị LangGraph chuẩn chỉnh"""
        self.workflow.add_node("plan_node", self.plan_node)
        self.workflow.add_node("select_skill_node", self.select_skill_node)
        self.workflow.add_node("execute_skill_node", self.execute_skill_node)
        self.workflow.add_node("evaluate_node", self.evaluate_node)
        self.workflow.add_node("respond_node", self.respond_node)

        self.workflow.set_entry_point("plan_node")


        self.workflow.add_edge("plan_node", "select_skill_node")
        self.workflow.add_edge("select_skill_node", "execute_skill_node")
        self.workflow.add_edge("execute_skill_node", "evaluate_node")

        self.workflow.add_conditional_edges(
            "evaluate_node", 
            self.evaluate_conditional_router, 
            {
                "replan_route": "plan_node",
                "retry_route": "execute_skill_node",
                "next_step_route": "select_skill_node",
                "final_response_route": "respond_node"
            }
        )
        self.workflow.add_edge("respond_node", END)

    def compile(self):
        """Biên dịch đồ thị để sẵn sàng chạy"""
        return self.workflow.compile()