---
name: analyze-python-error
description: Analyzes a Python exception stacktrace to pinpoint the exact file, line number, variable, and error type causing the crash. Designed for user-code frames only, ignoring stdlib and third-party library frames.
goal: "Return the precise source location (file, line, variable, error_type) of a Python exception so that a fix can be applied without manual debugging."
version: 1.0.0
category: SoftwareEngineering/Debugging
level: atomic
tags: [python, stacktrace, debug, attributeerror, typeerror]

# ── Layer 1: Specification ───────────────────────────────────────────────────
input:
  type: object
  required: [stacktrace, source_path]
  properties:
    stacktrace:
      type: string
      description: Full Python exception traceback text
    source_path:
      type: string
      description: Path or filename of the Python source file

output:
  type: object
  properties:
    file:
      type: string
      description: Python source filename where the error occurred (e.g. buggy_code.py)
    line:
      type: integer
      description: Line number of the crash
    variable:
      type: string
      description: The variable or expression that is None/invalid (e.g. self.current_user)
    error_type:
      type: string
      description: The Python exception class (e.g. AttributeError, TypeError, KeyError)

constraints:
  host:
    os: [linux, darwin, windows]
  resources:
    memory: "512MB"
    timeout: "30s"
  safety:
    fs_access: read-only
    requires_approval: false

acceptance_criteria:
  - "output.file must end with .py and be a user-code file (not stdlib or site-packages)"
  - "output.line must be within ±2 lines of the actual crash line in the traceback"
  - "output.error_type must match the exception class name in the last line of the traceback"
  - "output.variable must identify the object/expression that caused the error"

metrics:
  pass_rate:
    target: "≥ 80%"
    unit: "%"
  accuracy:
    target: "≥ 85%"
    unit: "%"
  latency_p95:
    target: "< 5000"
    unit: "ms"
  token_usage:
    target: "< 800"
    unit: "tokens/call"
  retry_rate:
    target: "< 10%"
    unit: "%"

# ── Layer 2: Design ──────────────────────────────────────────────────────────
reasoning_strategy: chain-of-thought
fallback_strategy: "If no user-code frame is found (all frames are stdlib/site-packages), return the last frame in the traceback and set variable to 'unknown'."

examples:
  - input:
      stacktrace: |
        Traceback (most recent call last):
          File "app/service.py", line 42, in get_user
            return self.db.find_user(user_id)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^
        AttributeError: 'NoneType' object has no attribute 'find_user'
      source_path: "app/"
    expected_output:
      file: "service.py"
      line: 42
      variable: "self.db"
      error_type: "AttributeError"

# ── Layer 5: Evaluation — Test Cases ────────────────────────────────────────
test_cases:
  - id: TC-001
    name: "AttributeError on None attribute access"
    input:
      stacktrace: |
        Handling order #42
        Traceback (most recent call last):
          File "/home/user/SWE-Agent-Skills/test_data/buggy_code.py", line 44, in <module>
            main()
          File "/home/user/SWE-Agent-Skills/test_data/buggy_code.py", line 40, in main
            controller.handle_order(order_id=42)
          File "/home/user/SWE-Agent-Skills/test_data/buggy_code.py", line 35, in handle_order
            self.user_service.process_user()
          File "/home/user/SWE-Agent-Skills/test_data/buggy_code.py", line 25, in process_user
            username = self.get_username()
          File "/home/user/SWE-Agent-Skills/test_data/buggy_code.py", line 19, in get_username
            return self.current_user.name
                   ^^^^^^^^^^^^^^^^^^^^^^
        AttributeError: 'NoneType' object has no attribute 'name'
      source_path: "test_data/buggy_code.py"
    expected_output:
      file: "buggy_code.py"
      line: 19
      variable: "self.current_user"
      error_type: "AttributeError"
    acceptance:
      - "output.file == expected.file"
      - "abs(output.line - expected.line) <= 2"
      - "output.error_type == expected.error_type"
      - "expected.variable in output.variable or output.variable in expected.variable"
    tags: [happy_path, attributeerror]

  - id: TC-002
    name: "KeyError on missing dict key"
    input:
      stacktrace: |
        Traceback (most recent call last):
          File "app/routes.py", line 33, in handle_request
            user_id = request_data['user_id']
        KeyError: 'user_id'
      source_path: "app/"
    expected_output:
      file: "routes.py"
      line: 33
      error_type: "KeyError"
    acceptance:
      - "output.file == expected.file"
      - "abs(output.line - expected.line) <= 2"
      - "output.error_type == expected.error_type"
    tags: [happy_path, keyerror]

  - id: TC-003
    name: "TypeError in arithmetic operation"
    input:
      stacktrace: |
        Traceback (most recent call last):
          File "utils/calculator.py", line 8, in multiply
            return factor * multiplier
        TypeError: unsupported operand type(s) for *: 'NoneType' and 'int'
      source_path: "utils/"
    expected_output:
      file: "calculator.py"
      line: 8
      error_type: "TypeError"
    acceptance:
      - "output.file == expected.file"
      - "abs(output.line - expected.line) <= 2"
      - "output.error_type == expected.error_type"
    tags: [happy_path, typeerror]
---

## Goal
Pinpoint the exact location and cause of a Python exception, filtering out stdlib and third-party frames to focus on user-written code.

## 🚀 Instructions

1. Read the Python traceback from **bottom to top**. The LAST frame (closest to the exception line) is where the crash occurred.
2. Find the innermost frame that belongs to **user code** — ignore frames from `stdlib`, `site-packages`, or installed libraries. Look for frames whose path matches or is near `source_path`.
3. Extract from that frame:
   - `file`: the basename of the source file (e.g. `buggy_code.py`)
   - `line`: the integer line number
4. From the exception message (last line of traceback):
   - `error_type`: the exception class name (e.g. `"AttributeError"`, `"TypeError"`)
   - `variable`: the object/expression before the failing attribute access; check the `^^^` highlighting in Python 3.11+ tracebacks for the precise expression.
5. Return **ONLY** a JSON object with keys: `file`, `line`, `variable`, `error_type`.

## Examples

See `examples:` in the YAML frontmatter above.

## ⚠️ Common Mistakes

- Returning a stdlib frame instead of a user-code frame.
- Extracting the wrong variable — use the `^^^` indicator if present.
- Returning the module path instead of the basename for `file`.

## 🔗 Related Skills

- `suggest-python-fix` — takes the output of this skill to generate fix suggestions.
- `debug-python-error` — composite skill that chains this with `suggest-python-fix`.
