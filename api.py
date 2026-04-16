"""
FastAPI backend — exposes SSE streaming endpoints so the frontend
can watch skill execution in real-time.
"""
import json
import os
import sys
import asyncio
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent))

from skill_library.core.registry import SkillRegistry
from skill_library.core.executor import SkillExecutor, LogEvent

# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(title="Skill Library API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Singleton registry + executor ──────────────────────────────────────────
SKILLS_DIR = Path(__file__).parent / "skills"
registry = SkillRegistry(SKILLS_DIR)
registry.load_all()

MOCK_MODE = os.environ.get("MOCK_MODE", "true").lower() in ("1", "true", "yes")
executor = SkillExecutor(
    registry=registry,
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    mock_mode=MOCK_MODE,
    log_callback=None,   # will be overridden per-request
)


# ─────────────────────────────────────────────────────────────────────────────
# Request / Response models
# ─────────────────────────────────────────────────────────────────────────────
class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


class ExecuteRequest(BaseModel):
    skill_name: str
    input_data: dict


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/api/skills")
def list_skills():
    """Return all skills in the library."""
    return [s.to_dict() for s in registry.all_skills()]


@app.get("/api/skills/{name}")
def get_skill(name: str):
    skill = registry.get(name)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")
    return skill.to_dict()


@app.post("/api/search")
def search_skills(req: SearchRequest):
    results = registry.search(req.query, top_k=req.top_k)
    return [
        {"skill": skill.to_dict(), "score": round(score, 4)}
        for skill, score in results
    ]


@app.post("/api/execute/stream")
async def execute_stream(req: ExecuteRequest):
    """
    SSE endpoint: streams LogEvents as `data: <json>` lines so the frontend
    can render each step as it happens.
    """
    skill = registry.get(req.skill_name)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{req.skill_name}' not found")

    # Queue to pass events from sync executor → async generator
    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_event_loop()

    def log_callback(event: LogEvent):
        loop.call_soon_threadsafe(queue.put_nowait, event.to_dict())

    async def event_generator() -> AsyncGenerator[str, None]:
        # Send identify_skill event first
        yield _sse({
            "step": "identify_skill",
            "status": "success",
            "skill_name": skill.name,
            "message": f"Skill '{skill.name}' found (level={skill.level})",
            "data": {"sub_skills": skill.sub_skills, "level": skill.level},
            "timestamp": __import__("time").time(),
        })

        # Run executor in a thread so we don't block the event loop
        import concurrent.futures
        local_executor = SkillExecutor(
            registry=registry,
            api_key=os.environ.get("DEEPSEEK_API_KEY"),
            mock_mode=MOCK_MODE,
            log_callback=log_callback,
        )

        result_holder = {}
        error_holder = {}

        def run_skill():
            try:
                result_holder["output"] = local_executor.run(skill, req.input_data)
            except Exception as exc:
                error_holder["error"] = str(exc)
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)  # sentinel

        thread_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        loop.run_in_executor(thread_executor, run_skill)

        # Stream events as they arrive
        while True:
            item = await queue.get()
            if item is None:   # sentinel → done
                break
            yield _sse(item)

        # Final result event
        if "output" in result_holder:
            yield _sse({
                "step": "result",
                "status": "success",
                "message": "Skill execution completed",
                "skill_name": skill.name,
                "data": result_holder["output"],
                "timestamp": __import__("time").time(),
            })
        else:
            yield _sse({
                "step": "result",
                "status": "error",
                "message": error_holder.get("error", "Unknown error"),
                "skill_name": skill.name,
                "data": None,
                "timestamp": __import__("time").time(),
            })

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/status")
def status():
    return {
        "skills_loaded": len(registry),
        "mock_mode": MOCK_MODE,
        "skills_dir": str(SKILLS_DIR),
    }


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


# ─── Serve frontend ──────────────────────────────────────────────────────────
frontend_dir = Path(__file__).parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
