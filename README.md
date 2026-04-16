# Universal Skill Library for AI Agents

A robust, framework-agnostic skill library designed for AI Agents in Software Engineering. It supports atomic and composite skills with structured metadata, input validation, and real-time execution logging.

## Features
- **Skill Registry**: TF-IDF based search for discovering relevant skills.
- **Skill Executor**: Handles the full lifecycle: validation → constraint checking → execution (Atomic/Composite).
- **Composite Skills**: Orchestrate multiple sub-skills with state propagation and cycle detection.
- **Framework Agnostic**: Includes adapters for LangChain (StructuredTools).
- **Real-time UI**: A modern dashboard to monitor skill execution steps and LLM responses.

## Getting Started

### 1. Prerequisites
- Python 3.10+
- DeepSeek API Key (for live LLM features)

### 2. Setup
Clone the repository and install dependencies:
```bash
git clone https://github.com/xun1607/ai-software-engineering-agent.git
cd ai-software-engineering-agent
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file in the root directory and add your DeepSeek API key:
```env
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

## Running the Project

### Test Real LLM Integration
To verify the composite skill pipeline with the real DeepSeek API:
```bash
python3 test_real_llm.py
```
This script generates a real Python stacktrace from `test_data/buggy_code.py` and runs the `debug-python-error` skill.

### Run Web UI (Demo)
By default, the UI runs in Mock Mode to save tokens. You can launch it with:
```bash
MOCK_MODE=true python3 -m uvicorn api:app --host 0.0.0.0 --port 8000
```
Then open [http://localhost:8000](http://localhost:8000) in your browser.

- To use **Real DeepSeek LLM** in the UI:
  ```bash
  MOCK_MODE=false python3 -m uvicorn api:app --host 0.0.0.0 --port 8000
  ```

## Project Structure
- `/skills`: Definitions of atomic and composite skills in `SKILL.md` (Markdown + YAML).
- `/skill_library`: Core engine (Registry, Executor, Validator, Constraints).
- `/frontend`: Web dashboard for skill execution.
- `api.py`: FastAPI backend with SSE streaming.
- `main.py`: CLI-based demo runner.
