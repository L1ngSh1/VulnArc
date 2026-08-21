"""Filesystem storage: YAML metadata remains the source of truth."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from .models import Experiment, Finding, Hypothesis, Pattern, PublicCase, Target

MODELS = {
    "target": Target,
    "hypothesis": Hypothesis,
    "finding": Finding,
    "public_case": PublicCase,
    "experiment": Experiment,
    "pattern": Pattern,
}


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("metadata root must be a mapping")
    return data


def dump_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def metadata_files(workspace: Path) -> list[Path]:
    ignored = {".git", ".venv", ".codex-transaction"}
    return sorted(p for p in workspace.rglob("metadata.yaml") if not ignored.intersection(p.parts))


def parse_record(path: Path):
    data = load_yaml(path)
    kind = data.get("kind")
    if kind not in MODELS:
        raise ValueError(f"unknown record kind: {kind!r}")
    return MODELS[kind].model_validate(data)


def validate_workspace(workspace: Path) -> list[str]:
    errors: list[str] = []
    seen: dict[str, Path] = {}
    for path in metadata_files(workspace):
        try:
            record = parse_record(path)
            if record.id in seen:
                errors.append(f"{path}: duplicate id {record.id} (also {seen[record.id]})")
            seen[record.id] = path
            if "cases/public" in path.as_posix() and not isinstance(record, PublicCase):
                errors.append(f"{path}: cases/public accepts public_case records only")
        except (ValueError, ValidationError, yaml.YAMLError) as exc:
            errors.append(f"{path}: {exc}")
    for record_id, path in seen.items():
        try:
            record = parse_record(path)
            references = []
            if isinstance(record, Finding):
                references.append(record.hypothesis)
            if isinstance(record, Pattern):
                references.extend(record.cases)
            for reference in references:
                if reference != record_id and reference not in seen:
                    errors.append(f"{path}: unresolved reference {reference}")
        except (ValueError, ValidationError, yaml.YAMLError):
            continue
    return errors


def find_record(workspace: Path, record_id: str) -> tuple[Path, dict[str, Any]]:
    for path in metadata_files(workspace):
        data = load_yaml(path)
        if data.get("id") == record_id:
            return path, data
    raise FileNotFoundError(f"record not found: {record_id}")
