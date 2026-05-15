"""
Skill Evaluation Service  (port 8002)
=======================================
Two evaluation dimensions for a registered skill:
  1. Doc Review   → SkillDocReviewer (rule-based score against criteria XML)
  2. Test Eval    → SkillEvaluator   (runs SKILL.md test_cases via SkillExecutor)
  3. Both         → Combined report

Also preserves legacy format/content XSD validation endpoints.
"""
from __future__ import annotations

import json
import os
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from lxml import etree
from sqlalchemy import select

from shared.config import get_skills_dir
from shared.db import get_session, init_db
from shared.models import Skill as SkillORM, SkillDocReview, SkillEvaluation
from shared.schemas import (
    DocReviewRead,
    DocCriterionRead,
    EvaluationReportRead,
    FullEvaluationRead,
    SkillPayload,
    ValidationResponse,
    ValidationResult,
)
from services.skill_management.skill_library.eval.evaluator import SkillEvaluator
from services.skill_management.skill_library.management.doc_reviewer import SkillDocReviewer
from services.skill_management.skill_library.models.skill import Skill as SkillModel
from services.skill_management.skill_library.registry.registry import SkillRegistry
from shared.skill_markdown import SkillMarkdownError, parse_skill_markdown
from shared.skill_validation import validate_skill_format
from shared.skill_xml import skill_to_xml

SCHEMA_PATH = Path(__file__).parent / "schema" / "skill.xsd"
SCHEMA_CACHE: etree.XMLSchema | None = None
SCHEMA_UPDATE_TOKEN = os.getenv("SCHEMA_UPDATE_TOKEN", "").strip() or None

SKILLS_DIR: Path = get_skills_dir()
REGISTRY: SkillRegistry | None = None
DOC_REVIEWER = SkillDocReviewer()


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


app = FastAPI(title="Skill Evaluation Service", version="2.0.0", lifespan=lifespan)

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
    """Load full Skill dataclass from stored raw markdown."""
    return SkillModel.from_markdown(skill_orm.raw_content)


def _doc_review_to_schema(review, skill_id: str | None) -> DocReviewRead:
    return DocReviewRead(
        skill_id=skill_id,
        skill_name=review.skill_name,
        doc_score=review.total_score,
        max_score=review.max_score,
        passed=review.passed,
        threshold=review.threshold,
        criteria=[
            DocCriterionRead(
                id=c.id,
                layer=c.layer,
                description=c.description,
                points=c.points,
                passed=c.passed,
                note=c.note,
            )
            for c in review.criteria
        ],
    )


def _store_doc_review(skill_id: str, review) -> None:
    with get_session() as session:
        record = SkillDocReview(
            skill_id=skill_id,
            doc_score=review.total_score,
            max_score=review.max_score,
            passed=review.passed,
            threshold=review.threshold,
            criteria_json=json.dumps(
                [{"id": c.id, "layer": c.layer, "passed": c.passed, "points": c.points}
                 for c in review.criteria]
            ),
        )
        session.add(record)


def _store_evaluation(skill_id: str, report) -> None:
    report_dict = report.to_dict()
    with get_session() as session:
        record = SkillEvaluation(
            skill_id=skill_id,
            total_cases=report.total,
            passed_cases=report.passed,
            pass_rate=report.pass_rate,
            accuracy=report.accuracy,
            latency_p50=report.latency_p50,
            latency_p95=report.latency_p95,
            avg_tokens=report.avg_tokens,
            mock_mode=report.mock_mode,
            report_json=json.dumps(report_dict),
            format_valid=True,
            content_valid=report.passed > 0,
            errors="",
        )
        session.add(record)


