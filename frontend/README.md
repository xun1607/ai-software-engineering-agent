# Skill Library Frontend — Demo Interface

## Overview
This frontend demonstrates the AI Skill Library system with a real-time execution pipeline visualization.

## Current Demo: Python Error Analysis

The frontend is configured to demonstrate the **`analyze-python-error`** skill, which:
- Analyzes Python exception stacktraces
- Identifies the exact file, line number, and problematic variable
- Provides error type classification

### Quick Start

1. **Inject Real Stacktrace**
   - Click the "📥 Inject Stacktrace" button
   - This runs `test_data/buggy_code.py` which contains a real `AttributeError`
   - The stacktrace is automatically populated

2. **Run the Skill**
   - Click "▶ Run Skill"
   - Watch the execution pipeline in real-time:
     - 🔍 IDENTIFY: Recognizes the skill
     - ✅ VALIDATE: Checks input format
     - 🔒 CONSTRAINT: Verifies system requirements
     - 🤖 LLM CALL: Calls DeepSeek/Mock LLM
     - 📦 PARSE: Extracts structured output
     - 🎉 RESULT: Shows final output

3. **View Results**
   - File: `buggy_code.py`
   - Line: `19`
   - Variable: `self.current_user`
   - Error Type: `AttributeError`

## Manual Testing

To manually enter a Python stacktrace:
1. Clear the default stacktrace field
2. Paste your own Python exception traceback
3. Update the source_path if needed (or leave as `test_data/`)
4. Click "▶ Run Skill"

## API Endpoints Used

| Endpoint | Purpose |
|----------|---------|
| `/api/status` | Check API status & mock mode |
| `/api/skills` | List all available skills |
| `/api/search` | Search skills by keyword |
| `/api/run-test-code` | Execute test code to generate stacktrace |
| `/api/execute/stream` | Stream skill execution with real-time logs |

## Configuration

- **Mock Mode**: Set `MOCK_MODE=true` env var for offline demo (uses canned responses)
- **Live Mode**: Set `DEEPSEEK_API_KEY` for real LLM calls

## Features

✅ Real-time SSE streaming of execution steps  
✅ Search skills by keyword  
✅ View complete skill metadata (input/output schema, constraints)  
✅ Automatic stacktrace injection from test code  
✅ JSON output visualization  
✅ Step-by-step execution logs  

## Architecture

- **Frontend**: Pure JavaScript (no framework) + SSE streaming
- **Backend**: FastAPI with Python skill execution engine
- **Skills**: YAML-based metadata + LangChain/LLM integration

See `requirement.md` and `skill.md` for full project documentation.
