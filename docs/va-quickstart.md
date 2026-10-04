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

`show` displays an identifier card and case path, not report body text. `check` checks
source hashes, evidence lines and document existence, not Markdown/YAML synchronization.
Moving or editing originals makes validation fail. Body reading, note editing commands,
VA update, a live timeline, interactive intake, search and web UI remain future work.

Submission and processing states are separate; explicit provenance distinguishes user
instructions from platform receipts. Reference identifiers are not this case's assigned
identifiers. The CLI does not upload, submit or execute report commands. Code rollback
is separate from data recovery; keep the original VA-capable runtime until verification.
