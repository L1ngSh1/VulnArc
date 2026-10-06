# Archive an existing report as a VA case

Use the [release installation](installation.md). `vulnarc va` is the formal command group;
`va` is its compatibility shortcut. A VA identifier is internal, not a CVE or vendor acceptance.

```bash
vulnarc va register /absolute/path/to/reviewed-intake.json --workspace /absolute/path/to/private-workspace
vulnarc va register /absolute/path/to/reviewed-intake.json --workspace /absolute/path/to/private-workspace --apply
vulnarc va list --workspace /absolute/path/to/private-workspace
vulnarc va show VA-2026-0001 --workspace /absolute/path/to/private-workspace
vulnarc va check --workspace /absolute/path/to/private-workspace
```

Prepare and review the intake JSON, preview, then apply. IDs are announced only after the
record is persisted, reopened and source hashes are checked. An identical repeat reuses
the ID without replacing handwritten notes. Changed intake is not an overwrite. Failed
or deleted IDs are not reused; gaps are allowed. The allocation year uses Asia/Shanghai.

`metadata.yaml` stores structured fields and history. `case.md`, `materials.md` and
`timeline.md` are registration snapshots; they are not live YAML/history views.
`learning.md` is for handwritten follow-up notes; `learning_notes` remains initial-import
content. The original report supplies the body, and reviewed JSON supplies import input.
Read the [maintenance contract](maintenance.md) for VA/RPT rules and distinct counts.

## Read a registered report and find its materials

```bash
WS="/absolute/path/to/private workspace"
vulnarc va show VA-2026-0001 --workspace "$WS"
vulnarc va read VA-2026-0001 --workspace "$WS"
vulnarc va read VA-2026-0001 --report translation --workspace "$WS"
vulnarc va materials VA-2026-0001 --workspace "$WS"
# If several translations are registered, use the number shown by materials:
vulnarc va read VA-2026-0001 --report translation --material 2 --workspace "$WS"
```

- `show` loads metadata only: title, source, rating attribution, submission/processing status,
  material count and commands quoting the actual workspace. Its materials are **unverified**;
  a missing attachment does not hide the overview. Registration receipts still mean all
  required sources have been checked.
- `read` selects the registered `primary_report` by default, or `translation` explicitly;
  it never guesses by filename or translates content. Multiple matching reports require
  `--material N`; N is the current 1-based position in `materials`, not a durable ID.
  A number outside the list or from another role is a parameter error.
- In a pipe or with `--raw`, complete UTF-8 text goes to stdout, with no truncation or added final newline. Identifier,
  role, source path and SHA-256 confirmation go to stderr. BOM is an encoding marker;
  terminal/bidirectional controls become visible escapes, while normal Markdown whitespace
  remains. Hashing uses original bytes, and output uses those same checked bytes.
- Missing/relative paths, missing hashes, changed hashes and read errors prevent body output;
  unrelated broken attachments do not block a valid report. Non-text formats, NUL-containing
  binary data and invalid UTF-8 show the original path, not a parser or partial body.
- `materials` checks every item independently and lists its number, role, label, original path
  and real integrity status, including remaining items after an error. Hash confirmation is
  not a claim that the material is a text report or that its vulnerability is valid.
- `show`, `read` and `materials` do not write records, snapshots, notes, locks or caches. They
  neither execute code/HTML/links nor open a browser, unpack archives, invoke a pager or use
  the network. PDFs, Word documents and images are not parsed; find originals in the list.

### Terminal reading layout

In a terminal, `read` automatically renders Markdown inside a bounded-width body panel,
with a separate source/verification panel on stderr. Headings, emphasis, lists, quotes,
tables and highlighted fenced code are formatted; long table cells and code lines wrap
instead of being replaced by ellipses. The page follows the current terminal width, keeping two columns of side margin rather
than a fixed 100-column cap. An explicit `--width 90` sets a narrower reading width
(40–200) and centers the page; either mode stays inside the available terminal width.
Paragraphs have an extra blank row, sections have breathing room, and the source/body
panels are separated. Code, table rows and tight list items do not get internal blank rows.

```bash
vulnarc va read VA-2026-0001 --pretty --workspace "$WS"
vulnarc va read VA-2026-0001 --pretty --width 90 --workspace "$WS"
vulnarc va read VA-2026-0001 --report translation --workspace "$WS"
vulnarc va read VA-2026-0001 --raw --workspace "$WS"
```

The header shows the current report and the option for switching to a registered translation
(or back to the primary). If your Chinese report is registered as `translation`, select it
with `--report translation`; this does not infer a language or create a translation.
`--pretty` forces the layout; `--raw` forces original text even in a terminal. They are
mutually exclusive. Pipes retain raw output by default; source details remain on stderr.
Links are displayed as text, with terminal hyperlinks disabled. No pager or browser is started.
A new invocation measures the current terminal dimensions; existing scrollback is not a live TUI.
Rich is declared directly for this view; it was already present through Typer, and the
locked runtime package set/versions have not changed.

Exit status: success 0; missing case, invalid metadata or material/text failure 1;
invalid options, conflicting/out-of-range numbers or ambiguous selection 2. `materials`
returns 1 if any item fails while still showing the entire list. `show` success is not a
workspace integrity verdict. `check` retains strict full-workspace checks of source hashes,
evidence lines and snapshot existence, not Markdown/YAML synchronization.

Moving or editing originals makes validation fail. Note editing commands, VA update, a live
timeline, interactive intake, search, web UI and cross-machine relinking remain future work.

Submission and processing states are separate; explicit provenance distinguishes user
instructions from platform receipts. Reference identifiers are not this case's assigned
identifiers. The CLI does not upload, submit or execute report commands. Code rollback
is separate from data recovery; keep the original VA-capable runtime until verification.
