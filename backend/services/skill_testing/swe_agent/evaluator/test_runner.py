from ..core.base import AbstractSandbox, SandboxResponse

class RuntimeEvaluator:
    """Cấp độ 2: Thực thi kiểm thử trong môi trường cô lập."""
    
    def __init__(self, sandbox: AbstractSandbox):
        self.sandbox = sandbox

    def run_pytest(self, test_file: str = "tests/") -> SandboxResponse:
        """Chạy pytest và trả về kết quả cấu trúc."""
        # Chúng ta giả định pytest đã được cài đặt trong môi trường
        return self.sandbox.execute_command(f"python -m pytest {test_file}")

    def run_custom_test(self, command: str) -> SandboxResponse:
        """Chạy bất kỳ lệnh test nào (ví dụ: python test_script.py)."""
        return self.sandbox.execute_command(command)