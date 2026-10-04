"""Pydantic domain models for readable Markdown + YAML research records."""

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator


class Status(StrEnum):
    HYPOTHESIS = "hypothesis"
    CANDIDATE = "candidate"
    VALIDATED = "validated"
    REPORTED = "reported"
    EMBARGOED = "embargoed"
    DISCLOSED = "disclosed"
    PUBLIC = "public"
    REJECTED = "rejected"


class Origin(StrEnum):
    HUMAN = "human"
    AI = "ai"
    HYBRID = "hybrid"


class AIProvenance(BaseModel):
    model: str | None = None
    harness: str | None = None
    reasoning_mode: str | None = None


class Evidence(BaseModel):
    type: Annotated[str, Field(min_length=1)]
    path: str | None = None
    sha256: Annotated[str | None, Field(pattern=r"^[a-f0-9]{64}$")] = None
    line: Annotated[int | None, Field(ge=1)] = None
    note: str | None = None
    date_raw: str | None = None


class Change(BaseModel):
    before: Any = None
    after: Any = None


class HistoryEvent(BaseModel):
    id: Annotated[str, Field(min_length=1)]
    recorded_at: datetime
    event_type: Annotated[str, Field(min_length=1)]
    actual_at: datetime | None = None
    date_raw: str | None = None
    changes: dict[str, Change] = Field(default_factory=dict)
    note: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    corrects_event_id: str | None = None


class Record(BaseModel):
    id: Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+$")]
    created_at: datetime
    updated_at: datetime | None = None
    history: list[HistoryEvent] = Field(default_factory=list)

    @model_validator(mode="after")
    def history_is_consistent(self) -> "Record":
        seen = set()
        for event in self.history:
            if event.id in seen:
                raise ValueError("duplicate history event id")
            if event.corrects_event_id and event.corrects_event_id not in seen:
                raise ValueError("correction must reference an earlier history event")
            seen.add(event.id)
        return self


class Target(Record):
    kind: Literal["target"] = "target"
    name: str
    repository: HttpUrl | str
    language: str | None = None
    version: str | None = None
    commit: str | None = None
    research_status: str = "planned"
    notes: str | None = None


class Hypothesis(Record):
    kind: Literal["hypothesis"] = "hypothesis"
    target: str
    title: str
    origin: Origin
    status: Literal[Status.HYPOTHESIS] = Status.HYPOTHESIS
    security_boundary: str
    confidence: Annotated[float | None, Field(ge=0, le=1)] = None
    ai: AIProvenance | None = None

    @model_validator(mode="after")
    def provenance_matches_origin(self) -> "Hypothesis":
        if self.origin == Origin.HUMAN and self.ai is not None:
            raise ValueError("human hypotheses must not include AI provenance")
        return self


class Finding(Record):
    kind: Literal["finding"] = "finding"
    hypothesis: str
    target: str
    title: str
    origin: Origin
    status: Status
    security_boundary: str
    ai: AIProvenance | None = None


class PublicCase(Record):
    kind: Literal["public_case"] = "public_case"
    target: str
    title: str
    status: Literal[Status.DISCLOSED, Status.PUBLIC]
    disclosure_date: datetime
    cve: str | None = None
    ghsa: str | None = None


class Pattern(Record):
    kind: Literal["pattern"] = "pattern"
    title: str
    category: str
    cases: list[str] = []
    description: str


class ArmMetrics(BaseModel):
    name: str
    origin: Origin
    model: str | None = None
    hypotheses: Annotated[int, Field(ge=0)] = 0
    validated: Annotated[int, Field(ge=0)] = 0
    rejected: Annotated[int, Field(ge=0)] = 0
    unique: Annotated[int, Field(ge=0)] = 0
    time_hours: Annotated[float | None, Field(ge=0)] = None
    tokens: Annotated[int | None, Field(ge=0)] = None
    api_cost: Annotated[float | None, Field(ge=0)] = None

    @model_validator(mode="after")
    def counts_are_consistent(self) -> "ArmMetrics":
        if self.validated + self.rejected > self.hypotheses:
            raise ValueError("validated + rejected cannot exceed hypotheses")
        return self


class Experiment(Record):
    kind: Literal["experiment"] = "experiment"
    title: str
    target: str
    audit_scope: str
    time_budget_hours: Annotated[float, Field(gt=0)]
    arms: Annotated[list[ArmMetrics], Field(min_length=2)]
    overlap: Annotated[int, Field(ge=0)] = 0
    limitations: list[str] = []


class SubmissionStatus(StrEnum):
    UNKNOWN = "unknown"
    NOT_SUBMITTED = "not_submitted"
    SUBMITTED = "submitted"
    WITHDRAWN = "withdrawn"


class ProcessingStatus(StrEnum):
    UNKNOWN = "unknown"
    PENDING_REVIEW = "pending_review"
    TRIAGED = "triaged"
    ACCEPTED = "accepted"
    DUPLICATE = "duplicate"
    INFORMATIVE = "informative"
    REJECTED = "rejected"
    RESOLVED = "resolved"


