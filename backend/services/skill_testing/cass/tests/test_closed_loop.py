import unittest
import os
from cass.core import CASS

# --- MOCK SKILLS ---
def skill_good(input_val: str):
    return f"Success: {input_val}"

def skill_unreliable(input_val: str):
    raise Exception("Random Hardware Failure!")

class TestCASSClosedLoop(unittest.TestCase):
    def setUp(self):
        self.db_path = "closed_loop.db"
        self.cass = CASS(self.db_path)
        self.session_id = "agent-session-001"
        
        # Giả lập danh sách skill thô (như lấy từ SKILL.md)
        self.all_skills = [
            {
                "name": "skill-good", 
                "description": "Reliable data processing",
                "constraints": {"host": {"os": []}, "resources": {"memory": "10MB"}}
            },
            {
                "name": "skill-unreliable", 
                "description": "Reliable data processing", # Cố tình để mô tả giống nhau
                "constraints": {"host": {"os": []}, "resources": {"memory": "10MB"}}
            }
        ]

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_learning_from_failure(self):
        """
        Chứng minh CASS học từ lỗi:
        1. Gọi skill_unreliable và bị lỗi.
        2. Kiểm tra xem lần sau CASS có ưu tiên chọn skill_good không.
        """
        import random
        random.seed(42)
        subtask = "process some data"
        
        # LƯỢT 1: Giả sử LLM chọn skill-unreliable và bị lỗi nhiều lần
        proxy_bad = self.cass.wrap_skill(skill_unreliable, self.session_id)
        for _ in range(5):
            try:
                proxy_bad(input_val="test")
            except:
                pass # Ghi nhận lỗi xong
        
        # LƯỢT 2: Giả sử gọi lại subtask tương tự
        optimized_skills = self.cass.get_optimized_skills(
            self.all_skills, self.session_id, subtask, top_k=1
        )
        
        # Kết quả: Phải chọn skill-good vì skill-unreliable đã bị hạ điểm uy tín (Beta tăng)
        self.assertEqual(optimized_skills[0]["name"], "skill-good")
        
        # Kiểm tra DB xem Beta của skill-unreliable có tăng không
        metrics = self.cass.db_manager.get_metrics(["skill-unreliable"])
        self.assertEqual(metrics["skill-unreliable"]["beta"], 6) # 1 (mặc định) + 5 (lỗi)

if __name__ == "__main__":
    unittest.main()