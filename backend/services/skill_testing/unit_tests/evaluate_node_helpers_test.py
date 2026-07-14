import asyncio
import json
from services.skill_testing.state import AgentState
from services.skill_testing.core.evaluate_node import (
    extract_normalized_error,
    detect_loop,
    route_next_state
)

def test_extract_normalized_error():
    print("🧪 Testing extract_normalized_error...")
    
    # NullPointerException
    obs1 = json.dumps({"stderr": "java.lang.NullPointerException at LoginService.java:42"})
    assert extract_normalized_error(obs1) == "NullPointerException"
    
    # ModuleNotFoundError
    obs2 = json.dumps({"stderr": "ModuleNotFoundError: No module named 'django'"})
    assert extract_normalized_error(obs2) == "ModuleNotFoundError: django"
    
    # Cannot find symbol
    obs3 = json.dumps({"stderr": "LoginService.java:10: error: cannot find symbol\n symbol:   class User"})
    assert extract_normalized_error(obs3) == "cannot find symbol: User"
    
    # Clean output
    obs4 = json.dumps({"status": "SUCCESS", "stdout": "Build successful."})
    assert extract_normalized_error(obs4) == "SUCCESS_OR_NO_ERROR"
    
    print("✅ extract_normalized_error tests passed!")


def test_detect_loop():
    print("\n🧪 Testing detect_loop...")
    
    state = AgentState(
        user_context={},
        plan=["Compile"],
        current_step_idx=0,
        selected_skill="compile-tool"
    )
    
    # 1. 2 entries: should not detect loop
    detect_loop(state, "Compile", "NullPointerException")
    detect_loop(state, "Compile", "NullPointerException")
    assert state.is_finished is False
    assert state.need_replan is False
    
    # 2. 3rd identical entry: should detect loop and abort
    is_loop = detect_loop(state, "Compile", "NullPointerException")
    assert is_loop is True
    assert state.is_finished is True
    assert state.need_replan is True
    assert "Infinite loop detected" in state.final_answer
    
    print("✅ detect_loop tests passed!")


def test_route_next_state():
    print("\n🧪 Testing route_next_state...")
    
    # Case 1: Success on last step
    state1 = AgentState(
        user_context={},
        plan=["Step 1", "Step 2"],
        current_step_idx=1,
        selected_skill="tool"
    )
    state1 = route_next_state(state1, is_success=True, analysis="Looks good")
    assert state1.is_finished is True
    assert "SUCCESS" in state1.final_answer
    
    # Case 2: Success on non-last step (should move index)
    state2 = AgentState(
        user_context={},
        plan=["Step 1", "Step 2"],
        current_step_idx=0,
        selected_skill="tool"
    )
    state2 = route_next_state(state2, is_success=True, analysis="First step done")
    assert state2.is_finished is False
    assert state2.current_step_idx == 1
    
    # Case 3: Fail -> triggers retry
    state3 = AgentState(
        user_context={},
        plan=["Step 1"],
        current_step_idx=0,
        selected_skill="tool"
    )
    assert state3.retry_count == 0
    state3 = route_next_state(state3, is_success=False, analysis="Compilation error")
    assert state3.retry_count == 1
    assert state3.is_finished is False
    
    # Case 4: Fail with retry exhausted -> triggers replan
    state4 = AgentState(
        user_context={},
        plan=["Step 1"],
        current_step_idx=0,
        selected_skill="tool",
        retry_count=1
    )
    assert state4.replan_count == 0
    state4 = route_next_state(state4, is_success=False, analysis="Compile error second time")
    assert state4.replan_count == 1
    assert state4.retry_count == 0
    assert state4.plan == []
    
    print("✅ route_next_state tests passed!")


def main():
    print("=========================================================")
    print("🚀 RUNNING EVALUATE NODE HELPER UNIT TESTS 🚀")
    print("=========================================================")
    test_extract_normalized_error()
    test_detect_loop()
    test_route_next_state()
    print("\n🎉 ALL HELPER TESTS PASSED!")

if __name__ == "__main__":
    main()
