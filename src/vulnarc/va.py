"""Local case registration from a reviewed manifest; never executes report contents."""

import json
import re
import unicodedata
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from shlex import quote
from typing import Annotated
from zoneinfo import ZoneInfo

import typer

from .history import event, now
from .materials import material_problem
from .materials import verify_case_materials as verify_materials
from .models import CaseDetails, VACase
from .storage import (
    create_record,
    digest,
    find_record,
    load_yaml,
    metadata_files,
    validate_workspace,
)

va_app = typer.Typer(help="VA 案例档案：登记、查阅、总账。仅处理本地材料。", no_args_is_help=True)
Workspace = Annotated[Path, typer.Option("--workspace", "-w", help="私有案例工作区")]
INTAKE_SCHEMA = "vulnarc-case-intake-v1"


class ReportChoice(StrEnum):
    PRIMARY = "primary"
    TRANSLATION = "translation"


REPORT_ROLES = {ReportChoice.PRIMARY: "primary_report", ReportChoice.TRANSLATION: "translation"}


def material_status(ref) -> tuple[str, bool]:
    """Inspect each source independently so a broken attachment does not hide the others."""
    try:
        problem = material_problem(
            ref.path, ref.sha256, absolute_required=True, hash_required=True
        )
    except OSError as exc:
        return f"读取失败：{clean(str(exc))}", False
    messages = {
        None: "通过（SHA-256 一致）",
        "required": "缺少路径或 SHA-256",
        "missing": "文件缺失或不是绝对文件路径",
        "hash": "哈希变化（source hash changed）",
    }
    return messages[problem], problem is None


def material_entries(record: VACase) -> bool:
    """Render current metadata, never the potentially stale materials.md snapshot."""
    valid = True
    for ref in record.materials:
        status, passed = material_status(ref)
        valid &= passed
        typer.echo(f"- {clean(ref.role)} · {clean(ref.label)}")
        typer.echo(f"  路径：{clean(ref.path)}")
        typer.echo(f"  登记 SHA-256：{ref.sha256 or '待补'}")
        typer.echo(f"  校验：{status}")
    return valid


def reading_entries(record: VACase, workspace: Path) -> None:
    """Commands include the explicit workspace required by the formal entry point."""
    for choice, role in REPORT_ROLES.items():
        refs = [ref for ref in record.materials if ref.role == role]
        state = f"{len(refs)} 份" if refs else "未登记"
        typer.echo(f"正文 {choice.value}：{state}")
        if refs:
            typer.echo(
                f"  vulnarc va read {record.id} --report {choice.value}"
                f" --workspace {quote(str(workspace))}"
            )
    typer.echo(f"材料入口：vulnarc va materials {record.id} --workspace {quote(str(workspace))}")


def local_year() -> str:
    return str(datetime.now(ZoneInfo("Asia/Shanghai")).year)


def read_intake(path: Path) -> tuple[CaseDetails, str]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if set(document) != {"schema", "case"} or document["schema"] != INTAKE_SCHEMA:
        raise ValueError("unknown case intake schema")
    details = CaseDetails.model_validate(document["case"])
    fingerprint = digest(
        json.dumps(details.model_dump(mode="json"), ensure_ascii=False, sort_keys=True).encode()
    )
    return details, fingerprint


def link(path: str, label: str) -> str:
    return f"[{label}](<{path}>)"


def render_documents(data: dict) -> dict[str, str]:
    record = VACase.model_validate(data)
    verify_materials(record)
    ratings = (
        "\n".join(
            f"- CVSS {r.version} **{r.score:g}**（{r.attribution}，既有报告转录）"
            f"；`{r.vector}`；{link(r.source.path, '依据')}:{r.source.line}"
            for r in record.ratings
        )
        or "- 尚未登记评分。"
    )
    references = (
        "\n".join(f"- {r.identifier}：参考案例，不是本案获配编号。" for r in record.reference_cases)
        or "- 无参考编号。"
    )
    case = (
        f"""# {record.id} · {record.title}

> 本地案例登记；不是 CVE 分配或厂商接受证明。技术内容来自既有文档，本次未复验。

## 案例身份
- 项目：{record.project}
- 用途：{record.purpose}
- 原编号：{", ".join(record.legacy_ids)}
- 分类：{record.category}
- CWE：{", ".join(record.cwe) or "待补"}
- 建档时间：{record.created_at.isoformat()}（不等于提交时间）

## 摘要
{record.summary}

## 严重度（保留归属，不重新计算）
{ratings}

## 本案外部编号
{", ".join(record.assigned_identifiers) or "尚未登记本案 CVE/GHSA 等编号。"}

## 参考案例
{references}

## 原报告的版本主张（仅转录）
"""
        + "\n".join("- " + v for v in record.reported_versions)
        + f"""

## 投稿信息
- 计划渠道：{record.planned_channel or "待补"}
- 计划提交日：{record.planned_submission_date_raw or "待补"}
- 登记提交状态：{record.submission_status.value}
- 状态依据：{record.submission_basis}；{record.submission_note or "待补"}
- 平台处理状态：{record.processing_status.value}
- 外部报告号：{record.external_report_id or "待补"}

## 待补信息
"""
        + "\n".join("- " + m for m in record.missing_information)
        + "\n"
    )
    materials = (
        f"# {record.id} · 报告与材料索引\n\n原件只引用和校验哈希，不搬迁、不执行、不解包。\n\n"
    )
    for ref in record.materials:
        materials += (
            f"- **{ref.role}** · {link(ref.path, ref.label)}\n  - SHA-256：`{ref.sha256}`\n"
        )
    timeline = f"# {record.id} · 登记时间线\n\n"
    timeline += f"- {record.created_at.isoformat()}：首次本地归档成功，未向外部平台发送。\n"
    timeline += "\n## 历史材料依据（不是新的验证事件）\n"
    for proof in record.evidence:
        timeline += (
            f"- {proof.date_raw or '源日期待补'}：{proof.note or '材料依据'}；"
            f"{link(proof.path, '原文')}:{proof.line or 1}\n"
        )
    timeline += "\n后续平台反馈按新事件登记；计划提交日不计作实际提交日。\n"
    learning = f"# {record.id} · 学习与经验\n\n仅归纳既有报告与本次归档工程，不增加利用步骤。\n\n"
    learning += "\n".join("- " + n for n in record.learning_notes) + "\n"
    learning += "\n## 学习状态\n已整理现有报告；本次未运行复现、未重新验证修复。\n"
    return {
        "case.md": case,
        "materials.md": materials,
        "timeline.md": timeline,
        "learning.md": learning,
    }


