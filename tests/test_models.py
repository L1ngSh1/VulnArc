from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from vulnarc.lifecycle import require_transition
from vulnarc.models import Hypothesis, Origin, PublicCase, Status

NOW = datetime.now(UTC)


def test_schema_validation():
    record = Hypothesis(
        id="SYNTH-HYP-001",
        target="example-project",
        title="Synthetic",
        origin="human",
        created_at=NOW,
        security_boundary="member -> project",
    )
    assert record.status == Status.HYPOTHESIS


def test_malformed_metadata():
    with pytest.raises(ValidationError):
        Hypothesis(
            id="bad",
            target="x",
            title="x",
            origin="human",
            created_at="nope",
            security_boundary="x",
        )


def test_human_provenance_rejected():
    with pytest.raises(ValidationError):
        Hypothesis(
            id="SYNTH-HYP-001",
            target="x",
            title="x",
            origin=Origin.HUMAN,
            created_at=NOW,
            security_boundary="x",
            ai={"model": "example"},
        )


def test_valid_transitions():
    require_transition(Status.HYPOTHESIS, Status.CANDIDATE)
    require_transition(Status.CANDIDATE, Status.VALIDATED)
    require_transition(Status.CANDIDATE, Status.REJECTED)


def test_invalid_transitions():
    with pytest.raises(ValueError, match="hypothesis -> public"):
        require_transition(Status.HYPOTHESIS, Status.PUBLIC)
    with pytest.raises(ValueError, match="rejected -> validated"):
        require_transition(Status.REJECTED, Status.VALIDATED)


def test_public_case_safety_rule():
    with pytest.raises(ValidationError):
        PublicCase(
            id="SYNTH-CASE-001",
            target="x",
            title="x",
            status="embargoed",
            created_at=NOW,
            disclosure_date=NOW,
        )