def _report_to_schema(report, skill_id: str | None) -> EvaluationReportRead:
    d = report.to_dict()
    return EvaluationReportRead(
        skill_id=skill_id,
        skill_name=d["skill_name"],
        skill_version=d["skill_version"],
        mock_mode=d["mock_mode"],
        summary=d["summary"],
        metrics=d["metrics"],
        metric_checks=d.get("metric_checks", {}),
        test_results=d.get("test_results", []),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Evaluation Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/evaluate/{skill_id}/doc", response_model=DocReviewRead)
def evaluate_doc(skill_id: str) -> DocReviewRead:
    """Run SkillDocReviewer on a registered skill — scores documentation quality."""
    with get_session() as session:
        skill_orm = _get_skill_orm(skill_id, session)
        skill_model = _load_skill_model(skill_orm)

    review = DOC_REVIEWER.review(skill_model)
    _store_doc_review(skill_id, review)
    return _doc_review_to_schema(review, skill_id)


@app.post("/evaluate/{skill_id}/run", response_model=EvaluationReportRead)
def evaluate_run(
    skill_id: str,
    mock_mode: bool = Body(default=True, embed=True),
) -> EvaluationReportRead:
    """Run SkillEvaluator (test_cases from SKILL.md) against a registered skill."""
    with get_session() as session:
        skill_orm = _get_skill_orm(skill_id, session)
        skill_model = _load_skill_model(skill_orm)

    if not skill_model.test_cases:
        raise HTTPException(
            status_code=422,
            detail=f"Skill '{skill_model.name}' has no test_cases defined in SKILL.md",
        )

    registry = get_registry()
    evaluator = SkillEvaluator(registry=registry, mock_mode=mock_mode, verbose=False)
    report = evaluator.evaluate(skill_model)
    _store_evaluation(skill_id, report)
    return _report_to_schema(report, skill_id)


@app.post("/evaluate/{skill_id}/all", response_model=FullEvaluationRead)
def evaluate_all(
    skill_id: str,
    mock_mode: bool = Body(default=True, embed=True),
) -> FullEvaluationRead:
    """Run both doc review and test case evaluation."""
    with get_session() as session:
        skill_orm = _get_skill_orm(skill_id, session)
        skill_model = _load_skill_model(skill_orm)

    # Doc review
    doc_review = DOC_REVIEWER.review(skill_model)
    _store_doc_review(skill_id, doc_review)
    doc_schema = _doc_review_to_schema(doc_review, skill_id)

    # Test evaluation (optional — skill may not have test_cases)
    eval_schema = None
    if skill_model.test_cases:
        registry = get_registry()
        evaluator = SkillEvaluator(registry=registry, mock_mode=mock_mode, verbose=False)
        report = evaluator.evaluate(skill_model)
        _store_evaluation(skill_id, report)
        eval_schema = _report_to_schema(report, skill_id)

    return FullEvaluationRead(doc_review=doc_schema, evaluation=eval_schema)


@app.get("/evaluate/{skill_id}/history")
def evaluation_history(skill_id: str) -> dict:
    """Get recent evaluation history for a skill."""
    with get_session() as session:
        evals = session.execute(
            select(SkillEvaluation)
            .where(SkillEvaluation.skill_id == skill_id)
            .order_by(SkillEvaluation.created_at.desc())
            .limit(10)
        ).scalars().all()
        doc_reviews = session.execute(
            select(SkillDocReview)
            .where(SkillDocReview.skill_id == skill_id)
            .order_by(SkillDocReview.created_at.desc())
            .limit(10)
        ).scalars().all()
        return {
            "evaluations": [
                {
                    "id": e.id,
                    "pass_rate": e.pass_rate,
                    "passed_cases": e.passed_cases,
                    "total_cases": e.total_cases,
                    "mock_mode": e.mock_mode,
                    "created_at": e.created_at.isoformat(),
                }
                for e in evals
            ],
            "doc_reviews": [
                {
                    "id": d.id,
                    "doc_score": d.doc_score,
                    "max_score": d.max_score,
                    "passed": d.passed,
                    "created_at": d.created_at.isoformat(),
                }
                for d in doc_reviews
            ],
        }


@app.get("/evaluate/{skill_id}/xml", response_class=PlainTextResponse)
def get_skill_xml(skill_id: str) -> str:
    """Get the XML representation of a registered skill."""
    with get_session() as session:
        skill_orm = _get_skill_orm(skill_id, session)
        metadata, instruction = parse_skill_markdown(skill_orm.raw_content)
    return skill_to_xml(metadata, instruction)


@app.get("/evaluate/{skill_id}/validate", response_model=ValidationResult)
def validate_registered_skill(skill_id: str) -> ValidationResult:
    """Validate a registered skill against format rules and XML Schema (XSD)."""
    with get_session() as session:
        skill_orm = _get_skill_orm(skill_id, session)
        metadata, instruction = parse_skill_markdown(skill_orm.raw_content)
    
    # Format validation
    format_errors = validate_skill_format(metadata, instruction)
    format_result = ValidationResponse(valid=not format_errors, errors=format_errors)
    
    # Content (XSD) validation
    schema = load_schema()
    xml_payload = skill_to_xml(metadata, instruction)
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    doc = etree.fromstring(xml_payload.encode("utf-8"), parser)
    
    content_errors: list[str] = []
    if not schema.validate(doc):
        content_errors = [str(err) for err in schema.error_log]
    
    content_result = ValidationResponse(valid=not content_errors, errors=content_errors)
    
    return ValidationResult(format=format_result, content=content_result)


@app.get("/criteria", response_class=PlainTextResponse)
def get_criteria() -> str:
    """Get the documentation review criteria XML."""
    if not DOC_REVIEWER.CRITERIA_FILE.exists():
        raise HTTPException(status_code=404, detail="Criteria file not found")
    return DOC_REVIEWER.CRITERIA_FILE.read_text(encoding="utf-8")


@app.post("/criteria")
def update_criteria(xml_content: str = Body(..., embed=True)) -> dict:
    """Update the documentation review criteria XML."""
    try:
        # Basic XML validation
        etree.fromstring(xml_content.encode("utf-8"))
        DOC_REVIEWER.CRITERIA_FILE.write_text(xml_content, encoding="utf-8")
        return {"status": "success", "message": "Criteria updated"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid XML: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# Legacy format/content validation (XSD-based)
# ─────────────────────────────────────────────────────────────────────────────

def load_schema() -> etree.XMLSchema:
    global SCHEMA_CACHE
    if SCHEMA_CACHE is None:
        if not SCHEMA_PATH.exists():
            raise HTTPException(status_code=503, detail="XSD schema not found")
        schema_text = SCHEMA_PATH.read_text(encoding="utf-8")
        parser = etree.XMLParser(resolve_entities=False, no_network=True)
        schema_doc = etree.fromstring(schema_text.encode("utf-8"), parser)
        SCHEMA_CACHE = etree.XMLSchema(schema_doc)
    return SCHEMA_CACHE


def resolve_skill_payload(skill: SkillPayload | None, skill_markdown: str | None) -> tuple[dict, str]:
    if skill_markdown:
        metadata, instruction = parse_skill_markdown(skill_markdown)
        return metadata, instruction
    if skill:
        return skill.metadata.model_dump(), skill.instruction
    raise HTTPException(status_code=400, detail="Provide skill or skill_markdown")


@app.post("/validate/format", response_model=ValidationResponse)
def validate_format(
    skill: SkillPayload | None = Body(default=None),
    skill_markdown: str | None = Body(default=None),
) -> ValidationResponse:
    try:
        metadata, instruction = resolve_skill_payload(skill, skill_markdown)
    except SkillMarkdownError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    errors = validate_skill_format(metadata, instruction)
    return ValidationResponse(valid=not errors, errors=errors)


@app.post("/validate/content", response_model=ValidationResponse)
def validate_content_endpoint(
    skill: SkillPayload | None = Body(default=None),
    skill_markdown: str | None = Body(default=None),
) -> ValidationResponse:
    try:
        metadata, instruction = resolve_skill_payload(skill, skill_markdown)
    except SkillMarkdownError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    schema = load_schema()
    xml_payload = skill_to_xml(metadata, instruction)
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    doc = etree.fromstring(xml_payload.encode("utf-8"), parser)
    errors: list[str] = []
    if not schema.validate(doc):
        errors = [str(err) for err in schema.error_log]
    return ValidationResponse(valid=not errors, errors=errors)


@app.post("/validate/all", response_model=ValidationResult)
def validate_all(
    skill: SkillPayload | None = Body(default=None),
    skill_markdown: str | None = Body(default=None),
) -> ValidationResult:
    try:
        metadata, instruction = resolve_skill_payload(skill, skill_markdown)
    except SkillMarkdownError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    format_errors = validate_skill_format(metadata, instruction)
    format_result = ValidationResponse(valid=not format_errors, errors=format_errors)
    schema = load_schema()
    xml_payload = skill_to_xml(metadata, instruction)
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    doc = etree.fromstring(xml_payload.encode("utf-8"), parser)
    content_errors = [str(err) for err in schema.error_log] if not schema.validate(doc) else []
    content_result = ValidationResponse(valid=not content_errors, errors=content_errors)
    return ValidationResult(format=format_result, content=content_result)
