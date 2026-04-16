---
name: analyze-python-error
description: Analyzes a Python exception stacktrace to pinpoint the exact file, line number, variable, and error type causing the crash.
version: 1.0.0
category: SoftwareEngineering/Debugging
level: atomic
tags: [python, stacktrace, debug, attributeerror, typeerror]

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
---

## Instructions

1. Read the Python traceback from bottom to top. The LAST frame (closest to the exception line) is where the crash occurred.
2. Find the innermost frame that belongs to user code (not stdlib, not site-packages, not installed libraries). Look for frames inside the provided source_path.
3. Extract from that frame: the filename (basename only), and the line number.
4. From the exception message (last line of traceback), identify:
   - `error_type`: the exception class name (e.g. "AttributeError", "TypeError")
   - `variable`: the object/expression being accessed that is None or invalid. For `AttributeError: 'NoneType' object has no attribute 'name'`, the variable is the object before `.name`; look at the highlighted code `^^^` to identify it precisely.
5. Return ONLY a JSON object with: file, line, variable, error_type.
