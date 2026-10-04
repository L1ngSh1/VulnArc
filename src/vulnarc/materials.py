"""Shared local material checks; record-specific rules remain explicit, without CLI imports."""

import hashlib
from pathlib import Path
from typing import Literal

from .models import CaseDetails


def resolve_material(path: str, workspace: Path | None = None) -> Path:
    material = Path(path)
    if not material.is_absolute() and workspace is not None:
        material = workspace / material
    return material


def material_problem(
    path: str | None,
    sha256: str | None,
    line: int | None = None,
    *,
    workspace: Path | None = None,
    absolute_required: bool = False,
    hash_required: bool = False,
) -> Literal["required", "missing", "hash", "line"] | None:
    """Check in the original order: required fields, path, hash, then line bounds."""
    if not path or (hash_required and not sha256):
        return "required"
    material = resolve_material(path, workspace)
    if (absolute_required and not Path(path).is_absolute()) or not material.is_file():
        return "missing"
    if sha256 and hashlib.sha256(material.read_bytes()).hexdigest() != sha256:
        return "hash"
    if line and line > len(material.read_text(encoding="utf-8").splitlines()):
        return "line"
    return None


def verify_case_materials(record: CaseDetails) -> None:
    proofs = list(record.evidence)
    proofs += [r.source for r in record.ratings]
    proofs += [r.source for r in record.reference_cases]
    for ref in [*record.materials, *proofs]:
        line = getattr(ref, "line", None)
        problem = material_problem(
            ref.path, ref.sha256, line, absolute_required=True, hash_required=True
        )
        if problem == "required":
            raise ValueError("case material/evidence needs a path and SHA-256")
        if problem == "missing":
            raise ValueError(f"missing absolute source path: {ref.path}")
        if problem == "hash":
            raise ValueError(f"source hash changed: {ref.path}")
        if problem == "line":
            raise ValueError(f"source line out of range: {ref.path}:{line}")
