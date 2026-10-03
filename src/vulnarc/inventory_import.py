"""One-off converter for the 2026-10-01 inventory, never a generic import engine."""

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Annotated

import typer

from .history import event, now
from .models import Report
from .reports import Workspace, create_report, error, mapped_status, material, report_app
from .storage import digest, external_key, load_yaml, metadata_files

SCHEMA = "local-vulnarc-planning-v1 (NOT an official VulnArc import schema)"


def source_path(root: Path, raw: str) -> Path:
    path = (root / raw).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"source path escapes source root: {raw}")
    if not path.is_file():
        raise ValueError(f"missing source path: {raw}")
    return path


def local_id(entry: dict) -> str:
    project = entry["project"].removesuffix("-audit")
    suffix = entry.get("local_id") or entry["id"].rsplit(":", 1)[-1]
    return "RPT-" + re.sub(r"[^A-Z0-9]+", "-", f"{project}-{suffix}".upper()).strip("-")


def convert_entry(entry: dict, root: Path) -> dict:
    external = entry.get("external_report") or {}
    proofs = []
    for raw in entry.get("status_evidence", []):
        ref = material(source_path(root, raw["path"]))
        if raw.get("sha256") and ref["sha256"] != raw["sha256"]:
            raise ValueError(f"inventory evidence hash mismatch: {raw['path']}")
        proofs.append(
            {"type": "local_ledger", **ref, "line": raw.get("line"), "note": raw.get("note")}
        )
    events = entry.get("events_from_local_documents", [])
    stamp = now()
    fingerprint = digest(json.dumps(entry, sort_keys=True, ensure_ascii=False).encode())
    data = {
        "kind": "report",
        "schema_version": 1,
        "id": local_id(entry),
        "project": entry["project"],
        "title": entry["title"],
        "created_at": stamp,
        "updated_at": stamp,
        "channel": external.get("platform") or entry.get("channel_recorded_or_proposed"),
        "external_id": external.get("id"),
        "submission_status": "submitted",
        "submission_evidence": proofs,
        "submitted_at": None,
        "submitted_at_raw": entry.get("submitted_at_raw"),
        "processing_status": mapped_status(entry["proposed_status"]),
        "platform_status_raw": None,
        "local_status_raw": entry["proposed_status"],
        "status_evidence": proofs,
        "status_at": None,
        "status_at_raw": events[-1].get("date_raw") if events else None,
        "original_report": material(source_path(root, entry["canonical_document"])),
        "related_documents": [
            material(source_path(root, p)) for p in entry.get("related_documents", [])
        ],
        "missing_information": entry.get("missing_information", []) + ["平台原始反馈文字"],
        "notes": entry.get("notes", []) + ["状态来自本地 inventory；没有核验平台最新结果。"],
        "source_key": entry["id"],
        "import_fingerprint": fingerprint,
    }
    data["history"] = [event("registration", {}, note="从本地清单登记；不推断实际提交时间")]
    previous = "unknown"
    for raw in events:
        mapped = mapped_status(raw["event"])
        changes = {"local_event": {"before": None, "after": raw["event"]}}
        if mapped != "unknown":
            changes["processing_status"] = {"before": previous, "after": mapped}
            previous = mapped
        data["history"].append(
            event(
                "imported_feedback",
                changes,
                date_raw=raw.get("date_raw"),
                note=raw.get("note"),
                evidence=proofs,
            )
        )
    return Report.model_validate(data).model_dump(mode="json")


def preview_inventory(
    inventory: Path, workspace: Path, *, sample=False, limit=8, source_root: Path | None = None
) -> list[dict]:
    data = json.loads(inventory.read_text())
    if data.get("schema") != SCHEMA:
        raise ValueError("unsupported inventory schema")
    if limit < 1 or limit > 8:
        raise ValueError("一期预览 limit 必须在 1..8")
    root = (source_root or Path(data["source_root"])).resolve()
    selected = [e for e in data["records"] if e["filing_group"] == "local_submission_record"]
    if sample:
        statuses = [
            "closed_duplicate",
            "pending_program_review",
            "submitted_pending_platform_review",
        ]
        selected = [next(e for e in selected if e["proposed_status"] == s) for s in statuses]
    selected = selected[:limit]
    existing = [load_yaml(p) for p in metadata_files(workspace)]
    previews = []
    ids, keys, sources = set(), set(), set()
    for entry in selected:
        record = convert_entry(entry, root)
        action, message = "create", "将创建；保留原材料"
        source_match = [r for r in existing if r.get("source_key") == record["source_key"]]
        id_match = [r for r in existing if r.get("id") == record["id"]]
        ext_match = [
            r for r in existing if external_key(record) and external_key(r) == external_key(record)
        ]
        other_collision = any(
            r.get("source_key") != record["source_key"] for r in id_match + ext_match
        )
        if other_collision:
            action, message = "conflict", "ID 或外部编号已属于其他来源档案"
        elif (
            len(source_match) == 1
            and source_match[0].get("import_fingerprint") == record["import_fingerprint"]
        ):
            action, message = "skip", "相同来源键与清单内容已登记"
        elif source_match or id_match or ext_match:
            action, message = "conflict", "来源、ID 或外部编号冲突；须人工关联既有档案"
        key = external_key(record)
        if record["id"] in ids or (key and key in keys) or record["source_key"] in sources:
            action, message = "conflict", "清单内部 ID 或外部编号冲突"
        ids.add(record["id"])
        sources.add(record["source_key"])
        if key:
            keys.add(key)
        previews.append(
            {
                "action": action,
                "message": message,
                "source_key": record["source_key"],
                "record": record,
            }
        )
    return previews


def apply_preview(workspace: Path, previews: list[dict]) -> list[Path]:
    if any(p["action"] == "conflict" for p in previews):
        raise ValueError("inventory conflict; nothing applied")
    prepared = [deepcopy(p["record"]) for p in previews if p["action"] == "create"]
    # Preflight every prepared record/material before publishing the first record.
    for data in prepared:
        Report.model_validate(data)
        for ref in [
            data["original_report"],
            *data["related_documents"],
            *data["submission_evidence"],
        ]:
            if ref and ref.get("path"):
                path = Path(ref["path"])
                if not path.is_file() or digest(path.read_bytes()) != ref["sha256"]:
                    raise ValueError(f"source changed after preview: {ref['path']}")
    return [create_report(workspace, data) for data in prepared]


@report_app.command("import-inventory")
def import_inventory(
    inventory: Path,
    workspace: Workspace,
    apply: Annotated[bool, typer.Option("--apply")] = False,
    sample: Annotated[bool, typer.Option("--sample", help="预览三类样例")] = False,
    limit: Annotated[int, typer.Option(min=1, max=8)] = 8,
    source_root: Annotated[Path | None, typer.Option()] = None,
):
    try:
        previews = preview_inventory(
            inventory, workspace, sample=sample, limit=limit, source_root=source_root
        )
        typer.echo("apply" if apply else "dry-run：零写入")
        typer.echo(json.dumps(previews, ensure_ascii=False, indent=2))
        if any(p["action"] == "conflict" for p in previews):
            raise ValueError("inventory conflict")
        if apply:
            paths = apply_preview(workspace, previews)
            typer.echo(f"已创建 {len(paths)} 条；每条独立原子提交")
    except (ValueError, OSError, KeyError, StopIteration) as exc:
        error(exc)
