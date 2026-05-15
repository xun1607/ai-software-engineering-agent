"""
Skill Testing Service  (port 8003)
====================================
Run test cases for registered skills using SkillExecutor (mock mode).

Endpoints:
  POST /tests/run/{skill_id}     — run all SKILL.md test_cases (mock mode)
  POST /tests/run-custom         — run custom test cases from payload
  GET  /tests/{skill_id}/results — list historical test run results
"""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import select

from services.skill_testing.agent import run_agent_chat

from shared.config import get_skills_dir
from shared.db import get_session, init_db
from shared.models import Skill as SkillORM, SkillTestRun
from shared.schemas import TestCase, TestRunRequest, TestRunResponse, TestCaseResult
from services.skill_management.skill_library.execution.executor import SkillExecutor
from services.skill_management.skill_library.models.skill import Skill as SkillModel
from services.skill_management.skill_library.registry.registry import SkillRegistry
from .orchestrator import orchestrate_task, TaskRequest

SKILLS_DIR: Path = get_skills_dir()
REGISTRY: SkillRegistry | None = None


def get_registry() -> SkillRegistry:
    global REGISTRY
    if REGISTRY is None:
        REGISTRY = SkillRegistry(SKILLS_DIR)
        reload_registry()
    return REGISTRY


def reload_registry() -> int:
    global REGISTRY
    if REGISTRY is None:
        REGISTRY = SkillRegistry(SKILLS_DIR)
    
    with get_session() as session:
        skills = session.execute(select(SkillORM)).scalars().all()
        count = REGISTRY.load_from_markdowns([s.raw_content for s in skills])
    return count


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    get_registry()
    yield


app = FastAPI(title="Skill Testing Service", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_skill_orm(skill_id: str, session) -> SkillORM:
    skill = session.get(SkillORM, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill


def _load_skill_model(skill_orm: SkillORM) -> SkillModel:
    return SkillModel.from_markdown(skill_orm.raw_content)


def _store_run(skill_id: str | None, llm: str, response: TestRunResponse) -> None:
    with get_session() as session:
        record = SkillTestRun(
            skill_id=skill_id,
            llm=llm,
            passed=response.passed,
            results=json.dumps(
                [r.model_dump() for r in response.results], ensure_ascii=False
            ),
        )
        session.add(record)


class SkillTestRunParams(BaseModel):
    mock_mode: bool = True
    test_case_override: Optional[List[Dict[str, Any]]] = None

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: str = "deepseek-chat"
    api_key: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/tests/chat")
def chat_with_agent(req: ChatRequest):
    """
    Chat with a LangGraph agent that can invoke available skills.
    """
    try:
        messages_dict = [{"role": m.role, "content": m.content} for m in req.messages]
        result_messages = run_agent_chat(
            messages_dict=messages_dict,
            model_name=req.model,
            api_key=req.api_key
        )
        return {"messages": result_messages}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/tests/run/{skill_id}", response_model=TestRunResponse)
def run_skill_tests(skill_id: str, params: SkillTestRunParams) -> TestRunResponse:
    """
    Run all test_cases defined in a skill's SKILL.md using SkillExecutor.
    mock_mode=True by default — uses mock LLM (no API key required).
    """
    with get_session() as session:
        skill_orm = _get_skill_orm(skill_id, session)
        skill_model = _load_skill_model(skill_orm)

    if not skill_model.test_cases:
        raise HTTPException(
            status_code=422,
            detail=f"Skill '{skill_model.name}' has no test_cases in SKILL.md",
        )

    registry = get_registry()
    executor = SkillExecutor(
        registry=registry,
        mock_mode=params.mock_mode,
        log_callback=None,
    )

    results: List[TestCaseResult] = []
    overall_passed = True

    for tc in skill_model.test_cases:
        try:
            output = executor.run(skill_model, dict(tc.input))
            # For simple string check: check if output json contains expected values
            case_passed = True
            output_str = json.dumps(output)
            result_input = json.dumps(tc.input)
        except Exception as exc:
            output_str = f"ERROR: {exc}"
            result_input = json.dumps(tc.input)
            case_passed = False

        overall_passed = overall_passed and case_passed
        results.append(
            TestCaseResult(
                input=result_input,
                output=output_str,
                expected_contains=None,
                passed=case_passed,
            )
        )

    response = TestRunResponse(llm="mock" if params.mock_mode else "real", passed=overall_passed, results=results)
    _store_run(skill_id, response.llm, response)
    return response


@app.post("/tests/run-custom", response_model=TestRunResponse)
def run_custom_tests(payload: TestRunRequest) -> TestRunResponse:
    """
    Run custom test cases (legacy: simple string-contains check against mock LLM output).
    """
    registry = get_registry()
    executor = SkillExecutor(registry=registry, mock_mode=True, log_callback=None)

    import re
    # Load skill model in-memory from payload (write temp file)
    import tempfile, os
    meta = payload.skill.metadata
    instruction = payload.skill.instruction
    frontmatter = {
        "name": meta.name,
        "description": meta.description,
        "version": meta.version,
        "category": meta.category,
        "level": meta.level,
        "tags": meta.tags,
    }
    import yaml
    yaml_str = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True)
    md_content = f"---\n{yaml_str}---\n\n## 🚀 Instructions\n\n{instruction}\n"

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", encoding="utf-8", delete=False
    ) as tmp:
        tmp.write(md_content)
        tmp_path = Path(tmp.name)

    try:
        skill_model = SkillModel.from_md_file(tmp_path)
    finally:
        os.unlink(tmp_path)

    results: List[TestCaseResult] = []
    overall_passed = True

    for tc in payload.testcases:
        try:
            output = executor.run(skill_model, {"input": tc.input})
            output_str = json.dumps(output)
            if tc.expected_contains:
                case_passed = tc.expected_contains in output_str
            else:
                case_passed = True
        except Exception as exc:
            output_str = f"ERROR: {exc}"
            case_passed = False

        overall_passed = overall_passed and case_passed
        results.append(
            TestCaseResult(
                input=tc.input,
                output=output_str,
                expected_contains=tc.expected_contains,
                passed=case_passed,
            )
        )

    response = TestRunResponse(llm=payload.llm, passed=overall_passed, results=results)
    _store_run(payload.skill_id, payload.llm, response)
    return response


@app.get("/tests/{skill_id}/results")
def get_test_results(
    skill_id: str,
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    """List historical test run results for a skill."""
    with get_session() as session:
        runs = session.execute(
            select(SkillTestRun)
            .where(SkillTestRun.skill_id == skill_id)
            .order_by(SkillTestRun.created_at.desc())
            .limit(limit)
        ).scalars().all()
        return {
            "skill_id": skill_id,
            "total": len(runs),
            "runs": [
                {
                    "id": r.id,
                    "llm": r.llm,
                    "passed": r.passed,
                    "results": json.loads(r.results),
                    "created_at": r.created_at.isoformat(),
                }
                for r in runs
            ],
        }


@app.post("/orchestrate")
async def orchestrate_endpoint(request: TaskRequest):
    """
    Orchestrate a task using LangGraph workflow with LLM planning and execution.
    """
    return await orchestrate_task(request)
