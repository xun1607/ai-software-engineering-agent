from typing import Dict, Any, Optional

class ExecutionContext:
    """Đóng gói ngữ cảnh thực thi của các kỹ năng trong hệ thống."""
    def __init__(self, workspace_dir: str, logger=None, config: Optional[Dict[str, Any]] = None, runtime=None):
        self.workspace_dir = workspace_dir
        self.logger = logger
        self.config = config or {}
        self.runtime = runtime
        self._active_processes = set()

    def register_process(self, proc):
        """Đăng ký tiến trình con đang chạy để quản lý vòng đời."""
        self._active_processes.add(proc)

    def unregister_process(self, proc):
        """Hủy đăng ký tiến trình con sau khi hoàn tất."""
        self._active_processes.discard(proc)

    def kill_active_processes(self):
        """Buộc chấm dứt toàn bộ tiến trình con đang chạy (khi timeout)."""
        if self._active_processes:
            print(f"[RUNTIME] Tiến trình bị treo hoặc quá hạn. Đang chấm dứt {len(self._active_processes)} tiến trình con...")
            for proc in list(self._active_processes):
                try:
                    proc.kill()
                except Exception as e:
                    print(f"⚠️ [RUNTIME] Không thể terminate tiến trình: {e}")
                self._active_processes.discard(proc)

class SkillResult:
    """Kết quả chuẩn hóa trả về từ mọi kỹ năng (Executor)."""
    def __init__(self, status: str, stdout: str = "", stderr: str = "", message: str = "", data: Optional[Dict[str, Any]] = None):
        self.status = status        # "SUCCESS" hoặc "FAILED"
        self.stdout = stdout        # Log/Output chuẩn
        self.stderr = stderr        # Log lỗi hoặc stacktrace lỗi vật lý
        self.message = message      # Tin nhắn phản hồi thân thiện
        self.data = data or {}      # Dữ liệu bổ sung cụ thể của từng kỹ năng
        
    def to_dict(self) -> Dict[str, Any]:
        """Chuyển đổi thành Dictionary tương thích ngược."""
        res = {
            "status": self.status,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "message": self.message
        }
        if self.data:
            res.update(self.data)
        return res

class ExecutionRequest:
    """Yêu cầu thực thi kỹ năng bao gồm tên kỹ năng và các tham số."""
    def __init__(self, skill_name: str, args: Dict[str, Any]):
        self.skill_name = skill_name
        self.args = args

class ExecutionResult(SkillResult):
    """Kết quả thực thi từ Skill Engine."""
    pass

class ValidationReport:
    """Báo cáo kết quả kiểm tra môi trường biên dịch/chạy thử (Validation)."""
    def __init__(self, validator_name: str, validator_type: str, exit_code: int, stdout: str = "", stderr: str = "", latency_ms: int = 0):
        self.validator_name = validator_name
        self.validator_type = validator_type
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.latency_ms = latency_ms

    def to_dict(self) -> Dict[str, Any]:
        return {
            "validator_name": self.validator_name,
            "validator_type": self.validator_type,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "latency_ms": self.latency_ms
        }

class RuntimeConfig:
    """Cấu hình chạy của Runtime Layer."""
    def __init__(self, validation_policy: str = "prefer_physical", timeout: int = 30, llm_model: str = "gpt-4o-mini"):
        self.validation_policy = validation_policy
        self.timeout = timeout
        self.llm_model = llm_model

