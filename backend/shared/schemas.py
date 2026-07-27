from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ─────────────────────────────────────────────────────────────────────────────
# Skill Schemas
# ─────────────────────────────────────────────────────────────────────────────

SkillLevel = Literal["atomic", "composite"]

class SkillMetadata(BaseModel):
    """Core metadata + arbitrary extra fields from YAML frontmatter."""
    model_config = ConfigDict(extra="allow")

    name: str = Field(..., min_length=1, max_length=255)
    version: str = Field(..., min_length=1, max_length=50)
    level: str = Field(..., min_length=1, max_length=15)
    category: str = Field(..., min_length=1, max_length=100)
    tags: List[str] = Field(default_factory=list)


class SkillPayload(BaseModel):
    """Used for creating or importing a skill (JSON + instruction body)."""
    metadata: SkillMetadata
    instruction: str = Field(..., min_length=1)


class SkillUpdate(BaseModel):
    metadata: Optional[Dict[str, Any]] = None
    instruction: Optional[str] = None
    full_markdown: Optional[str] = None
    raw_content: Optional[str] = None




class SkillSummary(BaseModel):
    """Lightweight skill listing (no instruction body)."""
    id: str
    name: str
    version: str
    level: str
    category: str
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime


class SkillRead(SkillSummary):
    """Full skill representation returned by the API."""
    raw_content: str
    full_markdown: str


class SkillList(BaseModel):
    items: List[SkillSummary]
    total: int = 0


class SkillSearchResult(BaseModel):
    skill: SkillSummary
    score: float


class SkillSearchResponse(BaseModel):
    query: str
    results: List[SkillSearchResult]


# ─────────────────────────────────────────────────────────────────────────────
# Validation Schemas (used by skill_evaluation)
# ─────────────────────────────────────────────────────────────────────────────

class ValidationResponse(BaseModel):
    valid: bool
    errors: List[str] = Field(default_factory=list)


class ValidationResult(BaseModel):
    format: ValidationResponse
    content: ValidationResponse


# ─────────────────────────────────────────────────────────────────────────────
# Doc Review Schemas
# ─────────────────────────────────────────────────────────────────────────────

class DocCriterionRead(BaseModel):
    id: str
    layer: str
    description: str
    points: int
    passed: bool
    note: str


class DocReviewRead(BaseModel):
    skill_id: Optional[str] = None
    skill_name: str
    doc_score: int
    max_score: int
    passed: bool
    threshold: int
    criteria: List[DocCriterionRead]


# ─────────────────────────────────────────────────────────────────────────────
# Evaluation Schemas (SkillEvaluator test-case results)
# ─────────────────────────────────────────────────────────────────────────────

class EvaluationReportRead(BaseModel):
    """Mirrors EvaluationReport.to_dict() structure."""
    skill_id: Optional[str] = None
    skill_name: str
    skill_version: str
    mock_mode: bool
    summary: Dict[str, Any]
    metrics: Dict[str, Any]
    metric_checks: Dict[str, bool]
    test_results: List[Dict[str, Any]]


class FullEvaluationRead(BaseModel):
    doc_review: Optional[DocReviewRead] = None
    evaluation: Optional[EvaluationReportRead] = None


# ─────────────────────────────────────────────────────────────────────────────
# Test Run Schemas (skill_testing)
# ─────────────────────────────────────────────────────────────────────────────

class TestCase(BaseModel):
    input: str
    expected_contains: Optional[str] = None


class TestRunRequest(BaseModel):
    llm: str = Field(..., min_length=1)
    skill: SkillPayload
    testcases: List[TestCase]
    skill_id: Optional[str] = None


class TestCaseResult(BaseModel):
    input: str
    output: str
    expected_contains: Optional[str]
    passed: bool


class TestRunResponse(BaseModel):
    llm: str
    passed: bool
    results: List[TestCaseResult]

# ─────────────────────────────────────────────────────────────────────────────
# Execution Schemas (SkillExecutor run results)
# ─────────────────────────────────────────────────────────────────────────────

class SkillExecutionRequest(BaseModel):
    input: Dict[str, Any]
    mock_mode: bool = True
    api_key: Optional[str] = None



class SkillExecutionResponse(BaseModel):
    skill_id: str
    skill_name: str
    output: Dict[str, Any]
    telemetry: Optional[Dict[str, Any]] = None


class SkillToolDefinition(BaseModel):
    """Schema for LangChain/LangGraph tool compatibility."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    skill_id: str
