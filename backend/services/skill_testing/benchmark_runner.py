import os
import shutil
import subprocess
import re
import errno
from typing import List, Dict, Any

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

class WorkspaceManager:
    @staticmethod
    def setup_workspace(repo_root: str, testcase_id: str, mode: str, run_id: int) -> str:
        """Copies the base repository to a unique temp workspace directory."""
        temp_root = os.path.join(BACKEND_DIR, "services", "skill_testing", "workspace_temp")
        os.makedirs(temp_root, exist_ok=True)
        
        workspace_name = f"{testcase_id}_{mode}_run{run_id}"
        workspace_path = os.path.join(temp_root, workspace_name)
        
        if os.path.exists(workspace_path):
            WorkspaceManager.destroy_workspace(workspace_path)
            
        os.makedirs(workspace_path, exist_ok=True)
        
        if repo_root:
            base_repo_path = os.path.join(BACKEND_DIR, repo_root) if not os.path.isabs(repo_root) else repo_root
            if os.path.exists(base_repo_path):
                print(f"📁 [WORKSPACE] Sao chép repository từ '{base_repo_path}' sang thư mục cô lập: '{workspace_path}'")
                shutil.copytree(base_repo_path, workspace_path, dirs_exist_ok=True)
        return workspace_path

    @staticmethod
    def destroy_workspace(workspace_path: str):
        """Removes the temp workspace directory."""
        if os.path.exists(workspace_path):
            print(f"🧹 [WORKSPACE] Dọn dẹp và xóa thư mục tạm: '{workspace_path}'")
            import stat
            for root, dirs, files in os.walk(workspace_path):
                for d in dirs:
                    try:
                        os.chmod(os.path.join(root, d), stat.S_IWRITE)
                    except Exception:
                        pass
                for f in files:
                    try:
                        os.chmod(os.path.join(root, f), stat.S_IWRITE)
                    except Exception:
                        pass
            try:
                shutil.rmtree(workspace_path, ignore_errors=True)
            except Exception as e:
                print(f"⚠️ [WORKSPACE WARNING] Không thể xóa hoàn toàn workspace {workspace_path}: {e}")

