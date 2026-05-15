"""
Skill Reporting Service  (port 8004)
======================================
Aggregated statistics and reporting across all skills, evaluations, and test runs.
Also provides live registry health information.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select

from shared.config import get_skills_dir
from shared.db import get_session, init_db
from shared.models import Skill as SkillORM, SkillDocReview, SkillEvaluation, SkillTestRun
from services.skill_management.skill_library.registry.registry import SkillRegistry

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


app = FastAPI(title="Skill Reporting Service", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _summarize_grouped(rows) -> dict:
    return {key: count for key, count in rows}


# ─────────────────────────────────────────────────────────────────────────────
# Skills Summary
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/reports/skills/summary")
def skills_summary() -> dict:
    """Aggregate skill counts by category, level, and tags."""
    with get_session() as session:
        total = session.scalar(select(func.count()).select_from(SkillORM)) or 0
        by_category = session.execute(
            select(SkillORM.category, func.count()).group_by(SkillORM.category)
        ).all()
        by_level = session.execute(
            select(SkillORM.level, func.count()).group_by(SkillORM.level)
        ).all()
        by_version = session.execute(
            select(SkillORM.version, func.count()).group_by(SkillORM.version)
        ).all()

        # Tag frequency
        all_skills = session.execute(select(SkillORM)).scalars().all()
        tag_freq: dict[str, int] = {}
        for s in all_skills:
            for tag in (s.tags or []):
                tag_freq[tag] = tag_freq.get(tag, 0) + 1

        return {
            "total": total,
            "by_category": _summarize_grouped(by_category),
            "by_level": _summarize_grouped(by_level),
            "by_version": _summarize_grouped(by_version),
            "top_tags": dict(
                sorted(tag_freq.items(), key=lambda x: x[1], reverse=True)[:10]
            ),
        }


@app.get("/reports/skills/{skill_id}/history")
def skill_history(skill_id: str) -> dict:
    """Full history of evaluations, doc reviews, and test runs for a skill."""
    with get_session() as session:
        skill = session.get(SkillORM, skill_id)
        if not skill:
            raise HTTPException(status_code=404, detail="Skill not found")

        evals = session.execute(
            select(SkillEvaluation)
            .where(SkillEvaluation.skill_id == skill_id)
            .order_by(SkillEvaluation.created_at.desc())
            .limit(20)
        ).scalars().all()

        doc_reviews = session.execute(
            select(SkillDocReview)
            .where(SkillDocReview.skill_id == skill_id)
            .order_by(SkillDocReview.created_at.desc())
            .limit(20)
        ).scalars().all()

        test_runs = session.execute(
            select(SkillTestRun)
            .where(SkillTestRun.skill_id == skill_id)
            .order_by(SkillTestRun.created_at.desc())
            .limit(20)
        ).scalars().all()

        return {
            "skill": {
                "id": skill.id,
                "name": skill.name,
                "category": skill.category,
                "level": skill.level,
                "version": skill.version,
            },
            "evaluations": [
                {
                    "id": e.id,
                    "pass_rate": e.pass_rate,
                    "passed_cases": e.passed_cases,
                    "total_cases": e.total_cases,
                    "accuracy": e.accuracy,
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
            "test_runs": [
                {
                    "id": r.id,
                    "llm": r.llm,
                    "passed": r.passed,
                    "created_at": r.created_at.isoformat(),
                }
                for r in test_runs
            ],
        }


# ─────────────────────────────────────────────────────────────────────────────
# Evaluation Summary
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/reports/evaluations/summary")
def evaluations_summary() -> dict:
    """Aggregate stats across all evaluation runs."""
    with get_session() as session:
        total = session.scalar(select(func.count()).select_from(SkillEvaluation)) or 0
        all_evals = session.execute(select(SkillEvaluation)).scalars().all()

        if not all_evals:
            return {
                "total": 0, "avg_pass_rate": 0.0,
                "avg_accuracy": 0.0, "mock_runs": 0, "real_runs": 0,
            }

        avg_pass_rate = sum(e.pass_rate for e in all_evals) / len(all_evals)
        avg_accuracy = sum(e.accuracy for e in all_evals) / len(all_evals)
        mock_runs = sum(1 for e in all_evals if e.mock_mode)

        return {
            "total": total,
            "avg_pass_rate": round(avg_pass_rate, 1),
            "avg_accuracy": round(avg_accuracy, 1),
            "mock_runs": mock_runs,
            "real_runs": total - mock_runs,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Doc Review Summary
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/reports/doc-reviews/summary")
def doc_reviews_summary() -> dict:
    """Aggregate stats across all documentation review runs."""
    with get_session() as session:
        total = session.scalar(select(func.count()).select_from(SkillDocReview)) or 0
        passed = session.scalar(
            select(func.count()).select_from(SkillDocReview).where(SkillDocReview.passed.is_(True))
        ) or 0
        all_reviews = session.execute(select(SkillDocReview)).scalars().all()
        avg_score = (
            sum(r.doc_score for r in all_reviews) / len(all_reviews)
            if all_reviews else 0.0
        )
        return {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "avg_doc_score": round(avg_score, 1),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Test Run Summary
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/reports/tests/summary")
def tests_summary() -> dict:
    """Aggregate stats across all test run sessions."""
    with get_session() as session:
        total = session.scalar(select(func.count()).select_from(SkillTestRun)) or 0
        passed = session.scalar(
            select(func.count()).select_from(SkillTestRun).where(SkillTestRun.passed.is_(True))
        ) or 0
        by_llm = session.execute(
            select(SkillTestRun.llm, func.count()).group_by(SkillTestRun.llm)
        ).all()
        return {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": round(passed / total * 100, 1) if total else 0.0,
            "by_llm": _summarize_grouped(by_llm),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Registry Status
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/reports/registry/status")
def registry_status() -> dict:
    """Live registry health — loaded skills count, categories."""
    registry = get_registry()
    all_skills = registry.all_skills()
    categories: dict[str, int] = {}
    for s in all_skills:
        categories[s.category] = categories.get(s.category, 0) + 1

    return {
        "loaded_skills": len(registry),
        "skills_dir": str(SKILLS_DIR),
        "categories": categories,
        "levels": {
            "atomic": sum(1 for s in all_skills if s.level == "atomic"),
            "composite": sum(1 for s in all_skills if s.level == "composite"),
        },
        "skill_names": [s.name for s in all_skills],
    }


@app.get("/reports/dashboard")
def dashboard() -> dict:
    """Unified dashboard snapshot — all key metrics in one call."""
    with get_session() as session:
        skill_total = session.scalar(select(func.count()).select_from(SkillORM)) or 0
        eval_total = session.scalar(select(func.count()).select_from(SkillEvaluation)) or 0
        test_total = session.scalar(select(func.count()).select_from(SkillTestRun)) or 0
        doc_total = session.scalar(select(func.count()).select_from(SkillDocReview)) or 0
        test_passed = session.scalar(
            select(func.count()).select_from(SkillTestRun).where(SkillTestRun.passed.is_(True))
        ) or 0
        doc_passed = session.scalar(
            select(func.count()).select_from(SkillDocReview).where(SkillDocReview.passed.is_(True))
        ) or 0

        by_category = session.execute(
            select(SkillORM.category, func.count()).group_by(SkillORM.category)
        ).all()
        by_level = session.execute(
            select(SkillORM.level, func.count()).group_by(SkillORM.level)
        ).all()

        registry = get_registry()

        return {
            "skills": {"total": skill_total},
            "evaluations": {"total": eval_total},
            "test_runs": {
                "total": test_total,
                "passed": test_passed,
                "pass_rate": round(test_passed / test_total * 100, 1) if test_total else 0.0,
            },
            "doc_reviews": {
                "total": doc_total,
                "passed": doc_passed,
                "pass_rate": round(doc_passed / doc_total * 100, 1) if doc_total else 0.0,
            },
            "by_category": _summarize_grouped(by_category),
            "by_level": _summarize_grouped(by_level),
            "registry_loaded": len(registry),
        }
