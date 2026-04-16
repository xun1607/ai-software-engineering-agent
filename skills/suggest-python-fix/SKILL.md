---
name: suggest-python-fix
description: Suggests a concrete Python fix for an exception given the file, line, variable, and error type.
version: 1.0.0
category: SoftwareEngineering/Debugging
level: atomic
tags: [python, fix, attributeerror, patch, refactoring]

input:
  type: object
  required: [file, line, variable, error_type]
  properties:
    file:
      type: string
      description: Python source filename with the error
    line:
      type: integer
      description: Line number where the exception occurs
    variable:
      type: string
      description: The variable or expression that is None or invalid
    error_type:
      type: string
      description: The Python exception class (e.g. AttributeError, TypeError)

output:
  type: object
  properties:
    fix_suggestion:
      type: string
      description: Clear explanation of the root cause and the recommended fix strategy
    code_snippet:
      type: string
      description: Python code snippet (10-20 lines) demonstrating the fix

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

1. Based on the file, line number, variable, and error type, reason about the root cause.
2. For `AttributeError: 'NoneType' object has no attribute ...`:
   - The variable was never initialized or was set to None
   - Fix options (choose most appropriate): guard with `if variable is not None`, raise early with `assert variable is not None, "message"`, initialize in `__init__`, or use dependency injection
3. For `TypeError`:
   - Check wrong type passed; add type check or use `isinstance()`
4. For `KeyError` / `IndexError`:
   - Use `.get(key, default)` for dicts, or check `if key in dict` first
5. Write a `fix_suggestion` explaining: what went wrong, why, and how to fix it (2-4 sentences).
6. Write a `code_snippet` in Python showing the corrected version of the relevant method/block.
7. Return ONLY a JSON object with fix_suggestion and code_snippet.
