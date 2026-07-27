from swe_agent.evaluator.syntax_checker import SyntaxEvaluator
from swe_agent.evaluator.test_runner import RuntimeEvaluator

class VerifyNode:
    def __init__(self, sandbox, default_test_cmd: str = None):
        self.sandbox = sandbox
        self.evaluator = RuntimeEvaluator(sandbox)
        # Cho phép cấu hình lệnh test mặc định (ví dụ: "pytest tests/")
        self.default_test_cmd = default_test_cmd

    def __call__(self, state):
        print("[Node: Verify] Starting verification process...")
        
        test_command = state.get("test_command") or self.default_test_cmd
        
        filename = state.get("current_file")
        
        iter_count = state.get("iteration_count", 0)
        
        if not test_command and not filename:
            if iter_count < 3:
                print(f"[Node: Verify] No file edited yet (Iteration {iter_count}). Requesting code fix...")
                return {"is_valid": False, "feedback": "Context inspected. Please call edit_file or python_syntax_fixer to apply the bug fix."}
            return {"is_valid": True}

        # --- BƯỚC 1: KIỂM TRA CÚ PHÁP (Nếu là file Python) ---
        if filename and filename.endswith(".py"):
            code = self.sandbox.read_file(filename)
            ok, err = SyntaxEvaluator.validate_python_code(code)
            if not ok:
                return {"is_valid": False, "feedback": f"Syntax Error: {err}"}

        # --- BƯỚC 2: THỰC THI KIỂM THỬ (RUNTIME) ---
        # Nếu không có test_command, ta thử chạy file đó (fallback logic)
        final_cmd = test_command or f"python {filename}"
        
        print(f"--- Running Test Command: {final_cmd} ---")
        run_res = self.evaluator.run_custom_test(final_cmd)
        
        combined_output = f"{run_res.stdout}\n{run_res.stderr}"
        is_failed = False
        
        if run_res.exit_code != 0:
            is_failed = True
        elif "FAILED (" in combined_output or "FAIL:" in combined_output or "ERRORS:" in combined_output:
            is_failed = True
        elif "'failed': " in combined_output and "'failed': 0" not in combined_output:
            is_failed = True
        elif "Traceback (most recent call last):" in combined_output or "SyntaxError:" in combined_output or "BeanCreationException" in combined_output:
            is_failed = True
            
        verify_log = {
            "tool": "verify_test_runner",
            "args": {"command": final_cmd},
            "output": f"Exit Code: {run_res.exit_code}\nSTDOUT:\n{run_res.stdout}\nSTDERR:\n{run_res.stderr}"[:3000]
        }
        
        if is_failed:
            error_feedback = f"Test Failed!\nSTDOUT: {run_res.stdout}\nSTDERR: {run_res.stderr}"
            return {"is_valid": False, "feedback": error_feedback, "execution_logs": [verify_log]}
            
        return {"is_valid": True, "feedback": "All tests passed!", "execution_logs": [verify_log]}