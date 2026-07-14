import asyncio
import os
import sys
import importlib
from services.skill_testing.core.execution_models import ExecutionContext, SkillResult

class SkillExecutionClient:
    """Môi trường thực thi kỹ năng (AG2 Runtime Engine)"""
    def __init__(self, workspace_path: str = None, logger=None, config: dict = None, runtime=None):
        # Đọc từ env WORKSPACE_PATH, fallback về tham số workspace_path, sau đó fallback về relative path
        env_path = os.environ.get("WORKSPACE_PATH")
        fallback_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "workspace")
        )
        target_path = env_path or workspace_path or fallback_path
        
        self.workspace_dir = os.path.abspath(target_path)
        os.makedirs(self.workspace_dir, exist_ok=True)
        self.java_src_dir = os.path.join(self.workspace_dir, "src", "main", "java")
        os.makedirs(self.java_src_dir, exist_ok=True)
        
        # Khởi tạo ExecutionContext thống nhất cho mọi kỹ năng
        self.context = ExecutionContext(
            workspace_dir=self.workspace_dir,
            logger=logger,
            config=config,
            runtime=runtime
        )

    def get_file_path(self, filename: str) -> str:
        if not filename:
            return ""
        if "src/main/java" in filename or filename.startswith("/") or ":" in filename or filename.startswith("."):
            return os.path.join(self.workspace_dir, filename)
        if filename.endswith(".java"):
            return os.path.join(self.java_src_dir, filename)
        return os.path.join(self.workspace_dir, filename)
        
    def setup_initial_workspace(self, code_content: str, filename: str = "") -> str:
        """Ghi đoạn code lỗi do người dùng paste vào thành file Java hoặc Python trên ổ cứng"""
        if filename.endswith(".py"):
            file_path = os.path.join(self.workspace_dir, filename)
        else:
            file_path = os.path.join(self.java_src_dir, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(code_content)
        print(f"📂 [WORKSPACE] Đã thiết lập hiện trường! Ghi file code lỗi tại: {file_path}")
        return file_path
    
    async def execute_skill(self, skill_name: str, args: dict) -> dict:
        import time
        import traceback
        
        name_clean = skill_name.lower().replace("-", "_")
        print(f"\n⏳ [RUNTIME] -> Đang khởi chạy kỹ năng '{skill_name}'...")
        print(f"   - Tham số đầu vào: {args}")
        
        start_time = time.time()
        timeout_sec = self.context.config.get("timeout_sec", 30.0)
        
        try:
            # Import tool của skill
            module_path = f"services.skill_testing.skills.{name_clean}.executor"
            module = importlib.import_module(module_path)
            execute_fn = getattr(module, "execute", None)
            
            if not execute_fn:
                raise ImportError(f"Không tìm thấy hàm 'execute' trong module {module_path}")
                
            # Thực thi kỹ năng với thời gian giới hạn (Timeout)
            result: SkillResult = await asyncio.wait_for(
                execute_fn(self.context, args),
                timeout=timeout_sec
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            print(f"✅ [RUNTIME] Kỹ năng '{skill_name}' thực thi HOÀN TẤT ({latency_ms}ms) | Trạng thái: {result.status}")
            return result.to_dict()
            
        except asyncio.TimeoutError:
            latency_ms = int((time.time() - start_time) * 1000)
            print(f"❌ [RUNTIME] Kỹ năng '{skill_name}' BỊ QUÁ HẠN TIMEOUT sau {timeout_sec}s! Dọn dẹp tài nguyên...")
            self.context.kill_active_processes()
            
            return {
                "status": "FAILED",
                "stdout": "",
                "stderr": f"TIMEOUT EXPIRED: Lệnh thực thi vượt quá giới hạn thời gian {timeout_sec} giây.",
                "message": f"❌ Lỗi timeout thực thi kỹ năng '{skill_name}'."
            }
        except ImportError as ie:
            latency_ms = int((time.time() - start_time) * 1000)
            print(f"❌ [RUNTIME] Lỗi import động kỹ năng '{skill_name}': {ie}")
            return {
                "status": "FAILED",
                "stdout": "",
                "stderr": str(ie),
                "message": f"❌ Không tìm thấy bộ thực thi cho kỹ năng '{skill_name}'"
            }
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            print(f"❌ [RUNTIME] Ngoại lệ chưa xử lý khi chạy kỹ năng '{skill_name}': {e}")
            traceback.print_exc()
            return {
                "status": "FAILED",
                "stdout": "",
                "stderr": f"{str(e)}\n{traceback.format_exc()}",
                "message": f"❌ Lỗi hệ thống trong quá trình thực thi kỹ năng: {str(e)}"
            }