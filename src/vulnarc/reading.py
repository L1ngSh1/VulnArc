"""Read-only VA selection and presentation; report contents are never executed."""

import shlex
from enum import StrEnum
from pathlib import Path

from .materials import read_material
from .models import CaseMaterial, VACase
from .storage import find_record


class ReportKind(StrEnum):
    PRIMARY = "primary"
    TRANSLATION = "translation"


class SelectionError(ValueError):
    """A material number is needed or conflicts with the requested role."""


BIDI_CONTROLS = frozenset(
    "\u061c\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069"
)
NON_TEXT_SUFFIXES = frozenset(
    {
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".zip",
        ".gz",
        ".bz2",
        ".xz",
        ".7z",
        ".rar",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".mp3",
        ".mp4",
        ".wav",
        ".exe",
        ".dll",
        ".so",
        ".dylib",
    }
)
NON_TEXT_SIGNATURES = (
    b"%PDF-",
    b"PK\x03\x04",
    b"\x89PNG",
    b"GIF87a",
    b"GIF89a",
    b"\xff\xd8\xff",
    b"\xd0\xcf\x11\xe0",
    b"\x1f\x8b",
)


def visible_text(text: str, *, multiline: bool = False) -> str:
    """Keep Markdown whitespace but render terminal/bidi controls literally."""
    parts = []
    for i, char in enumerate(text):
        code = ord(char)
        if multiline and (char in "\n\t" or (char == "\r" and text[i + 1 : i + 2] == "\n")):
            parts.append(char)
        elif code < 32 or 127 <= code <= 159 or char in BIDI_CONTROLS:
            parts.append(f"\\x{code:02x}" if code < 256 else f"\\u{code:04x}")
        else:
            parts.append(char)
    return "".join(parts)


def load_case(workspace: Path, record_id: str) -> tuple[Path, VACase]:
    path, data = find_record(workspace, record_id)
    return path, VACase.model_validate(data)


def select_report(record: VACase, report: ReportKind, number: int | None) -> CaseMaterial:
    role = "primary_report" if report == ReportKind.PRIMARY else "translation"
    if number is not None:
        if not 1 <= number <= len(record.materials):
            raise SelectionError(f"--material 须在 1..{len(record.materials)} 范围内")
        ref = record.materials[number - 1]
        if ref.role != role:
            raise SelectionError(f"材料 {number} 的角色不是 {role}；请与 --report 一致")
        return ref
    candidates = [(i, ref) for i, ref in enumerate(record.materials, 1) if ref.role == role]
    if not candidates:
        raise ValueError(f"未登记 {role} 报告")
    if len(candidates) > 1:
        lines = [f"存在多份 {role}；请添加 --material N（材料清单的当前序号）："]
        lines += [
            f"{i}. {visible_text(ref.label)} · {visible_text(ref.path)}" for i, ref in candidates
        ]
        raise SelectionError("\n".join(lines))
    return candidates[0][1]


def inspect_material(ref: CaseMaterial) -> tuple[bytes | None, str | None]:
    """Contain one item's I/O failure; never weaken VA's path/hash requirements."""
    try:
        problem, content = read_material(
            ref.path,
            ref.sha256,
            absolute_required=True,
            hash_required=True,
        )
    except OSError as exc:
        return None, f"原件读取失败：{visible_text(str(exc))}"
    errors = {
        "required": "缺少原件路径或 SHA-256（未校验）",
        "missing": "原件路径缺失、不是文件或不是绝对路径",
        "hash": "SHA-256 变化（source hash changed）",
    }
    return content, errors.get(problem)


def report_text(ref: CaseMaterial) -> str:
    content, error = inspect_material(ref)
    if error:
        raise ValueError(f"{error}；原件：{visible_text(ref.path)}")
    if (
        Path(ref.path).suffix.lower() in NON_TEXT_SUFFIXES
        or b"\x00" in content
        or content.startswith(NON_TEXT_SIGNATURES)
    ):
        raise ValueError(f"材料类型不是 UTF-8 文本；原件：{visible_text(ref.path)}")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(f"材料不是有效 UTF-8 文本；原件：{visible_text(ref.path)}") from exc
    return visible_text(text, multiline=True)


def overview_lines(record: VACase, path: Path, workspace: Path) -> list[str]:
    """Overview explicitly has no source integrity verdict or disk side effects."""
    fields = [
        ("编号", record.id),
        ("标题", record.title),
        ("项目", record.project),
        ("来源", record.source_key),
        ("用途", record.purpose),
        ("登记状态", record.submission_status.value),
        ("状态依据", record.submission_basis),
        ("平台处理状态", record.processing_status.value),
    ]
    lines = ["VulnArc 案例概览", *[f"{label}：{visible_text(value)}" for label, value in fields]]
    lines += [
        f"评分：CVSS {r.version} · {r.score:g} · {visible_text(r.attribution)}"
        for r in record.ratings
    ] or ["评分：待补"]
    lines += [
        f"材料：{len(record.materials)} 份 · 未校验",
        f"案例快照：{visible_text(str(path.parent / 'case.md'))}",
        "概览不代表全库完整性校验；原件核对请使用 materials/check。",
    ]
    commands = [("正文", ["read", record.id, "--report", "primary"])]
    if any(ref.role == "translation" for ref in record.materials):
        commands.append(("翻译", ["read", record.id, "--report", "translation"]))
    commands += [("材料", ["materials", record.id]), ("全库校验", ["check"])]
    for label, args in commands:
        command = shlex.join(["vulnarc", "va", *args, "--workspace", str(workspace.resolve())])
        lines.append(f"{label}：{visible_text(command)}")
    return lines
