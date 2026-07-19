import unittest
import os
import shutil
from swe_agent.core.sandbox import LocalSandbox

class TestMilestone1(unittest.TestCase):
    def test_milestone_1(self):
        print("🚀 Testing Milestone 1: LocalSandbox...")
        
        # 1. Khởi tạo Sandbox tại thư mục tạm
        sandbox = LocalSandbox(workspace_dir="./test_workspace")
        
        # 2. Test Write File
        code = "print('Hello World from CASS-ready Agent')"
        sandbox.write_file("hello.py", code)
        print("✅ Write file: OK")
        
        # 3. Test Execute Command
        response = sandbox.execute_command("python hello.py")
        
        print(f"STDOUT: {response.stdout.strip()}")
        print(f"EXIT CODE: {response.exit_code}")
        
        # 4. Kiểm tra DoD
        self.assertIn("Hello World", response.stdout)
        self.assertEqual(response.exit_code, 0)
        print("✅ Execute command: OK")
        
        # 5. Kiểm tra thông tin môi trường cho CASS
        env_info = sandbox.get_environment_info()
        print(f"✅ Environment Info for CASS: {env_info}")
        
        # Dọn dẹp
        if os.path.exists("./test_workspace"):
            shutil.rmtree("./test_workspace")

if __name__ == "__main__":
    unittest.main()