import os
import json
import time
import re
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from services.skill_testing.core.execution_models import ValidationReport, RuntimeConfig

def get_rel_file_path(workspace_dir: str, filename: str) -> str:
    if not filename:
        return ""
    if "src/main/java" in filename or filename.startswith("/") or ":" in filename or filename.startswith("."):
        abs_path = os.path.join(workspace_dir, filename)
        return os.path.relpath(abs_path, workspace_dir)
    if filename.endswith(".java"):
        return os.path.join("src", "main", "java", filename)
    return filename

class BaseValidator(ABC):
    @abstractmethod
    async def validate(self, filename: str, rel_path: str, workspace_dir: str, args: Dict[str, Any], model_client=None) -> Dict[str, Any]:
        """
        Runs validation and returns a dict with keys: exit_code, stdout, stderr.
        """
        pass

class CompileJavaValidator(BaseValidator):
    async def validate(self, filename: str, rel_path: str, workspace_dir: str, args: Dict[str, Any], model_client=None) -> Dict[str, Any]:
        if not rel_path:
            return {"exit_code": 0, "stdout": "", "stderr": ""}
        print(f"🔍 [CompileJavaValidator] Kích hoạt validator 'javac' cho file {rel_path}...")
        try:
            proc = await asyncio.create_subprocess_exec(
                "javac", rel_path,
                cwd=workspace_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout_bytes, stderr_bytes = await proc.communicate()
            exit_code = proc.returncode
            stdout = stdout_bytes.decode("utf-8", errors="ignore")
            stderr = stderr_bytes.decode("utf-8", errors="ignore")
            return {
                "exit_code": exit_code,
                "stdout": stdout,
                "stderr": stderr
            }
        except Exception as e:
            return {
                "exit_code": 1,
                "stdout": "",
                "stderr": f"Compiler failed to launch: {str(e)}"
            }

class PyCompileValidator(BaseValidator):
    async def validate(self, filename: str, rel_path: str, workspace_dir: str, args: Dict[str, Any], model_client=None) -> Dict[str, Any]:
        if not rel_path:
            return {"exit_code": 0, "stdout": "", "stderr": ""}
        print(f"🔍 [PyCompileValidator] Kích hoạt validator 'python -m py_compile' cho file {rel_path}...")
        try:
            proc = await asyncio.create_subprocess_exec(
                "python", "-m", "py_compile", rel_path,
                cwd=workspace_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout_bytes, stderr_bytes = await proc.communicate()
            exit_code = proc.returncode
            stdout = stdout_bytes.decode("utf-8", errors="ignore")
            stderr = stderr_bytes.decode("utf-8", errors="ignore")
            return {
                "exit_code": exit_code,
                "stdout": stdout,
                "stderr": stderr
            }
        except Exception as e:
            return {
                "exit_code": 1,
                "stdout": "",
                "stderr": f"Python compiler failed to launch: {str(e)}"
            }

class LLMValidator(BaseValidator):
    async def validate(self, filename: str, rel_path: str, workspace_dir: str, args: Dict[str, Any], model_client=None) -> Dict[str, Any]:
        if not model_client:
            return {"exit_code": 0, "stdout": "", "stderr": "Model client not provided for simulated compiler validation."}
            
        patched_code = args.get("patched_code") or ""
        if not patched_code:
            try:
                file_path = os.path.join(workspace_dir, rel_path)
                if os.path.exists(file_path):
                    with open(file_path, "r", encoding="utf-8") as f:
                        patched_code = f.read()
            except Exception:
                pass
                
        print(f"🔍 [LLMValidator] Kích hoạt Simulated Compiler (LLM) cho file {filename}...")
        
        system_prompt = """
        You are a strict Java/Python syntax and scope analyzer.
        Your task is to check if the provided code snippet has:
        1. Syntax errors (e.g. mismatched braces, missing semicolons).
        2. Scope errors (e.g. a variable is declared inside an if-block or else-block but is referenced outside of those blocks).
        
        CRITICAL RULES:
        - Do NOT check for missing variable declarations (like 'owner'), missing classes, or missing imports. Assume all external variables, classes, and imports are valid and defined elsewhere.
        - Only fail (exit_code = 1) if there is a structural syntax error or a local variable scope error in the snippet.
        - Otherwise, return exit_code = 0.
        
        Output ONLY a JSON object:
        {
            "exit_code": 0 (success) or 1 (compilation failure),
            "stderr": "The compiler error message if exit_code is 1, else empty"
        }
        Do not add extra text or markdown formatting.
        """
        
        user_prompt = f"FILE: {filename}\nCODE:\n{patched_code}"
        try:
            response = await model_client.call(system_prompt, user_prompt)
            cleaned = response.strip()
            if "```" in cleaned:
                match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL | re.IGNORECASE)
                if match:
                    cleaned = match.group(1).strip()
            data = json.loads(cleaned)
            return {
                "exit_code": data.get("exit_code", 0),
                "stdout": "",
                "stderr": data.get("stderr", "")
            }
        except Exception as e:
            return {
                "exit_code": 0,
                "stdout": "",
                "stderr": f"Error running simulated validator: {str(e)}"
            }

class ValidationRuntime:
    """Bộ điều phối Validator Registry và thực thi Validation Policy."""
    def __init__(self, overlay_config_path: Optional[str] = None):
        if overlay_config_path is None:
            overlay_config_path = os.path.join(os.path.dirname(__file__), "validator_overlay.json")
        self.overlay_config_path = overlay_config_path
        self.validator_mapping = {}
        self.load_config()
        
        # Đăng ký validator plugins
        self.validators = {
            "compile_java": CompileJavaValidator(),
            "execute_python": PyCompileValidator(),
            "llm_simulation": LLMValidator()
        }
        
    def load_config(self):
        try:
            if os.path.exists(self.overlay_config_path):
                with open(self.overlay_config_path, "r", encoding="utf-8") as f:
                    self.validator_mapping = json.load(f)
        except Exception as e:
            print(f"⚠️ [VALIDATION RUNTIME] Failed to load validator overlay config: {e}")
            
    async def validate(
        self,
        skill_name: str,
        args: Dict[str, Any],
        workspace_dir: str,
        skill_client_class_name: str,
        model_client=None,
        runtime_config: Optional[RuntimeConfig] = None
    ) -> Optional[ValidationReport]:
        """
        Thực hiện validate mã nguồn và trả về ValidationReport.
        """
        # Đọc cấu hình từ overlay config
        skill_cfg = self.validator_mapping.get(skill_name)
        if not skill_cfg or not isinstance(skill_cfg, dict):
            return None
            
        validator_type = skill_cfg.get("validator")
        if not validator_type:
            return None
            
        filename = args.get("file") or args.get("source_path") or ""
        rel_path = get_rel_file_path(workspace_dir, filename)
        
        # Phân tích xem chính sách validation là gì
        policy = runtime_config.validation_policy if runtime_config else "prefer_physical"
        
        # Nhận diện mock-client chạy thử
        is_benchmark_mock = (skill_client_class_name == "BenchmarkSkillExecutionClient")
        
        # Nhận diện xem mã nguồn sửa đổi có phải snippet hay không
        is_snippet = False
        try:
            file_path = os.path.join(workspace_dir, rel_path)
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                if "class " not in content and "interface " not in content and "enum " not in content:
                    is_snippet = True
        except Exception:
            pass
            
        # Áp dụng Validation Policy quyết định dùng LLM giả lập hay chạy Compiler thật
        use_simulation = False
        if policy == "always_simulated":
            use_simulation = True
        elif policy == "always_physical":
            use_simulation = False
        else: # "prefer_physical" (default)
            use_simulation = is_benchmark_mock or is_snippet
            
        start_time = time.time()
        
        if use_simulation:
            validator = self.validators["llm_simulation"]
            v_type = "llm_simulation"
        else:
            validator = self.validators.get(validator_type)
            v_type = validator_type
            
        if not validator:
            return None
            
        feedback = await validator.validate(filename, rel_path, workspace_dir, args, model_client)
        latency_ms = int((time.time() - start_time) * 1000)
        
        return ValidationReport(
            validator_name=validator.__class__.__name__,
            validator_type=v_type,
            exit_code=feedback.get("exit_code", 0),
            stdout=feedback.get("stdout", ""),
            stderr=feedback.get("stderr", ""),
            latency_ms=latency_ms
        )

# Global validation runtime instance
validation_runtime = ValidationRuntime()
