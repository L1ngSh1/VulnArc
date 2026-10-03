"""Existing-report registration, independent of research lifecycle commands."""

from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer

from .history import append_change, event, now
from .models import ProcessingStatus, Report, SubmissionStatus
from .storage import (
    create_record,
    digest,
    find_record,
    metadata_files,
    parse_record,
    read_for_update,
    update_record,
)
from .template_loader import template_text

report_app = typer.Typer(help="登记已有报告、查看清单和补记反馈。", no_args_is_help=True)
Workspace = Annotated[Path, typer.Option("--workspace", "-w", help="显式指定外部登记工作区")]

STATUS_MAP = {
    "pending program review": "pending_review",
    "pending_program_review": "pending_review",
    "engineering_review": "pending_review",
    "转工程验证": "pending_review",
    "under_triage": "pending_review",
    "submitted_pending_platform_review": "pending_review",
    "closed_duplicate": "duplicate",
    "closed_informative": "informative",
    **{status.value: status.value for status in ProcessingStatus},
}


def mapped_status(raw: str) -> str:
    return STATUS_MAP.get(raw.strip().casefold(), "unknown")


def material(path: Path) -> dict:
    path = path.resolve()
    if not path.is_file():
        raise ValueError(f"missing material {path}")
    return {"path": str(path), "sha256": digest(path.read_bytes())}


def evidence_value(evidence_type, note, path) -> list[dict]:
    if not (note or path):
        return []
    if not evidence_type:
        raise ValueError("依据必须同时提供 --evidence-type")
    result = {"type": evidence_type, "note": note}
    if path:
        result.update(material(path))
    return [result]


def missing_fields(record: Report) -> list[str]:
    missing = list(record.missing_information)
    fields = {
        "channel": "渠道",
        "original_report": "原报告路径",
        "submitted_at": "精确提交时间",
        "platform_status_raw": "平台状态原文",
        "status_evidence": "处理状态依据",
    }
    for field, label in fields.items():
        if not getattr(record, field) and label not in missing:
            missing.append(label)
    if record.submission_status == SubmissionStatus.UNKNOWN:
        missing.append("提交事实")
    if record.processing_status == ProcessingStatus.UNKNOWN:
        missing.append("处理状态")
    return missing


def create_report(workspace: Path, data: dict) -> Path:
    data = deepcopy(data)
    data.setdefault("kind", "report")
    data.setdefault("created_at", now())
    data.setdefault("updated_at", now())
    if not data.get("history"):
        fields = {k: {"before": None, "after": v} for k, v in data.items() if k != "history"}
        data["history"] = [event("registration", fields, note="本地登记；建档时间不是提交时间")]
    # Validate all fields before allocating an ID and normalize values to JSON/YAML primitives.
    validated = Report.model_validate(data | {"id": data.get("id") or "RPT-LOCAL-001"})
    normalized = validated.model_dump(mode="json")
    normalized["id"] = data.get("id")
    body = template_text("report.md")
    return create_record(
        workspace, "reports", normalized, {"report.md": body}, prefix="RPT", target=data["project"]
    )


def update_report(
    workspace: Path,
    record_id: str,
    fields: dict,
    *,
    historical=False,
    actual_at=None,
    date_raw=None,
    note=None,
    evidence=None,
    corrects=None,
    apply_current=False,
    reason=None,
) -> Path:
    path, data, fingerprint = read_for_update(workspace, record_id)
    if data.get("kind") != "report":
        raise ValueError(f"{record_id} is not a report")
    allowed = set(Report.model_fields) - {
        "id",
        "kind",
        "schema_version",
        "created_at",
        "history",
        "updated_at",
        "source_key",
        "import_fingerprint",
    }
    if set(fields) - allowed:
        raise ValueError("immutable or unknown report fields")
    if apply_current and (not reason or not reason.strip()):
        raise ValueError("校正当前值必须提供 --reason")
    # Dated backfills default to history when older or chronology is uncertain.
    if (actual_at or date_raw) and not apply_current and not historical:
        try:
            previous = datetime.fromisoformat(
                data.get("status_at") or data.get("status_at_raw") or ""
            )
            incoming = datetime.fromisoformat(actual_at or date_raw)
            historical = incoming < previous
        except (ValueError, TypeError):
            historical = True
    if corrects:
        if not reason or not reason.strip():
            raise ValueError("更正必须提供 --reason")
        if corrects not in {e["id"] for e in data.get("history", [])}:
            raise ValueError("correction event not found")
        historical = not apply_current
    if historical and apply_current:
        if not reason or not reason.strip():
            raise ValueError("校正当前值必须提供 --reason")
        historical = False
    changes = {
        k: {"before": deepcopy(data.get(k)), "after": deepcopy(v)}
        for k, v in fields.items()
        if data.get(k) != v
    }
    if not changes and not (note or evidence or corrects):
        raise ValueError("没有变更或反馈；请提供字段或 --note")
    Report.model_validate(data | fields)
    snapshot = deepcopy(data)
    if not historical:
        data.update(deepcopy(fields))
    append_change(
        data,
        changes,
        "correction" if corrects else "feedback",
        snapshot=snapshot,
        actual_at=actual_at,
        date_raw=date_raw,
        note="；".join(v for v in [note, reason] if v) or None,
        evidence=evidence,
        corrects=corrects,
    )
    return update_record(workspace, path, data, fingerprint)