class MaterialRef(BaseModel):
    path: Annotated[str, Field(min_length=1)]
    sha256: Annotated[str | None, Field(pattern=r"^[a-f0-9]{64}$")] = None


class Report(Record):
    kind: Literal["report"] = "report"
    schema_version: Literal[1] = 1
    project: Annotated[str, Field(min_length=1)]
    title: Annotated[str, Field(min_length=1)]
    channel: str | None = None
    external_id: str | None = None
    external_url: HttpUrl | None = None
    submission_status: SubmissionStatus = SubmissionStatus.UNKNOWN
    submission_evidence: list[Evidence] = Field(default_factory=list)
    submitted_at: datetime | None = None
    submitted_at_raw: str | None = None
    processing_status: ProcessingStatus = ProcessingStatus.UNKNOWN
    platform_status_raw: str | None = None
    local_status_raw: str | None = None
    status_evidence: list[Evidence] = Field(default_factory=list)
    status_at: datetime | None = None
    status_at_raw: str | None = None
    original_report: MaterialRef | None = None
    related_documents: list[MaterialRef] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    research_refs: list[str] = Field(default_factory=list)
    source_key: str | None = None
    import_fingerprint: Annotated[str | None, Field(pattern=r"^[a-f0-9]{64}$")] = None

    @model_validator(mode="after")
    def report_fields_are_consistent(self) -> "Report":
        if not self.project.strip() or not self.title.strip():
            raise ValueError("project and title must not be blank")
        if self.external_id and (
            not self.external_id.strip() or not self.channel or not self.channel.strip()
        ):
            raise ValueError("external identifier requires a channel")
        if self.submission_status == SubmissionStatus.SUBMITTED and not any(
            e.path or (e.note and e.note.strip()) for e in self.submission_evidence
        ):
            raise ValueError("submitted requires typed submission evidence")
        return self


class CaseMaterial(MaterialRef):
    role: str
    label: str


class RecordedRating(BaseModel):
    version: Literal["3.1", "4.0"]
    score: Annotated[float, Field(ge=0, le=10)]
    vector: str
    attribution: Literal["reporter", "reporter_alternative", "vendor"]
    source: Evidence

    @model_validator(mode="after")
    def version_matches_vector(self):
        if not self.vector.startswith(f"CVSS:{self.version}/"):
            raise ValueError("CVSS vector/version mismatch")
        return self


class CaseReference(BaseModel):
    identifier: str
    relationship: Literal["reference_only"] = "reference_only"
    source: Evidence


class CaseDetails(BaseModel):
    model_config = {"extra": "forbid"}
    project: Annotated[str, Field(min_length=1)]
    title: Annotated[str, Field(min_length=1)]
    purpose: Literal["own_research", "study"]
    source_key: Annotated[str, Field(min_length=1)]
    legacy_ids: list[str] = Field(default_factory=list)
    category: str
    cwe: list[Annotated[str, Field(pattern=r"^CWE-[0-9]+$")]] = Field(default_factory=list)
    ratings: list[RecordedRating] = Field(default_factory=list)
    assigned_identifiers: list[str] = Field(default_factory=list)
    reference_cases: list[CaseReference] = Field(default_factory=list)
    materials: Annotated[list[CaseMaterial], Field(min_length=1)]
    evidence: Annotated[list[Evidence], Field(min_length=1)]
    submission_status: SubmissionStatus = SubmissionStatus.UNKNOWN
    submission_basis: Literal["unknown", "user_instruction", "platform_receipt"] = "unknown"
    submission_note: str | None = None
    processing_status: ProcessingStatus = ProcessingStatus.UNKNOWN
    planned_channel: str | None = None
    planned_submission_date_raw: str | None = None
    external_report_id: str | None = None
    reported_versions: list[str] = Field(default_factory=list)
    summary: str
    learning_notes: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    verification_basis: Literal["existing_report_only"] = "existing_report_only"

    @model_validator(mode="after")
    def references_are_not_assignments(self):
        if self.submission_status == SubmissionStatus.SUBMITTED:
            if self.submission_basis == "unknown" or not self.submission_note:
                raise ValueError("submitted case requires explicit basis and note")
            if not any(e.type == self.submission_basis for e in self.evidence):
                raise ValueError("submitted case requires matching evidence")
        refs = {r.identifier for r in self.reference_cases}
        if refs.intersection(self.assigned_identifiers):
            raise ValueError("reference identifier cannot be assigned to this case")
        if not self.source_key.startswith("VA:"):
            raise ValueError("VA source_key must use the VA: namespace")
        if not any(m.role == "primary_report" for m in self.materials):
            raise ValueError("a primary report is required")
        return self


class VACase(CaseDetails, Record):
    kind: Literal["va_case"] = "va_case"
    schema_version: Literal[1] = 1
    id: Annotated[str, Field(pattern=r"^VA-[0-9]{4}-[0-9]{4,}$")]
    intake_sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
