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
        
        if not test_command and not filename:
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
        
        if run_res.exit_code != 0:
            # Trả về cả stdout và stderr để Agent có đủ thông tin sửa lỗi
            error_feedback = f"Test Failed!\nSTDOUT: {run_res.stdout}\nSTDERR: {run_res.stderr}"
            return {"is_valid": False, "feedback": error_feedback}
            
        return {"is_valid": True, "feedback": "All tests passed!"}