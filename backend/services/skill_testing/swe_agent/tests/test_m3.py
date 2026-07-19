import unittest
import os
import shutil
from swe_agent.evaluator.syntax_checker import SyntaxEvaluator
from swe_agent.evaluator.test_runner import RuntimeEvaluator
from swe_agent.core.sandbox import LocalSandbox

class TestMilestone3(unittest.TestCase):
    def setUp(self):
        self.workspace = "./test_m3_workspace"
        self.sandbox = LocalSandbox(self.workspace)
        self.runtime_evaluator = RuntimeEvaluator(self.sandbox)

    def tearDown(self):
        if os.path.exists(self.workspace):
            shutil.rmtree(self.workspace)

    def test_syntax_checker_invalid(self):
        """Kiểm tra mã nguồn lỗi cú pháp (thiếu dấu hai chấm)."""
        bad_code = "def hello()\n    print('world')"
        is_valid, error = SyntaxEvaluator.validate_python_code(bad_code)
        
        self.assertFalse(is_valid)
        self.assertIn("SyntaxError", error)
        self.assertIn("line 1", error)
        print(f"✅ Caught Syntax Error: {error}")

    def test_syntax_checker_valid(self):
        """Kiểm tra mã nguồn đúng cú pháp."""
        good_code = "def hello():\n    print('world')"
        is_valid, error = SyntaxEvaluator.validate_python_code(good_code)
        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_runtime_evaluator_fail(self):
        """Kiểm tra khi thực thi script test bị fail."""
        # Tạo 1 file test gây lỗi
        test_code = "assert 1 == 2"
        self.sandbox.write_file("test_fail.py", test_code)
        
        response = self.runtime_evaluator.run_custom_test("python test_fail.py")
        
        self.assertNotEqual(response.exit_code, 0)
        self.assertIn("AssertionError", response.stderr)
        print("✅ Caught Runtime Test Failure")

if __name__ == "__main__":
    unittest.main()