def error(exc):
    typer.echo(f"ERROR {exc}", err=True)
    raise typer.Exit(1) from exc


@report_app.command("add")
def add(
    workspace: Workspace,
    project: Annotated[str | None, typer.Option()] = None,
    title: Annotated[str | None, typer.Option()] = None,
    record_id: Annotated[str | None, typer.Option("--id")] = None,
    channel: Annotated[str | None, typer.Option()] = None,
    external_id: Annotated[str | None, typer.Option()] = None,
    external_url: Annotated[str | None, typer.Option()] = None,
    submission: Annotated[SubmissionStatus, typer.Option()] = SubmissionStatus.UNKNOWN,
    status: Annotated[ProcessingStatus | None, typer.Option()] = None,
    raw_status: Annotated[str | None, typer.Option()] = None,
    submitted_at: Annotated[str | None, typer.Option()] = None,
    submitted_at_raw: Annotated[str | None, typer.Option()] = None,
    status_at: Annotated[str | None, typer.Option()] = None,
    status_at_raw: Annotated[str | None, typer.Option()] = None,
    evidence_type: Annotated[str | None, typer.Option()] = None,
    evidence: Annotated[str | None, typer.Option()] = None,
    evidence_path: Annotated[Path | None, typer.Option()] = None,
    original: Annotated[Path | None, typer.Option()] = None,
    related: Annotated[list[Path] | None, typer.Option()] = None,
    research_ref: Annotated[list[str] | None, typer.Option()] = None,
    missing: Annotated[list[str] | None, typer.Option()] = None,
    note: Annotated[str | None, typer.Option()] = None,
):
    project = project or typer.prompt("项目")
    title = title or typer.prompt("标题")
    if submission == SubmissionStatus.SUBMITTED and not (evidence or evidence_path):
        evidence_type = evidence_type or typer.prompt("提交依据类型（如 local_ledger / receipt）")
        evidence = typer.prompt("已有登记或回执依据")
    try:
        proofs = evidence_value(evidence_type, evidence, evidence_path)
        data = {
            "id": record_id,
            "project": project,
            "title": title,
            "channel": channel,
            "external_id": external_id,
            "external_url": external_url,
            "submission_status": submission.value,
            "submission_evidence": proofs if submission == SubmissionStatus.SUBMITTED else [],
            "processing_status": status.value if status else mapped_status(raw_status or ""),
            "platform_status_raw": raw_status,
            "submitted_at": submitted_at,
            "submitted_at_raw": submitted_at_raw,
            "status_at": status_at,
            "status_at_raw": status_at_raw,
            "status_evidence": proofs if raw_status or status else [],
            "original_report": material(original) if original else None,
            "related_documents": [material(p) for p in related or []],
            "research_refs": research_ref or [],
            "missing_information": missing or [],
            "notes": [note] if note else [],
        }
        similar = [parse_record(p) for p in metadata_files(workspace)]
        for record in similar:
            if isinstance(record, Report) and record.title.casefold() == title.casefold():
                typer.echo(f"提示：标题相同的报告 {record.id}；本次不会自动合并")
        directory = create_report(workspace, data)
    except (ValueError, OSError) as exc:
        error(exc)
    typer.echo(f"已登记 {directory.name}：{directory}")


@report_app.command("list")
def list_reports(
    workspace: Workspace,
    project: Annotated[str | None, typer.Option()] = None,
    status: Annotated[ProcessingStatus | None, typer.Option()] = None,
):
    try:
        for path in metadata_files(workspace):
            record = parse_record(path)
            if not isinstance(record, Report):
                continue
            if project and record.project != project:
                continue
            if status and record.processing_status != status:
                continue
            typer.echo(
                f"{record.id} | {record.project} | {record.title} | "
                f"{record.channel or 'unknown'} | "
                f"{record.external_id or '—'} | {record.submission_status.value} | "
                f"{record.processing_status.value} | {record.updated_at or record.created_at} | "
                f"缺项：{', '.join(missing_fields(record)) or '无'}"
            )
    except (ValueError, OSError) as exc:
        error(exc)


