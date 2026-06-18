import asyncio
import json
from datetime import datetime
from services.skill_testing.state import AgentState
from services.skill_testing.core.registry import semantic_registry
from services.skill_testing.core.execute_node import execute_node
from services.skill_testing.core.evaluate_node import evaluate_node
from services.skill_testing.unit_tests.mock_client import MockModelClient, MockSkillClient
from shared.schemas import SkillRead

async def test_execution_and_evaluation():
    # --- BƯỚC 1: SETUP REGISTRY VÀ SKILL GIẢ ---
    mock_skill = SkillRead(
        id="uuid-123",
        name="analyze-stacktrace",
        version="1.0",
        level="atomic",
        category="debug",
        tags=["java"],
        metadata={"description": "Analyzes logs", "input": {"stacktrace": {"type": "string"}}},
        updated_at=datetime.now(),
        raw_content="...",
        full_markdown="..."
    )
    semantic_registry.build_index([mock_skill])

    # --- BƯỚC 2: SETUP STATE ---
    state = AgentState(
        user_context={"code": "...", "stacktrace": "NullPointer", "message": "Fix"},
        plan=["Analyze logs"],
        current_step_idx=0,
        selected_skill="analyze-stacktrace",
        goal="Fix NullPointer"
    )

    # --- BƯỚC 3: TEST EXECUTE_NODE (HAPPY PATH) ---
    print("\n--- Testing Execute Node ---")
    mock_llm = MockModelClient({
        "extract_args": json.dumps({"stacktrace": "NullPointer at line 10"})
    })
    mock_skill_api = MockSkillClient({"status": "success", "output": "Error found at line 10"})
    
    state = await execute_node(state, mock_llm, mock_skill_api)
    print(f"Observation: {state.last_observation}")
    assert "Error found at line 10" in state.last_observation

    # --- BƯỚC 4: TEST EVALUATE_NODE (SUCCESS) ---
    print("\n--- Testing Evaluate Node (Success) ---")
    mock_llm_eval = MockModelClient({
        "evaluate": json.dumps({"is_success": True, "analysis": "Line 10 identified."})
    })
    
    state = await evaluate_node(state, mock_llm_eval)
    print(f"Is Finished: {state.is_finished}")
    print(f"Final Answer: {state.final_answer}")
    assert state.is_finished is True
    assert state.current_step_idx == 1

    # --- BƯỚC 5: TEST RETRY LOGIC (FAILURE PATH) ---
    print("\n--- Testing Retry Logic (Failure Case) ---")
    state.is_finished = False
    state.current_step_idx = 0
    state.retry_count = 0
    
    mock_llm_fail = MockModelClient({
        "evaluate": json.dumps({"is_success": False, "analysis": "Results inconclusive."})
    })
    
    # Lần fail 1 -> Phải tăng retry_count
    state.last_observation = json.dumps({"status": "FAILED", "stderr": "NullPointerException"})
    state = await evaluate_node(state, mock_llm_fail)
    print(f"Retry Count: {state.retry_count}")
    assert state.retry_count == 1
    assert state.plan != [] # Chưa xóa plan, chỉ retry

    # Lần fail 2 -> Phải tăng replan_count và xóa plan
    print("\n--- Testing Re-plan Logic (After Max Retries) ---")
    state.last_observation = json.dumps({"status": "FAILED", "stderr": "ArithmeticException"})
    state = await evaluate_node(state, mock_llm_fail)
    print(f"Re-plan Count: {state.replan_count}")
    print(f"Plan cleared: {state.plan == []}")
    assert state.replan_count == 1
    assert state.plan == []

    # --- BƯỚC 6: TEST LOOP DETECTION (3 LẦN LIÊN TIẾP) ---
    print("\n--- Testing Loop Detection (Safe Terminate) ---")
    state.is_finished = False
    state.fingerprint_history = []
    
    # Gửi cùng một lỗi 3 lần liên tiếp
    state.last_observation = json.dumps({"status": "FAILED", "stderr": "NullPointerException"})
    
    # Lần 1
    state.plan = ["Analyze logs"]
    state.current_step_idx = 0
    state = await evaluate_node(state, mock_llm_fail)
    assert state.is_finished is False
    
    # Lần 2
    state.plan = ["Analyze logs"]
    state.current_step_idx = 0
    state = await evaluate_node(state, mock_llm_fail)
    assert state.is_finished is False
    
    # Lần 3
    state.plan = ["Analyze logs"]
    state.current_step_idx = 0
    state = await evaluate_node(state, mock_llm_fail)
    print(f"Loop Detection finished: {state.is_finished}")
    print(f"Final Answer: {state.final_answer}")
    assert state.is_finished is True
    assert state.need_replan is True
    assert "Infinite loop detected" in state.final_answer

    print("\n✅ All Execution and Evaluation Tests Passed!")

if __name__ == "__main__":
    asyncio.run(test_execution_and_evaluation())