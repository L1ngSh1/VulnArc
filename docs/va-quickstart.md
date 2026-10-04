# Archive an existing report as a VA case

Use the [release installation](installation.md). `vulnarc va` is the formal command group;
`va` is its compatibility shortcut. A VA identifier is internal, not a CVE or vendor acceptance.

```bash
vulnarc va register /absolute/path/to/reviewed-intake.json --workspace /absolute/path/to/private-workspace
vulnarc va register /absolute/path/to/reviewed-intake.json --workspace /absolute/path/to/private-workspace --apply
vulnarc va list --workspace /absolute/path/to/private-workspace
vulnarc va show VA-2026-0001 --workspace /absolute/path/to/private-workspace
vulnarc va read VA-2026-0001 --report primary --workspace /absolute/path/to/private-workspace
vulnarc va read VA-2026-0001 --report translation --workspace /absolute/path/to/private-workspace
vulnarc va materials VA-2026-0001 --workspace /absolute/path/to/private-workspace
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

## Read using only the VA identifier

`read --report primary` (the default) selects `primary_report`; `--report translation`
selects `translation`. It verifies and decodes the same byte snapshot, then prints the
complete UTF-8 Markdown/text (`.md`, `.markdown`, `.txt`) body without a summary or wrapper.
It does not open a browser, execute code blocks, extract archives or write files. Other
formats stay accessible by path in `materials`; this step does not add PDF/Word rendering.
Missing/changed files, absent translations, ambiguous roles, missing hashes, invalid UTF-8
and terminal control characters are explicit errors; no unverified body is printed.

`materials` reads current YAML, not the registration snapshot, and lists every material's
role, label, absolute path, registered SHA-256 and current check result. It continues after
a missing/unreadable/changed file and exits 1 if any material fails. A broken attachment
never blocks reading a verified report. `show` retains the card, prints runnable read and
materials commands with the workspace, and includes these per-file checks (exit 1 on failure).
These checks describe source integrity, not new vulnerability validation or evidence-line checks.

`check` remains the full workspace/evidence/document validator. Moving or editing originals
makes validation fail; reads never update metadata, notes, history or hashes. The formal
`vulnarc` entry point still requires `-w`; the compatibility `va` shortcut also supports
`read` and `materials` with its existing workspace environment/default precedence.
Note editing commands, VA update, a live timeline, interactive intake, search and web UI
remain future work.

Submission and processing states are separate; explicit provenance distinguishes user
instructions from platform receipts. Reference identifiers are not this case's assigned
identifiers. The CLI does not upload, submit or execute report commands. Code rollback
is separate from data recovery; keep the original VA-capable runtime until verification.
