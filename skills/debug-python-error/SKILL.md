---
name: debug-python-error
description: Full pipeline to debug a Python exception — analyzes the stacktrace to find the root cause, then generates an actionable fix suggestion with code.
version: 1.0.0
category: SoftwareEngineering/Debugging
level: composite
tags: [python, debug, pipeline, composite, attributeerror]

# Execution order: analyze first, then suggest fix using analyze's output
sub_skills:
  - analyze-python-error    # step 1 → produces: file, line, variable, error_type
  - suggest-python-fix      # step 2 → uses: file, line, variable, error_type → produces: fix_suggestion, code_snippet

input:
  type: object
  required: [stacktrace, source_path]
  properties:
    stacktrace:
      type: string
      description: Full Python exception traceback
    source_path:
      type: string
      description: Path to the Python source file with the bug

output:
  type: object
  properties:
    file:
      type: string
    line:
      type: integer
    variable:
      type: string
    error_type:
      type: string
    fix_suggestion:
      type: string
    code_snippet:
      type: string

constraints:
  host:
    os: [linux, darwin, windows]
  resources:
    memory: "512MB"
    timeout: "120s"
  safety:
    fs_access: read-only
    requires_approval: false
---

## Instructions

Composite skill — SkillExecutor handles the pipeline:
1. `analyze-python-error` receives {stacktrace, source_path} → outputs {file, line, variable, error_type}
2. `suggest-python-fix` receives {file, line, variable, error_type} (from step 1) → outputs {fix_suggestion, code_snippet}
3. All outputs are merged into the final response.