@report_app.command("show")
def show(record_id: str, workspace: Workspace):
    try:
        path, data = find_record(workspace, record_id)
        if data.get("kind") != "report":
            raise ValueError(f"{record_id} is not a report")
        record = Report.model_validate(data)
        from .storage import yaml_bytes

        typer.echo(yaml_bytes(record.model_dump(mode="json")).decode(), nl=False)
        typer.echo("缺项：" + ", ".join(missing_fields(record)))
        typer.echo(f"档案：{path}")
    except (ValueError, OSError) as exc:
        error(exc)


@report_app.command("update")
def update(
    record_id: str,
    workspace: Workspace,
    project: Annotated[str | None, typer.Option()] = None,
    title: Annotated[str | None, typer.Option()] = None,
    channel: Annotated[str | None, typer.Option()] = None,
    external_id: Annotated[str | None, typer.Option()] = None,
    external_url: Annotated[str | None, typer.Option()] = None,
    submission: Annotated[SubmissionStatus | None, typer.Option()] = None,
    status: Annotated[ProcessingStatus | None, typer.Option()] = None,
    raw_status: Annotated[str | None, typer.Option()] = None,
    submitted_at: Annotated[str | None, typer.Option()] = None,
    submitted_at_raw: Annotated[str | None, typer.Option()] = None,
    actual_at: Annotated[str | None, typer.Option()] = None,
    date_raw: Annotated[str | None, typer.Option()] = None,
    evidence_type: Annotated[str | None, typer.Option()] = None,
    evidence: Annotated[str | None, typer.Option()] = None,
    evidence_path: Annotated[Path | None, typer.Option()] = None,
    original: Annotated[Path | None, typer.Option()] = None,
    related: Annotated[list[Path] | None, typer.Option()] = None,
    research_ref: Annotated[list[str] | None, typer.Option()] = None,
    missing: Annotated[list[str] | None, typer.Option()] = None,
    note: Annotated[str | None, typer.Option()] = None,
    historical: Annotated[bool, typer.Option()] = False,
    corrects: Annotated[str | None, typer.Option()] = None,
    apply_current: Annotated[bool, typer.Option()] = False,
    reason: Annotated[str | None, typer.Option()] = None,
    yes: Annotated[bool, typer.Option("--yes")] = False,
):
    if apply_current and not yes:
        if not typer.confirm("确认校正当前字段并追加事件？", default=False):
            raise typer.Exit(1)
    try:
        fields = {
            k: v
            for k, v in {
                "project": project,
                "title": title,
                "channel": channel,
                "external_id": external_id,
                "external_url": external_url,
                "submitted_at": submitted_at,
                "submitted_at_raw": submitted_at_raw,
                "platform_status_raw": raw_status,
            }.items()
            if v is not None
        }
        if submission:
            fields["submission_status"] = submission.value
        if status or raw_status is not None:
            fields["processing_status"] = status.value if status else mapped_status(raw_status)
            fields["platform_status_raw"] = raw_status
            fields["status_evidence"] = []
            fields["status_at"] = actual_at
            fields["status_at_raw"] = date_raw
        proofs = evidence_value(evidence_type, evidence, evidence_path)
        if proofs:
            if submission == SubmissionStatus.SUBMITTED:
                fields["submission_evidence"] = proofs
            if status or raw_status is not None:
                fields["status_evidence"] = proofs
        if original:
            fields["original_report"] = material(original)
        for option, name, convert in [
            (related, "related_documents", material),
            (research_ref, "research_refs", str),
            (missing, "missing_information", str),
        ]:
            if option is not None:
                fields[name] = [convert(v) for v in option]
        if not fields and not note and not corrects and not proofs:
            note = typer.prompt("反馈备注")
        backup = update_report(
            workspace,
            record_id,
            fields,
            historical=historical,
            actual_at=actual_at,
            date_raw=date_raw,
            note=note,
            evidence=proofs,
            corrects=corrects,
            apply_current=apply_current,
            reason=reason,
        )
    except (ValueError, OSError) as exc:
        error(exc)
    typer.echo(f"已更新 {record_id}；备份：{backup.name}")
