"""Pydantic domain models for readable Markdown + YAML research records."""

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

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


class Record(BaseModel):
    id: Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+$")]
    created_at: datetime


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