def register_case(workspace: Path, intake: Path) -> tuple[VACase, Path, bool]:
    details, fingerprint = read_intake(intake)
    verify_materials(details)
    errors = validate_workspace(workspace)
    if errors:
        raise ValueError("existing workspace validation failed: " + errors[0])
    for path in metadata_files(workspace):
        existing = load_yaml(path)
        if existing.get("source_key") != details.source_key:
            continue
        if existing.get("kind") != "va_case" or existing.get("intake_sha256") != fingerprint:
            raise ValueError("source already registered with different data; no overwrite")
        record = VACase.model_validate(existing)
        verify_materials(record)
        for name in render_documents(existing):
            if not (path.parent / name).is_file():
                raise ValueError(f"existing case is incomplete: {name}")
        return record, path.parent, False
    stamp = now()
    data = details.model_dump(mode="json") | {
        "id": None,
        "kind": "va_case",
        "schema_version": 1,
        "created_at": stamp,
        "updated_at": stamp,
        "intake_sha256": fingerprint,
        "history": [event("case_registered", {}, note="本地材料归档，未对外提交")],
    }
    path = create_record(
        workspace,
        "cases/private",
        data,
        {},
        prefix="VA",
        target=local_year(),
        body_factory=render_documents,
    )
    # Reopen persisted data/documents before emitting any allocation success message.
    record = VACase.model_validate(load_yaml(path / "metadata.yaml"))
    verify_materials(record)
    for name in render_documents(record.model_dump(mode="json")):
        if not (path / name).is_file():
            raise ValueError(f"incomplete persisted case: {name}")
    return record, path, True


def clean(text: str) -> str:
    return re.sub(r"[\x00-\x1f\x7f]", " ", text)


def display_width(text: str) -> int:
    return sum(
        0 if unicodedata.combining(c) else 2 if unicodedata.east_asian_width(c) in "WF" else 1
        for c in text
    )


