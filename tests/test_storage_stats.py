from pathlib import Path

import yaml

from vulnarc.statistics import calculate
from vulnarc.storage import validate_workspace

NOW = "2026-01-01T00:00:00Z"


def put(root: Path, folder: str, data: dict):
    path = root / folder / "metadata.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


def test_public_directory_rejects_non_case(tmp_path):
    put(
        tmp_path,
        "cases/public/bad",
        {
            "kind": "hypothesis",
            "id": "SYNTH-HYP-001",
            "target": "x",
            "title": "x",
            "origin": "human",
            "status": "hypothesis",
            "created_at": NOW,
            "security_boundary": "x",
        },
    )
    assert "cases/public accepts" in validate_workspace(tmp_path)[0]


def test_unresolved_finding_reference(tmp_path):
    put(
        tmp_path,
        "records/a",
        {
            "kind": "finding",
            "id": "SYNTH-FIND-001",
            "hypothesis": "SYNTH-HYP-404",
            "target": "x",
            "title": "synthetic",
            "origin": "human",
            "status": "candidate",
            "security_boundary": "a -> b",
            "created_at": NOW,
        },
    )
    assert "unresolved reference SYNTH-HYP-404" in validate_workspace(tmp_path)[0]


def test_stats_and_provenance_aggregation(tmp_path):
    base = {
        "kind": "finding",
        "target": "x",
        "security_boundary": "a -> b",
        "created_at": NOW,
        "hypothesis": "SYNTH-HYP-000",
        "title": "synthetic",
    }
    put(
        tmp_path,
        "records/a",
        base | {"id": "SYNTH-FIND-001", "origin": "human", "status": "validated"},
    )
    put(
        tmp_path,
        "records/b",
        base
        | {
            "id": "SYNTH-FIND-002",
            "origin": "ai",
            "status": "rejected",
            "ai": {"model": "fictional-model"},
        },
    )
    result = calculate(tmp_path)
    assert result["hypotheses"] == 2
    assert result["validated"] == 1 and result["rejected"] == 1
    assert result["origins"] == {"human": 1, "ai": 1}
    assert result["rates"]["human"]["validation_rate"] == 1
    assert result["rates"]["ai"]["rejection_rate"] == 1
