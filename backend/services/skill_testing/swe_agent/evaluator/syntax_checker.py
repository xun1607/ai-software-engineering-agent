import ast
from typing import Tuple, Optional

class SyntaxEvaluator:
    """syntax checker for Python code snippets"""
    
    @staticmethod
    def validate_python_code(code: str) -> Tuple[bool, Optional[str]]:
        """
        check python syntax
        return: (Is_Valid, Error_Message)
        """
        try:
            ast.parse(code)
            return True, None
        except SyntaxError as e:
            # Trích xuất chi tiết lỗi để Agent dễ sửa
            error_details = (
                f"SyntaxError at line {e.lineno}, offset {e.offset}: "
                f"{e.msg}\nCode: {e.text.strip() if e.text else 'unknown'}"
            )
            return False, error_details
        except Exception as e:
            return False, f"Unexpected error during syntax check: {str(e)}"