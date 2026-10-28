"""Versioned integration contracts. Student responses are deliberately absent."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "gmf.assessment.modules/1.1"


def uid(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


class AnswerStatus(StrEnum):
    VERIFIED = "Verified"
    PROVISIONAL = "Provisional"
    DISPUTED = "Disputed"
    UNRESOLVED = "Unresolved"


class ExternalLink(Contract):
    course_id: str | None = None
    unit_id: str | None = None
    topic_id: str | None = None
    exercise_id: str | None = None
    confirmed: bool = False
    registry_version: str | None = None


class SourceSpan(Contract):
    page: int = Field(ge=1)
    page_label: str | None = None
    bbox: tuple[float, float, float, float]
    extraction: Literal["native", "ocr", "docling"] = "native"

    @model_validator(mode="after")
    def valid_box(self):
        x0, y0, x1, y1 = self.bbox
        if min(self.bbox) < 0 or x1 <= x0 or y1 <= y0:
            raise ValueError("bbox must be positive, ordered PDF points (top-left origin)")
        return self


class Option(Contract):
    label: str = Field(pattern=r"^[A-H]$")
    text: str = Field(min_length=1)


class QuestionAsset(Contract):
    asset_id: str
    document_id: str
    kind: Literal["original_pdf", "page_image", "question_crop", "layout_json", "docling_json"]
    relative_path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    media_type: str
    page: int | None = None
    bbox: tuple[float, float, float, float] | None = None
    exam_safe: bool = False
    solver_usable: bool = False


class Question(Contract):
    schema_version: str = SCHEMA_VERSION
    question_id: str
    scope: Literal["bank", "exam_private"]
    owner_id: str
    document_id: str
    source_number: str
    publication: Literal["draft", "approved"] = "draft"
    current_version_id: str
    created_at: str = Field(default_factory=now)


class QuestionVersion(Contract):
    schema_version: str = SCHEMA_VERSION
    version_id: str
    question_id: str
    source_section: str | None = None
    version: int = Field(ge=1)
    stem: str = Field(min_length=1)
    options: list[Option] = Field(min_length=2, max_length=8)
    spans: list[SourceSpan] = Field(min_length=1)
    asset_ids: list[str] = Field(default_factory=list)
    formula_fragments: list[str] = Field(default_factory=list)
    raw_text: str
    text_fingerprint: str
    fingerprint: str
    warnings: list[str] = Field(default_factory=list)
    has_visual: bool = False
    external: ExternalLink = Field(default_factory=ExternalLink)
    created_at: str = Field(default_factory=now)

    @model_validator(mode="after")
    def unique_options(self):
        labels = [o.label for o in self.options]
        if len(set(labels)) != len(labels):
            raise ValueError("duplicate option labels")
        return self


class AnswerEvidence(Contract):
    evidence_id: str = Field(default_factory=lambda: uid("ev"))
    version_id: str
    kind: Literal["source_key", "trusted_match", "model_solution", "math_check", "independent_review", "human_review", "engine_error", "dependency_invalidated"]
    producer: str
    details: dict[str, Any]
    created_at: str = Field(default_factory=now)


class AnswerKey(Contract):
    answer_key_id: str = Field(default_factory=lambda: uid("ans"))
    version_id: str
    revision: int = Field(ge=1)
    label: str | None = Field(default=None, pattern=r"^[A-H]$")
    status: AnswerStatus
    evidence_ids: list[str]
    explanation: str = ""
    supersedes: str | None = None
    confirmed_by: str | None = None
    created_at: str = Field(default_factory=now)

    @model_validator(mode="after")
    def verified_has_auditor(self):
        if self.status == AnswerStatus.VERIFIED and (not self.confirmed_by or not self.label):
            raise ValueError("Verified requires a label and accountable confirmation")
        return self


class QuestionClassification(Contract):
    classification_id: str = Field(default_factory=lambda: uid("cls"))
    version_id: str
    course_hint: str = "AP Physics C: Mechanics"
    unit_hints: list[str] = Field(default_factory=list)
    topic_hints: list[str] = Field(default_factory=list)
    knowledge: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    methods: list[str] = Field(default_factory=list)
    structures: list[str] = Field(default_factory=list)
    difficulty: Literal["unknown", "introductory", "intermediate", "advanced"] = "unknown"
    confidence: float = Field(default=0, ge=0, le=1)
    producer: str = "rules-v1"
    reviewed: bool = False
    external: ExternalLink = Field(default_factory=ExternalLink)


class QuestionRelation(Contract):
    relation_id: str = Field(default_factory=lambda: uid("rel"))
    from_version_id: str
    to_version_id: str
    kind: Literal["exact_duplicate", "possible_duplicate", "consolidation", "transfer"]
    score: float = Field(ge=0, le=1)
    reasons: list[str]


class ImportBatch(Contract):
    batch_id: str
    scope: Literal["bank", "exam_private"]
    owner_id: str
    status: Literal["queued", "running", "completed", "partial", "failed", "interrupted"]
    files: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=now)


class SourceRecord(Contract):
    document_id: str
    sha256: str
    filename: str
    scope: Literal["bank", "exam_private"]
    owner_id: str
    source_url: str | None = None
    license_name: str | None = None
    reuse_confirmed: bool = False
    page_count: int
    warnings: list[str] = Field(default_factory=list)


class ParsedQuestion(Contract):
    number: str
    version: QuestionVersion
    source_answers: list[str] = Field(default_factory=list)


class ParseResult(Contract):
    source: SourceRecord
    assets: list[QuestionAsset]
    questions: list[ParsedQuestion]
    warnings: list[str]
    diagnostics: dict[str, Any] = Field(default_factory=dict)


class MathCheck(Contract):
    kind: Literal["equivalence", "derivative", "integral", "solve"] = "equivalence"
    lhs: str = Field(max_length=240)
    rhs: str = Field(max_length=240)
    variable: str = Field(default="x", pattern=r"^[A-Za-z][A-Za-z0-9]{0,15}$")


class ModelSolution(Contract):
    label: str | None = Field(default=None, pattern=r"^[A-H]$")
    explanation: str = Field(max_length=12000)
    confidence: float = Field(ge=0, le=1)
    assumptions: list[str] = Field(default_factory=list)
    checks: list[MathCheck] = Field(default_factory=list, max_length=6)


class SolverInput(Contract):
    version_id: str
    source_number: str | None = None
    stem: str
    options: list[Option]
    images: list[str] = Field(default_factory=list)  # local validated crops only; never original answer pages
    warnings: list[str] = Field(default_factory=list)

