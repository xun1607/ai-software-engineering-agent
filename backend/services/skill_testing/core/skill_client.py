import asyncio
import subprocess
import os
import re
import sys

class SkillExecutionClient:
    """Môi trường thực thi kỹ năng (AG2 Runtime Engine) trên Hệ điều hành"""
    def __init__(self, workspace_path: str = None):
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
        
    def setup_initial_workspace(self, code_content: str, filename: str = "LoginService.java") -> str:
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
        print(f"⏳ [RUNTIME RUN] -> Đang thực thi REAL kỹ năng '{skill_name}' trên ổ cứng...")
        
        # CHUẨN HÓA: Biến 'analyze-stacktrace' thành 'analyze_stacktrace' để code Python dễ bắt
        name_clean = skill_name.lower().replace("-", "_")
        
        # --- SKILL 1: PHÂN TÍCH STACKTRACE THẬT ---
        if name_clean == "analyze_stacktrace":
            raw_stacktrace = args.get("stacktrace", "")
            
            # 1. Parse Python stacktrace (e.g. File "data_sync.py", line 4)
            py_match = re.search(r'File\s+["\']([^"\']+)["\'],\s*line\s*(\d+)', raw_stacktrace)
            # 2. Parse Java stacktrace (e.g. at CalculatorService.divide(CalculatorService.java:3) or at Customer.getEmail(Customer.java:12))
            java_match = re.search(r'at\s+[\w\.]+\([\w\-]+\.java:(\d+)\)', raw_stacktrace)
            # Find any .java file mentioned
            java_file_match = re.search(r'([\w\-]+\.java)', raw_stacktrace)
            
            parsed_file = None
            parsed_line = 1
            
            if py_match:
                parsed_file = py_match.group(1)
                parsed_line = int(py_match.group(2))
            elif java_match:
                parsed_line = int(java_match.group(1))
                if java_file_match:
                    parsed_file = java_file_match.group(1)
            elif java_file_match:
                parsed_file = java_file_match.group(1)
            
            # Fallback to arguments or dynamically detect file in workspace
            if not parsed_file:
                parsed_file = args.get("file") or args.get("source_path")
                if not parsed_file:
                    import glob
                    java_files = glob.glob(os.path.join(self.java_src_dir, "*.java"))
                    py_files = glob.glob(os.path.join(self.workspace_dir, "*.py"))
                    if java_files:
                        parsed_file = os.path.basename(java_files[0])
                    elif py_files:
                        parsed_file = os.path.basename(py_files[0])
                    else:
                        parsed_file = "LoginService.java"
            
            return {
                "status": "SUCCESS",
                "file": parsed_file,
                "line": parsed_line,
                "stdout": f"Parsed frame: {parsed_file} at line {parsed_line}.",
                "message": f"✅ [SKILL LOG] Khớp hiện trường: Phát hiện điểm nghẽn tại {parsed_file}:{parsed_line}."
            }
        
        # --- SKILL 2: ĐỌC NGỮ CẢNH CODE ---
        elif name_clean == "read_code_context":
            filename = args.get("file") or args.get("source_path")
            if not filename:
                import glob
                java_files = glob.glob(os.path.join(self.java_src_dir, "*.java"))
                py_files = glob.glob(os.path.join(self.workspace_dir, "*.py"))
                if java_files:
                    filename = os.path.basename(java_files[0])
                elif py_files:
                    filename = os.path.basename(py_files[0])
                else:
                    filename = "LoginService.java"
                    
            target_line = int(args.get("line", 1))
            file_path = os.path.join(self.java_src_dir if filename.endswith(".java") else self.workspace_dir, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                start = max(0, target_line - 6)
                end = min(len(lines), target_line + 5)
                code_snippet = "".join(lines[start:end])
                return {
                    "status": "SUCCESS",
                    "stdout": code_snippet,
                    "message": f"🚀 [SKILL LOG] Đã bốc mã nguồn từ {filename} xung quanh dòng {target_line}"
                }
            except Exception as e:
                return {"status": "FAILED", "stdout": str(e)}
 
        # --- SKILL 3: GHI BẢN SỬA CODE MỚI ---
        elif name_clean == "suggest_java_fix":
            filename = args.get("file") or args.get("source_path")
            if not filename:
                import glob
                java_files = glob.glob(os.path.join(self.java_src_dir, "*.java"))
                if java_files:
                    filename = os.path.basename(java_files[0])
                else:
                    filename = "LoginService.java"
                    
            patched_code = args.get("patched_code") or args.get("code_context") or args.get("code_snippet")
            file_path = os.path.join(self.java_src_dir, filename)
            
            if not patched_code:
                return {"status": "FAILED", "stdout": "Missing patched_code parameter."}
                
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(patched_code)
                return {
                    "status": "SUCCESS",
                    "stdout": "File updated successfully.",
                    "message": f"🔧 [SKILL LOG] Agent đã vá file {filename} vật lý xuống đĩa cứng!"
                }
            except Exception as e:
                return {"status": "FAILED", "stdout": str(e)}
 
        # --- SKILL 4: BIÊN DỊCH JAVAC ---
        elif name_clean == "debug_java_null_pointer":
            filename = args.get("file") or args.get("source_path")
            if not filename:
                import glob
                java_files = glob.glob(os.path.join(self.java_src_dir, "*.java"))
                if java_files:
                    filename = os.path.basename(java_files[0])
                else:
                    filename = "LoginService.java"
                    
            file_path = os.path.join(self.java_src_dir, filename)
            rel_file_path = os.path.relpath(file_path, self.workspace_dir)
            try:
                import subprocess
                result = await asyncio.to_thread(
                    subprocess.run,
                    ["javac", rel_file_path],
                    cwd=self.workspace_dir,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0:
                    return {
                        "status": "SUCCESS",
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "returncode": result.returncode,
                        "message": f"✅ [SKILL LOG] Javac xác nhận: File {filename} sạch bóng lỗi cú pháp!"
                    }
                else:
                    return {
                        "status": "FAILED",
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "returncode": result.returncode,
                        "message": "❌ Lỗi biên dịch cú pháp Java."
                    }
            except subprocess.TimeoutExpired as te:
                return {
                    "status": "FAILED",
                    "stdout": te.stdout or "",
                    "stderr": te.stderr or "TIMEOUT: Lệnh biên dịch javac bị treo và vượt quá 30 giây.",
                    "message": "❌ Lỗi timeout biên dịch."
                }
            except Exception as e:
                return {
                    "status": "FAILED",
                    "stdout": "",
                    "stderr": str(e),
                    "message": "❌ Lỗi hệ thống khi thực thi javac."
                }
 
        # --- SKILL 5: THỰC THI PYTHON THẬT ---
        elif name_clean == "debug_python_error":
            filename = args.get("file") or args.get("source_path")
            if not filename:
                import glob
                py_files = glob.glob(os.path.join(self.workspace_dir, "*.py"))
                if py_files:
                    filename = os.path.basename(py_files[0])
                else:
                    filename = "data_sync.py"
                    
            if not filename.endswith(".py"):
                filename += ".py"
                
            file_path = os.path.join(self.workspace_dir, filename)
            try:
                import subprocess
                # Check for virtual environment python executable
                python_exe = os.path.join(os.path.dirname(self.workspace_dir), "venv", "Scripts", "python.exe")
                if not os.path.exists(python_exe):
                    python_exe = sys.executable # Use current running Python interpreter
                
                result = await asyncio.to_thread(
                    subprocess.run,
                    [python_exe, filename],
                    cwd=self.workspace_dir,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0:
                    return {
                        "status": "SUCCESS",
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "returncode": result.returncode,
                        "message": f"✅ [SKILL LOG] Python xác nhận: File {filename} chạy không lỗi!"
                    }
                else:
                    return {
                        "status": "FAILED",
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "returncode": result.returncode,
                        "message": f"❌ Lỗi thực thi Python: {result.stderr}"
                    }
            except subprocess.TimeoutExpired as te:
                return {
                    "status": "FAILED",
                    "stdout": te.stdout or "",
                    "stderr": te.stderr or "TIMEOUT: Lệnh thực thi python bị treo.",
                    "message": "❌ Lỗi timeout Python."
                }
            except Exception as e:
                return {
                    "status": "FAILED",
                    "stdout": "",
                    "stderr": str(e),
                    "message": "❌ Lỗi hệ thống khi thực thi Python."
                }
 
        # --- SKILL 6: GHI BẢN SỬA PYTHON THẬT ---
        elif name_clean == "suggest_python_fix":
            filename = args.get("file") or args.get("source_path")
            if not filename:
                import glob
                py_files = glob.glob(os.path.join(self.workspace_dir, "*.py"))
                if py_files:
                    filename = os.path.basename(py_files[0])
                else:
                    filename = "data_sync.py"
                    
            patched_code = args.get("patched_code") or args.get("code_context") or args.get("code_snippet")
            file_path = os.path.join(self.workspace_dir, filename)
            
            if not patched_code:
                return {"status": "FAILED", "stdout": "Missing patched_code parameter."}
                
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(patched_code)
                return {
                    "status": "SUCCESS",
                    "stdout": "File updated successfully.",
                    "message": f"🔧 [SKILL LOG] Agent đã vá file {filename} vật lý xuống đĩa cứng!"
                }
            except Exception as e:
                return {"status": "FAILED", "stdout": str(e)}
                
        return {"status": "FAILED", "stdout": f"Unknown skill: {skill_name}"}