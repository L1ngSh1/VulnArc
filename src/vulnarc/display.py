"""Bounded-width terminal Markdown views; no paging, network or persisted report copies."""

import sys

from rich.align import Align
from rich.console import Console, Group
from rich.markdown import Heading, Markdown, Paragraph, TableElement
from rich.padding import Padding
from rich.panel import Panel
from rich.text import Text

from .models import CaseMaterial, VACase
from .reading import ReportKind, visible_text


class WrappingTable(TableElement):
    """Fold Markdown table cells instead of Rich's default ellipsis overflow."""

    def __rich_console__(self, console, options):
        for table in super().__rich_console__(console, options):
            for column in table.columns:
                column.overflow = "fold"
                column.no_wrap = False
            yield table


class SpacedParagraph(Paragraph):
    @classmethod
    def create(cls, markdown, token):
        paragraph = super().create(markdown, token)
        # Tight list items stay tight; paragraphs get one extra blank row.
        paragraph.space_after = 0 if token.hidden else 1
        return paragraph

    def __rich_console__(self, console, options):
        yield Padding(
            Group(*super().__rich_console__(console, options)), (0, 0, self.space_after, 0)
        )


class SpacedHeading(Heading):
    def __rich_console__(self, console, options):
        yield Padding(
            Group(*super().__rich_console__(console, options)),
            (0 if self.tag == "h1" else 1, 0, 0, 0),
        )


class ReportMarkdown(Markdown):
    elements = {
        **Markdown.elements,
        "table_open": WrappingTable,
        "paragraph_open": SpacedParagraph,
        "heading_open": SpacedHeading,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._visible_tokens(self.parsed)

    @classmethod
    def _visible_tokens(cls, tokens):
        # Markdown entity decoding may introduce bidi controls that were not
        # literal code points in the original report. Keep them visible too.
        for token in tokens:
            token.content = visible_text(token.content, multiline=True)
            if token.children:
                cls._visible_tokens(token.children)


def pretty_enabled(*, pretty: bool, raw: bool) -> bool:
    """A pipe/export keeps the original text contract unless pretty is explicit."""
    return not raw and (pretty or sys.stdout.isatty())


def reading_header(
    record: VACase,
    ref: CaseMaterial,
    report: ReportKind,
) -> Group:
    """All metadata is literal Text, never Rich markup or a terminal hyperlink."""
    selected = "主报告" if report == ReportKind.PRIMARY else "已登记翻译"
    lines = [
        Text(f"{record.id}  ·  {selected}  ·  SHA-256 已核对", style="bold green"),
        Text(visible_text(record.title), style="bold"),
        Text(""),
        Text(f"材料：{visible_text(ref.label)}", style="dim"),
        Text(f"原件：{visible_text(ref.path)}", style="dim"),
        Text(""),
    ]
    has_translation = any(item.role == "translation" for item in record.materials)
    tabs = "● 主报告" if report == ReportKind.PRIMARY else "○ 主报告"
    if has_translation:
        tabs += "     " + ("● 已登记翻译" if report == ReportKind.TRANSLATION else "○ 已登记翻译")
    lines.append(Text(tabs, style="bold cyan"))
    if has_translation:
        other = "translation" if report == ReportKind.PRIMARY else "primary"
        label = "已登记翻译（中文报告若已登记）" if other == "translation" else "主报告"
        lines.append(Text(f"切换到{label}：追加 --report {other}", style="cyan"))
    else:
        lines.append(Text("尚未登记翻译；只显示已有报告，不自动翻译。", style="dim"))
    return Group(*lines)


def render_report(
    record: VACase,
    ref: CaseMaterial,
    report: ReportKind,
    text: str,
    *,
    width: int | None = None,
    console: Console | None = None,
    metadata_console: Console | None = None,
) -> None:
    """Metadata stays on stderr; only the framed Markdown body goes to stdout."""
    console = console or Console(highlight=False, markup=False, emoji=False)
    metadata_console = metadata_console or Console(
        stderr=True,
        width=console.width,
        highlight=False,
        markup=False,
        emoji=False,
    )
    # Default fills the current terminal, leaving two cells on each side.
    # Explicit narrower pages are centered instead of stranded on the left.
    available_width = max(1, console.width - (4 if console.width >= 40 else 0))
    page_width = min(width or available_width, available_width)
    metadata_console.print(
        Align.center(
            Panel(
                reading_header(record, ref, report),
                title=Text("V U L N A R C  /  报告阅读", style="bold cyan"),
                title_align="left",
                border_style="cyan",
                width=page_width,
                padding=(1, 2),
            )
        )
    )
    console.print()
    console.print(
        Align.center(
            Panel(
                ReportMarkdown(text, hyperlinks=False, justify="left"),
                title=Text("正文 · Markdown", style="bold"),
                title_align="left",
                border_style="bright_black",
                width=page_width,
                padding=(1, 2),
            )
        )
    )
