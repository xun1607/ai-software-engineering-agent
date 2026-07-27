# class MockModelClient: danh cho plan_select_test.py
#     def __init__(self, responses: dict):
#         self.responses = responses # Lưu các phản hồi giả lập

#     def call(self, system_prompt, user_prompt):
#         # Trả về kết quả dựa trên từ khóa trong prompt
#         for key in self.responses:
#             if key in system_prompt or key in user_prompt:
#                 return self.responses[key]
#         return "{}"

# backend/services/skill_testing/unit_tests/mock_clients.py

class MockModelClient:
    def __init__(self, responses: dict):
        self.responses = responses

    async def call(self, system_prompt, user_prompt):
        # 1. Trả về kết quả cho execute_node và evaluate_node dựa trên vai trò
        if "Parameter Extractor" in system_prompt and "extract_args" in self.responses:
            return self.responses.get("extract_args", "{}")
        if "Quality Assurance Engineer" in system_prompt and "evaluate" in self.responses:
            return self.responses.get("evaluate", '{"is_success": true}')
            
        # 2. Fallback tìm từ khóa trong prompt để hỗ trợ plan_select_test
        for key in self.responses:
            if key in system_prompt or key in user_prompt:
                return self.responses[key]
                
        return "{}"

class MockSkillClient:
    def __init__(self, result: dict):
        self.result = result

    async def execute_skill(self, skill_id, args):
        # Giả lập kết quả trả về từ API skill_management
        return self.result