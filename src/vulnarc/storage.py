"""Local YAML storage with exclusive creation, optimistic updates and guarded recovery."""

import fcntl
import hashlib
import json
import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml
from pydantic import ValidationError

from .models import Experiment, Finding, Hypothesis, Pattern, PublicCase, Report, Target, VACase

MODELS = {
    "target": Target,
    "hypothesis": Hypothesis,
    "finding": Finding,
    "public_case": PublicCase,
    "experiment": Experiment,
    "pattern": Pattern,
    "report": Report,
    "va_case": VACase,
}
TOOL_DIR = ".vulnarc"
IGNORED = {".git", ".venv", ".codex-transaction", TOOL_DIR}


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def load_yaml(path: Path) -> dict[str, Any]:
    return decode_yaml(path.read_bytes())


def decode_yaml(content: bytes) -> dict[str, Any]:
    data = yaml.safe_load(content)
    if not isinstance(data, dict):
        raise ValueError("metadata root must be a mapping")
    return data


def yaml_bytes(data: dict[str, Any]) -> bytes:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True).encode("utf-8")


def atomic_write(path: Path, content: bytes) -> None:
    """Prepare a same-directory temporary file; failure never truncates the destination."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".metadata-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def dump_yaml(path: Path, data: dict[str, Any]) -> None:
    """Atomic low-level serialization; CLI writes use create_record/update_record."""
    atomic_write(path, yaml_bytes(data))


def contained(workspace: Path, path: Path) -> Path:
    root = workspace.resolve()
    absolute = path.absolute()
    try:
        relative = absolute.relative_to(workspace.absolute())
    except ValueError:
        try:
            relative = absolute.relative_to(root)
        except ValueError as exc:
            raise ValueError("path escapes workspace") from exc
    current = root
    for part in relative.parts:
        if part in {"..", "."}:
            raise ValueError("path escapes workspace")
        current /= part
        if current.is_symlink():
            raise ValueError(f"symlink is not a writable record path: {current}")
    if not current.resolve().is_relative_to(root):
        raise ValueError("path escapes workspace")
    return current


@contextmanager
def workspace_lock(workspace: Path):
    workspace = workspace.resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    tools = contained(workspace, workspace / TOOL_DIR)
    tools.mkdir(exist_ok=True)
    lock = contained(workspace, tools / "write.lock")
    with lock.open("a+b") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def metadata_files(workspace: Path) -> list[Path]:
    return sorted(
        p
        for p in workspace.rglob("metadata.yaml")
        if not IGNORED.intersection(p.relative_to(workspace).parts)
    )


def validate_data(data: dict[str, Any]):
    kind = data.get("kind")
    if kind not in MODELS:
        raise ValueError(f"unknown record kind: {kind!r}")
    return MODELS[kind].model_validate(data)


def parse_record(path: Path):
    return validate_data(load_yaml(path))


def next_id(workspace: Path, prefix: str, target: str) -> str:
    import re

    if prefix == "VA":
        if not re.fullmatch(r"[0-9]{4}", target):
            raise ValueError("VA year must be four digits")
        ledger = contained(workspace, workspace / TOOL_DIR / "va-sequence.json")
        values = json.loads(ledger.read_text()) if ledger.exists() else {}
        stem = f"VA-{target}-"
        used = [
            int(load_yaml(p)["id"][len(stem) :])
            for p in metadata_files(workspace)
            if re.fullmatch(re.escape(stem) + r"[0-9]{4,}", str(load_yaml(p).get("id", "")))
        ]
        number = max([values.get(target, 0), *used]) + 1
        values[target] = number
        # Reservations survive a failed write/deletion; gaps are allowed, reuse is not.
        atomic_write(ledger, (json.dumps(values, sort_keys=True) + "\n").encode())
        return f"{stem}{number:04d}"
    component = re.sub(r"[^A-Z0-9]+", "-", target.upper()).strip("-") or "LOCAL"
    stem = f"{prefix}-{component}-"
    used = []
    for path in metadata_files(workspace):
        value = load_yaml(path).get("id", "")
        if value.startswith(stem) and value[len(stem) :].isdigit():
            used.append(int(value[len(stem) :]))
    return f"{stem}{max(used, default=0) + 1:03d}"


def external_key(data: dict[str, Any]) -> tuple[str, str] | None:
    if data.get("kind") == "report" and data.get("channel") and data.get("external_id"):
        return data["channel"].strip().casefold(), data["external_id"].strip().casefold()
    return None


def check_unique(workspace: Path, data: dict[str, Any], exclude: Path | None = None) -> None:
    for path in metadata_files(workspace):
        if exclude is not None and path.resolve() == exclude.resolve():
            continue
        old = load_yaml(path)
        if old.get("id") == data["id"]:
            raise ValueError(f"duplicate id {data['id']}; existing record: {path}")
        if external_key(data) and external_key(data) == external_key(old):
            raise ValueError(f"duplicate external identifier; link existing report {old['id']}")
        if data.get("source_key") and data.get("source_key") == old.get("source_key"):
            raise ValueError(f"duplicate source key; existing report {old['id']}")


def create_record(
    workspace: Path,
    folder: str,
    data: dict[str, Any],
    bodies: dict[str, str],
    *,
    prefix: str | None = None,
    target: str = "LOCAL",
    body_factory=None,
) -> Path:
    workspace = workspace.resolve()
    data = dict(data)
    # Explicit IDs and invalid fields are rejected before preparing any formal directory.
    if data.get("id") is not None:
        validate_data(data)
    with workspace_lock(workspace):
        if data.get("id") is None:
            data["id"] = next_id(workspace, prefix or "REC", target)
        validate_data(data)
        check_unique(workspace, data)
        directory = contained(workspace, workspace / folder / data["id"])
        if directory.exists():
            raise ValueError(f"record directory already exists: {directory}")
        if body_factory is not None:
            bodies = body_factory(data)
        staging = contained(workspace, workspace / TOOL_DIR / "staging")
        staging.mkdir(exist_ok=True)
        temporary = Path(tempfile.mkdtemp(dir=staging))
        try:
            for name, text in bodies.items():
                if Path(name).name != name or name == "metadata.yaml":
                    raise ValueError("body filename must be a simple non-metadata filename")
                (temporary / name).write_text(text, encoding="utf-8")
            (temporary / "metadata.yaml").write_bytes(yaml_bytes(data))
            directory.parent.mkdir(parents=True, exist_ok=True)
            os.rename(temporary, directory)
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)
        return directory


def find_record(workspace: Path, record_id: str) -> tuple[Path, dict[str, Any]]:
    matches = []
    for path in metadata_files(workspace):
        data = load_yaml(path)
        if data.get("id") == record_id:
            matches.append((path, data))
    if len(matches) > 1:
        raise ValueError(f"duplicate id {record_id}; repair ambiguity before updating")
    if not matches:
        raise FileNotFoundError(f"record not found: {record_id}")
    return matches[0]


def read_for_update(workspace: Path, record_id: str) -> tuple[Path, dict[str, Any], str]:
    path, _ = find_record(workspace, record_id)
    path = contained(workspace, path)
    content = path.read_bytes()
    data = decode_yaml(content)
    if data.get("id") != record_id:
        raise ValueError("external edit conflict: record id changed during read")
    return path, data, digest(content)


def _replace_with_backup(workspace: Path, path: Path, content: bytes, fingerprint: str) -> Path:
    current = path.read_bytes()
    if digest(current) != fingerprint:
        raise ValueError("external edit conflict: metadata changed since it was read")
    backup = contained(workspace, workspace / TOOL_DIR / "backups" / uuid4().hex)
    backup.mkdir(parents=True)
    (backup / "before.bin").write_bytes(current)
    manifest = {
        "path": str(path.relative_to(workspace)),
        "before": digest(current),
        "after": digest(content),
    }
    (backup / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    if digest(path.read_bytes()) != fingerprint:
        raise ValueError("external edit conflict: metadata changed during write preparation")
    atomic_write(path, content)
    return backup


def update_record(workspace: Path, path: Path, data: dict[str, Any], fingerprint: str) -> Path:
    path = contained(workspace, path)
    workspace = workspace.resolve()
    validate_data(data)
    with workspace_lock(workspace):
        old = load_yaml(path)
        if old.get("id") != data["id"]:
            raise ValueError("record id is immutable")
        old_history = old.get("history", [])
        if data.get("history", [])[: len(old_history)] != old_history:
            raise ValueError("history is append-only; add a correction event")
        check_unique(workspace, data, exclude=path)
        return _replace_with_backup(workspace, path, yaml_bytes(data), fingerprint)


def restore_backup(workspace: Path, backup_id: str) -> Path:
    workspace = workspace.resolve()
    if len(backup_id) != 32 or any(c not in "0123456789abcdef" for c in backup_id):
        raise ValueError("invalid backup id")
    with workspace_lock(workspace):
        backup = contained(workspace, workspace / TOOL_DIR / "backups" / backup_id)
        manifest = json.loads(contained(workspace, backup / "manifest.json").read_text())
        path = contained(workspace, workspace / manifest["path"])
        content = contained(workspace, backup / "before.bin").read_bytes()
        if digest(content) != manifest["before"]:
            raise ValueError("backup hash mismatch")
        if digest(path.read_bytes()) != manifest["after"]:
            raise ValueError("current version differs from this write; recovery aborted")
        restored = decode_yaml(content)
        validate_data(restored)
        check_unique(workspace, restored, exclude=path)
        _replace_with_backup(workspace, path, content, manifest["after"])
        return path


def validate_workspace(workspace: Path) -> list[str]:
    errors: list[str] = []
    seen: dict[str, Path] = {}
    external_seen = {}
    sources_seen = {}
    for path in metadata_files(workspace):
        try:
            contained(workspace, path)
            record = parse_record(path)
            if record.id in seen:
                errors.append(f"{path}: duplicate id {record.id} (also {seen[record.id]})")
            seen[record.id] = path
            if isinstance(record, VACase):
                from .va import verify_materials

                verify_materials(record)
                for name in ("case.md", "materials.md", "timeline.md", "learning.md"):
                    if not (path.parent / name).is_file():
                        errors.append(f"{path}: missing case document {name}")
                if record.source_key in sources_seen:
                    errors.append(f"{path}: duplicate VA source key")
                sources_seen[record.source_key] = path
            if isinstance(record, Report):
                key = external_key(load_yaml(path))
                if key and key in external_seen:
                    errors.append(
                        f"{path}: duplicate external identifier (also {external_seen[key]})"
                    )
                if key:
                    external_seen[key] = path
                if record.source_key and record.source_key in sources_seen:
                    errors.append(f"{path}: duplicate source key")
                if record.source_key:
                    sources_seen[record.source_key] = path
                materials = list(record.related_documents)
                if record.original_report:
                    materials.append(record.original_report)
                for ref in materials:
                    material = Path(ref.path)
                    if not material.is_absolute():
                        material = workspace / material
                    if not material.is_file():
                        errors.append(f"{path}: missing material {ref.path}")
                    elif ref.sha256 and digest(material.read_bytes()) != ref.sha256:
                        errors.append(f"{path}: hash mismatch for {ref.path}")
                for evidence in (
                    record.submission_evidence
                    + record.status_evidence
                    + [e for event in record.history for e in event.evidence]
                ):
                    if evidence.path:
                        material = Path(evidence.path)
                        if not material.is_absolute():
                            material = workspace / material
                        if not material.is_file():
                            errors.append(f"{path}: missing material {evidence.path}")
                        elif evidence.sha256 and digest(material.read_bytes()) != evidence.sha256:
                            errors.append(f"{path}: hash mismatch for {evidence.path}")
                        elif evidence.line and evidence.line > len(
                            material.read_text().splitlines()
                        ):
                            errors.append(f"{path}: evidence line out of range {evidence.path}")
            if path.relative_to(workspace).parts[:2] == ("cases", "public") and not isinstance(
                record, PublicCase
            ):
                errors.append(f"{path}: cases/public accepts public_case records only")
        except (ValueError, ValidationError, yaml.YAMLError, OSError) as exc:
            errors.append(f"{path}: {exc}")
    for record_id, path in seen.items():
        try:
            record = parse_record(path)
            references = []
            if isinstance(record, Finding):
                references.append(record.hypothesis)
            if isinstance(record, Report):
                references.extend(record.research_refs)
            if isinstance(record, Pattern):
                references.extend(record.cases)
            for reference in references:
                if reference != record_id and reference not in seen:
                    errors.append(f"{path}: unresolved reference {reference}")
        except (ValueError, ValidationError, yaml.YAMLError, OSError):
            continue
    return errors