def receipt(
    record: VACase, path: Path, mode="show", *, material_summary: str | None = None
) -> None:
    caption = {
        "created": "已为您分配好 VA 编号",
        "existing": "已找到原档案 · 未重复分配",
        "show": "VulnArc 案例卡",
    }[mode]
    main = next((r for r in record.ratings if r.attribution == "reporter"), None)
    rating = f"CVSS {main.version} · {main.score:g} · 报告自评" if main else "CVSS · 待补"
    status = {
        "unknown": "外部提交待确认",
        "not_submitted": "尚未对外提交",
        "submitted": "已有外部提交记录",
        "withdrawn": "已撤回",
    }[record.submission_status.value]
    if (
        record.submission_status.value == "submitted"
        and record.submission_basis == "user_instruction"
    ):
        status = "已提交（按用户口径；平台回执待补）"
    rows = [
        "V U L N A R C",
        "",
        caption,
        "",
        record.id,
        "",
        f"项目  {record.project}",
        f"分类  {record.category}",
        f"弱点  {', '.join(record.cwe) or '待补'}",
        rating,
        f"材料  {material_summary or f'{len(record.materials)} 份 · SHA-256 已核对'}",
        status,
        "",
        "本地归档完成 · 本次未向外部平台发送",
    ]
    rows = [clean(row) for row in rows]
    width = max(54, max(map(display_width, rows)) + 4)
    typer.echo("╭" + "─" * width + "╮")
    for row in rows:
        space = width - display_width(row)
        typer.echo("│" + " " * (space // 2) + row + " " * (space - space // 2) + "│")
    typer.echo("╰" + "─" * width + "╯")
    typer.echo(f"案例：{path / 'case.md'}")
    typer.echo(f"查看：va show {record.id}")


@va_app.command("register")
def register(
    intake: Path,
    workspace: Workspace,
    apply: Annotated[bool, typer.Option("--apply", help="确认本地登记")] = False,
):
    """导入已经人工整理的案例清单。默认只预览，--apply 才保存与分配编号。"""
    try:
        if not apply:
            details, _ = read_intake(intake)
            verify_materials(details)
            typer.echo("登记预览 · 尚未分配编号 · 零工作区写入")
            typer.echo(f"项目：{details.project}\n标题：{details.title}")
            typer.echo(f"材料：{len(details.materials)} 份\n本地确认登记请添加 --apply")
            return
        record, path, created = register_case(workspace, intake)
        receipt(record, path, "created" if created else "existing")
    except (ValueError, OSError, KeyError) as exc:
        typer.echo(f"登记未完成：{exc}", err=True)
        raise typer.Exit(1) from exc


@va_app.command("show")
def show(record_id: str, workspace: Workspace):
    """显示案例卡、正文入口和当前材料校验状态，不改动档案。"""
    try:
        path, data = find_record(workspace, record_id)
        record = VACase.model_validate(data)
        receipt(record, path.parent, material_summary=f"{len(record.materials)} 份 · 校验见下方")
        reading_entries(record, workspace)
        if not material_entries(record):
            raise typer.Exit(1)
    except (ValueError, OSError) as exc:
        typer.echo(f"查阅未完成：{exc}", err=True)
        raise typer.Exit(1) from exc


@va_app.command("read")
def read_report(
    record_id: str,
    workspace: Workspace,
    report: Annotated[ReportChoice, typer.Option("--report", help="主报告或中文翻译")]
    = ReportChoice.PRIMARY,
):
    """按 VA 编号输出完整 UTF-8 Markdown/文本正文；只核对所选原件，不执行内容。"""
    try:
        _, data = find_record(workspace, record_id)
        record = VACase.model_validate(data)
        refs = [ref for ref in record.materials if ref.role == REPORT_ROLES[report]]
        if not refs:
            raise ValueError(f"未登记 {report.value} 报告；用 va materials {record.id} 查看材料")
        if len(refs) != 1:
            paths = ", ".join(clean(ref.path) for ref in refs)
            raise ValueError(f"{report.value} 报告不唯一（{len(refs)} 份）：{paths}")
        ref = refs[0]
        source = Path(ref.path)
        if not source.is_absolute() or not source.is_file():
            raise ValueError(f"报告文件缺失或不是绝对文件路径：{clean(ref.path)}")
        if not ref.sha256:
            raise ValueError(f"报告缺少 SHA-256：{clean(ref.path)}")
        # Hash and decode the same byte snapshot; never reopen after verification.
        content = source.read_bytes()
        if digest(content) != ref.sha256:
            raise ValueError(f"报告哈希变化（source hash changed）：{clean(ref.path)}")
        if source.suffix.lower() not in {".md", ".markdown", ".txt"}:
            raise ValueError(f"正文阅读支持 UTF-8 Markdown/文本；其他格式见材料入口：{source}")
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"报告不是 UTF-8 文本：{clean(ref.path)}") from exc
        if any(unicodedata.category(c) == "Cc" and c not in "\n\r\t" for c in text):
            raise ValueError(f"报告含终端控制字符：{clean(ref.path)}")
        typer.echo(text, nl=False)
    except (ValueError, OSError) as exc:
        typer.echo(f"正文查阅未完成：{clean(str(exc))}", err=True)
        raise typer.Exit(1) from exc


@va_app.command("materials")
def materials(record_id: str, workspace: Workspace):
    """按 VA 编号逐项列出报告和附件的位置、角色、登记哈希和当前校验情况。"""
    try:
        _, data = find_record(workspace, record_id)
        record = VACase.model_validate(data)
        typer.echo(f"{record.id} · 当前报告与材料（只读）")
        if not material_entries(record):
            raise typer.Exit(1)
    except (ValueError, OSError) as exc:
        typer.echo(f"材料查阅未完成：{clean(str(exc))}", err=True)
        raise typer.Exit(1) from exc


@va_app.command("list")
def list_cases(workspace: Workspace):
    """编号总账由真实元数据生成，避免额外索引与档案不同步。"""
    count = 0
    for path in metadata_files(workspace):
        data = load_yaml(path)
        if data.get("kind") == "va_case":
            record = VACase.model_validate(data)
            typer.echo(f"{record.id}  {clean(record.project)}  {clean(record.title)}")
            count += 1
    typer.echo(f"共 {count} 份 VA 案例；编号不代表厂商确认或 CVE 分配。")


@va_app.command("check")
def check(workspace: Workspace):
    """校验档案结构、材料哈希与引用；不执行报告中的命令。"""
    errors = validate_workspace(workspace)
    if errors:
        for error in errors:
            typer.echo(error, err=True)
        raise typer.Exit(1)
    typer.echo(f"档案校验通过：{len(metadata_files(workspace))} 条记录。")
