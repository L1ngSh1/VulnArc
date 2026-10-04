# VulnArc — Human–AI Collaborative Vulnerability Research

[中文首页](docs/docs-zh/README.md)

**From hypothesis to disclosure, with existing reports kept intact.**

VulnArc is a repo-first research notebook. YAML records structured facts and history;
Markdown preserves reasoning and handwritten notes. An AI finding remains a hypothesis
until reproducible evidence and human validation support it. The CLI never submits,
pushes, publishes or uploads records.

## Start with an existing report

Use the [single release installation guide](docs/installation.md), then a reviewed
intake JSON and an explicitly selected external workspace:

```bash
vulnarc va register /absolute/path/to/reviewed-intake.json --workspace /absolute/path/to/VulnArc-Research
vulnarc va register /absolute/path/to/reviewed-intake.json --workspace /absolute/path/to/VulnArc-Research --apply
vulnarc va list --workspace /absolute/path/to/VulnArc-Research
vulnarc va show VA-2026-0001 --workspace /absolute/path/to/VulnArc-Research
vulnarc va check --workspace /absolute/path/to/VulnArc-Research
```

Preview does not write or allocate an ID. `--apply` registers a local `VA-YYYY-NNNN` case,
not a CVE or vendor acceptance. Repeating an identical intake preserves its ID and manual
notes. `show` displays a card and document path, not the original report body.
Read the [VA guide](docs/va-quickstart.md) and [maintenance contract](docs/maintenance.md).

## Implemented commands

| Purpose | Current commands |
| --- | --- |
| New local case archives | `va register`, `va list`, `va show`, `va check` |
| Existing RPT records | `report add`, `report list`, `report show`, `report update` |
| One-off legacy inventory | `report import-inventory` (specific format; preview by default) |
| Workspace and recovery | `validate`, `list`, `restore` |
| Advanced research | `new hypothesis`, `new experiment`, `new case`, `status`, `stats`, `compare` |

**Planned, not implemented:** report-body reader, note editing command, VA update, unified
live timeline, interactive case intake, search and web UI. VA/RPT models remain separate;
there is no automatic conversion or second RPT for a new VA case.

## Advanced research

HYP/EXP and disclosed public cases remain available; they are not prerequisites for
archiving an existing report. See [workflow](docs/research-workflow.md),
[methodology](docs/methodology.md), [architecture](docs/architecture.md) and
[workspace model](docs/workspace-model.md). Existing RPT feedback and recovery are documented
in the [report reference](docs/docs-zh/report-quickstart.md).

Counts stay distinct: `va list` reports VA cases; `report list` and the report section of
`stats` describe RPTs; research metrics retain their original population. `list` includes
all metadata record kinds, not one deduplicated vulnerability total.