class BugInjector:
    @staticmethod
    def inject(workspace_path: str, bug_config: dict):
        """Injects a bug into the workspace source file by replacing original content with buggy content."""
        target_file = bug_config.get("target_file")
        original_content = bug_config.get("original_content")
        buggy_content = bug_config.get("buggy_content")
        
        file_path = os.path.join(workspace_path, target_file)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"❌ [INJECT ERROR] File target không tồn tại: {file_path}")
            
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            
        normalized_content = content.replace("\r\n", "\n")
        normalized_original = original_content.replace("\r\n", "\n")
        normalized_buggy = buggy_content.replace("\r\n", "\n")
        
        if normalized_original not in normalized_content:
            # Relaxed match fallback (strip leading/trailing whitespaces per line)
            print(f"⚠️ [INJECT WARNING] Không tìm thấy đoạn code gốc chính xác. Thử tìm kiếm với khoảng trắng đơn giản...")
            norm_content_lines = [l.strip() for l in normalized_content.split("\n")]
            norm_orig_lines = [l.strip() for l in normalized_original.split("\n") if l.strip()]
            
            # Find start index
            matched = False
            for idx in range(len(norm_content_lines) - len(norm_orig_lines) + 1):
                sub = norm_content_lines[idx:idx+len(norm_orig_lines)]
                if sub == norm_orig_lines:
                    # Found! Let's reconstruct or raise warning
                    matched = True
                    break
            
            if not matched:
                raise ValueError(f"❌ [INJECT ERROR] Không tìm thấy đoạn mã gốc trong file để inject bug:\n{original_content}")
            
        new_content = normalized_content.replace(normalized_original, normalized_buggy)
        with open(file_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(new_content)
        print(f"🐛 [BUG INJECTOR] Đã tiêm lỗi vào file: {target_file}")

class PipelineVerifier:
    @staticmethod
    def run_cmd(workspace_path: str, cmd_list: List[str]) -> tuple[int, str]:
        """Runs a subprocess command within the workspace directory."""
        use_shell = os.name == "nt"
        try:
            result = subprocess.run(
                cmd_list,
                cwd=workspace_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=use_shell,
                timeout=180
            )
            stdout = result.stdout or ""
            stderr = result.stderr or ""
            return result.returncode, stdout + "\n" + stderr
        except subprocess.TimeoutExpired as te:
            stdout = te.stdout.decode("utf-8", errors="ignore") if te.stdout else ""
            stderr = te.stderr.decode("utf-8", errors="ignore") if te.stderr else ""
            return -1, f"TIMEOUT EXPIRED: {stdout}\n{stderr}"
        except Exception as e:
            return -2, f"EXCEPTION: {str(e)}"

    @classmethod
    def verify_pre_run(cls, workspace_path: str, bug_type: str, build_cmd: List[str], val_cmd: List[str]) -> bool:
        """Verifies that the workspace compiles/fails tests as expected BEFORE the agent runs."""
        print(f"🔬 [PRE-VERIFY] Kiểm tra trước khi chạy Agent. Yêu cầu build/test thất bại do lỗi '{bug_type}'...")
        
        code, output = cls.run_cmd(workspace_path, build_cmd)
        if "NullPointerException" in bug_type or "logical" in bug_type.lower():
            if code != 0:
                print(f"✅ [PRE-VERIFY SUCCESS] Build thất bại (Exit code: {code}) đúng như dự đoán.")
                return True
                
            code_val, output_val = cls.run_cmd(workspace_path, val_cmd)
            if code_val != 0:
                print(f"✅ [PRE-VERIFY SUCCESS] Test thất bại (Exit code: {code_val}) đúng như dự đoán.")
                return True
            else:
                print("❌ [PRE-VERIFY FAILED] Test chạy thành công dù lỗi đã được inject!")
                return False
        else:
            if code != 0:
                print(f"✅ [PRE-VERIFY SUCCESS] Build thất bại (Exit code: {code}) đúng như dự đoán cho lỗi biên dịch.")
                return True
            else:
                print("❌ [PRE-VERIFY FAILED] Build chạy thành công dù lỗi biên dịch đã được inject!")
                return False

    @classmethod
    def verify_post_run(cls, workspace_path: str, expected_config: dict) -> tuple[bool, str]:
        """Verifies the agent's patch against the assertions in expected.json."""
        print(f"🔬 [POST-VERIFY] Kiểm tra sau khi chạy Agent...")
        targets = expected_config.get("validation_targets", {})
        
        if targets.get("verify_compilation", True):
            comp_assert = expected_config.get("compilation_assertion", {})
            cmd = comp_assert.get("command")
            expected_code = comp_assert.get("expected_exit_code", 0)
            
            code, output = cls.run_cmd(workspace_path, cmd)
            if code != expected_code:
                return False, f"Lỗi biên dịch: Lệnh {cmd} trả về exit code {code} thay vì {expected_code}.\nOutput: {output[:1000]}"
            print("   - [POST-VERIFY] Biên dịch thành công!")
            
        if targets.get("verify_tests", True):
            test_assert = expected_config.get("test_assertion", {})
            cmd = test_assert.get("command")
            expected_code = test_assert.get("expected_exit_code", 0)
            
            code, output = cls.run_cmd(workspace_path, cmd)
            if code != expected_code:
                return False, f"Lỗi chạy Test: Lệnh {cmd} trả về exit code {code} thay vì {expected_code}.\nOutput: {output[:1000]}"
            print("   - [POST-VERIFY] Tất cả testcases đều pass!")

        if targets.get("verify_patch", True):
            patch_assert = expected_config.get("patch_assertion", {})
            modified_files = patch_assert.get("modified_files", [])
            prohibited_patterns = patch_assert.get("prohibited_patterns", [])
            required_patterns = patch_assert.get("required_patterns", [])
            
            for rel_file in modified_files:
                file_path = os.path.join(workspace_path, rel_file)
                if not os.path.exists(file_path):
                    return False, f"File vá lỗi mong đợi không tồn tại: {rel_file}"
                    
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    
                for pattern in prohibited_patterns:
                    if pattern in content:
                        return False, f"Phát hiện mẫu cấm '{pattern}' trong file {rel_file}"
                        
                for pattern in required_patterns:
                    if pattern not in content:
                        return False, f"Thiếu mẫu bắt buộc '{pattern}' trong file {rel_file}"
            print("   - [POST-VERIFY] Kiểm tra các mẫu mã nguồn (regex) hợp lệ!")
            
        return True, "Tất cả điều kiện kiểm chứng đều thành công!"
