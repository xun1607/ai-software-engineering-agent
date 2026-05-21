import os
import json
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI

from orchestrator_module.orchestrator import OrchestratorGraph
from planner_module.planner import PlannerModule
from skill_selector_module.selector import ContextBasedSkillSelector
from executor_module.executor import LLMSkillExecutor

app = FastAPI(title="AI Software Engineering Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
planner = PlannerModule(client=client)
selector = ContextBasedSkillSelector(client=client, skill_registry_url="http://localhost:8001")
executor = LLMSkillExecutor(client=client)

orchestrator = OrchestratorGraph(
    planner_module=planner, 
    skill_selector=selector,
    executor_module=executor
)
agent_app = orchestrator.compile()

@app.post("/api/v1/chat/stream")
async def stream_agent_chat(request: Request):
    """
    Endpoint Endpoint xử lý Streaming SSE gửi toàn bộ tiến trình chạy Node về cho FE hiển thị
    """
    body = await request.json()
    user_message = body.get("message", "")
    
    # Thiết lập State khởi tạo cho LangGraph
    initial_state = {
        "user_goal": user_message,
        "chat_history": "",
        "execution_plan": [],
        "current_step_index": 0,
        "accumulated_context": {},
        "latest_error_feedback": None,
        "current_retry_count": 0,
        "extracted_arguments": {}
    }

    async def event_generator():
        try:
            for output in agent_app.stream(initial_state):
                for node_name, state_update in output.items():
                    payload = {
                        "node": node_name.upper(),
                        "current_step_index": state_update.get("current_step_index", 0),
                        "selected_skill": state_update.get("current_selected_skill_name"),
                        "latest_output": state_update.get("latest_step_output", {}).get("result"),
                        "final_response": state_update.get("final_response")
                    }
                    
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.1)
                    
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")