# import asyncio

# class SkillExecutionClient:
#     def __init__(self, base_url: str = None):
#         self.base_url = base_url

#     async def execute_skill(self, skill_name: str, args: dict) -> dict:
#         """
#         MOCK HÔM NAY: Giả lập đầu ra của hệ thống dựa theo tên kỹ năng (skill_name)
#         nhận từ execute_node để chạy thông suốt vòng lặp.
#         """
#         print(f"⏳ [MOCK RUNTIME] -> Môi trường đang thực thi công cụ ngầm cho '{skill_name}'...")
#         await asyncio.sleep(0.5) # Mô phỏng độ trễ hệ thống
        
#         name_lower = skill_name.lower()
        
#         # Kịch bản 1: Kỹ năng đọc mã nguồn
#         if "read" in name_lower or "view" in name_lower:
#             return {
#                 "status": "SUCCESS",
#                 "output": f"// Content of target Java file at: {args.get('path', 'src/Main.java')}\npublic class App {{ }}"
#             }
            
#         # Kịch bản 2: Kỹ năng chạy Unit Test (Java Maven)
#         elif "test" in name_lower or "maven" in name_lower:
#             return {
#                 "status": "SUCCESS",
#                 "output": "🚀 BUILD SUCCESS. Total tests run: 14, Failures: 0, Errors: 0"
#             }
            
#         # Mặc định cho các tác vụ khác
#         return {
#             "status": "SUCCESS",
#             "output": f"Successfully executed tool '{skill_name}' with args: {args}"
#         }

import asyncio
import json

class SkillExecutionClient:
    """
    Mock Service thực thi Skill (AG2 Runtime).
    Nhận tên kỹ năng và tham số đã bóc tách từ Executor Node,
    mô phỏng chạy thực tế và trả ra Log kết quả phù hợp để mồi cho Evaluator.
    """
    def __init__(self, base_url: str = None):
        self.base_url = base_url

    async def execute_skill(self, skill_name: str, args: dict) -> dict:
        print(f"⏳ [RUNTIME RUN] -> Môi trường cô lập đang thực thi kỹ năng '{skill_name}'...")
        await asyncio.sleep(0.8)  # Mô phỏng độ trễ chạy compiler thật
        
        name_lower = skill_name.lower().replace("-", "_")
        
        # 1. Kịch bản chạy Test Python/Java
        if "test" in name_lower or "maven" in name_lower:
            code = args.get("code_snippet", "")
            return {
                "status": "SUCCESS",
                "exit_code": 0,
                "stdout": "🚀 BUILD SUCCESS. Total tests run: 5, Failures: 0, Errors: 0",
                "message": "All unit tests passed successfully."
            }
            
        # 2. Kịch bản đọc context code nguồn
        elif "read_code" in name_lower or "view" in name_lower:
            file_name = args.get("file", "unknown_file")
            return {
                "status": "SUCCESS",
                "exit_code": 0,
                "stdout": f"// Code context of {file_name}\npublic class LoginService {{\n    public void login(User user) {{\n        if (user == null) throw new IllegalArgumentException('User is null');\n    }}\n}}",
                "message": f"Successfully read file {file_name}."
            }
            
        # 3. Kịch bản phân tích Log lỗi (Stacktrace Analysis)
        elif "analyze" in name_lower or "debug" in name_lower:
            return {
                "status": "SUCCESS",
                "exit_code": 0,
                "stdout": json.dumps({
                    "file": "LoginService.java",
                    "line": 42,
                    "variable": "user",
                    "error_type": "NullPointerException"
                }),
                "message": "Stacktrace analyzed. Root cause identified at LoginService.java:42."
            }
            
        # 4. Kịch bản đề xuất bản vá (Fix suggestion)
        elif "suggest" in name_lower or "fix" in name_lower:
            return {
                "status": "SUCCESS",
                "exit_code": 0,
                "stdout": "Patch suggested: Add null-safety check 'if (user != null)' before dereferencing.",
                "message": "Suggested fix pattern generated."
            }
            
        # Mặc định
        return {
            "status": "SUCCESS",
            "exit_code": 0,
            "stdout": f"Executed tool with arguments: {args}",
            "message": "Command executed."
        }