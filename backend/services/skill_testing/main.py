from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from services.skill_testing.state import AgentState
# Import app = workflow.compile() từ file pipeline của bạn

app = FastAPI(title="AG2 Orchestrator API")

class UserRequest(BaseModel):
    code: str
    stacktrace: str
    message: str

@app.post("/api/v1/agent/run")
async def run_agent_workflow(request: UserRequest):
    initial_state = AgentState(
        user_context={
            "code": request.code,
            "stacktrace": request.stacktrace,
            "message": request.message
        }
    )
    
    # Kích hoạt đồ thị LangGraph chạy ngầm thực tế
    try:
        final_state = await app_langgraph.ainvoke(initial_state)
        return {
            "status": "COMPLETED",
            "final_answer": final_state.get("final_answer"),
            "steps_taken": final_state.get("step_count"),
            "history": final_state.get("history") # Gửi lịch sử chạy để FE hiển thị logs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

