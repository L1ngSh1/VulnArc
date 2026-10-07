# VulnArc 🗂️
### Vulnerability Report Archive & Research Notes

[👉 中文版本 (Chinese Version)](docs/docs-zh/README.md)

![Python](https://img.shields.io/badge/Python-3.12%2B-blue)
![License](https://img.shields.io/badge/License-Apache--2.0-green)

---

## 📌 Project Introduction

**VulnArc** is a local archive for vulnerability reports and security research notes.
It brings reports, supporting evidence, submission records and learning notes together under a case ID such as **`VA-2026-0001`**.

A report often comes with several versions, a translation, attachments and follow-up records.
VulnArc keeps these materials connected so you can return to a case later, read the report and see where its conclusions came from.
It supports both your own research reports and case studies of published vulnerabilities.

The project currently supports:

- Registering existing reports and assigning local VA case IDs
- Recording CWE classifications, CVSS ratings and CVE/GHSA identifiers with their sources
- Reading primary reports and registered translations in the terminal
- Checking original materials against their recorded SHA-256 hashes
- Generating case cards, material indexes and timeline snapshots
- Keeping handwritten learning notes alongside each case

VA IDs belong to the local archive. Assigned external identifiers and historical references are recorded separately.
Registration does not submit a report to a vendor or assign a CVE.

---

## 🧩 How It Works

```text
Existing report and supporting materials
│
▼
Reviewed intake JSON
│
▼
Preview → Confirm registration
│
▼
VA-YYYY-NNNN
│
├── Case overview
├── Primary report / Translation
├── Material paths and integrity checks
└── Timeline snapshot and learning notes
```

Records use **YAML + Markdown** rather than a database. Structured fields and history live in `metadata.yaml`;
notes and case documents remain readable in a text editor.
Original reports stay in place and are referenced by path and hash.

A registered case contains:

```text
VA-2026-0001/
├── metadata.yaml    # Structured facts, material references and history
├── case.md          # Case card
├── materials.md     # Material index
├── timeline.md      # Timeline snapshot
└── learning.md      # Handwritten learning notes
```

The case card, material index and timeline are registration snapshots.
The CLI reads current metadata when showing a case or checking its materials.
Private case archives should live outside the public code repository.

---

## ⚡ Quick Start

### Install

VulnArc requires **Python 3.12+**. Follow the [installation guide](docs/installation.md) to build and install the CLI.

```bash
vulnarc --help
```

### Register a report

For a first run, use the [complete example](docs/va-intake-example.md): it creates a fictional report and a working intake JSON.
For your own materials, review the intake before registering it.

Replace the paths below with your private workspace and intake file. Preview first:

```bash
WS="/absolute/path/to/VulnArc-Research"
vulnarc va register /absolute/path/to/intake.json --workspace "$WS"
```

Then confirm the registration:

```bash
vulnarc va register /absolute/path/to/intake.json --workspace "$WS" --apply
```

The receipt shows the assigned VA ID. Repeating an identical intake reuses that ID and preserves your notes.

### Read and revisit a case

Use the ID from the receipt; `VA-2026-0001` is an example.

```bash
vulnarc va list --workspace "$WS"
vulnarc va show VA-2026-0001 --workspace "$WS"
vulnarc va read VA-2026-0001 --workspace "$WS"
vulnarc va read VA-2026-0001 --report translation --workspace "$WS"
```

Terminal output formats headings, paragraphs, tables and code blocks.
Use `--raw` for plain-text reading; translation requires a registered translation file.

To locate and check the supporting materials:

```bash
vulnarc va materials VA-2026-0001 --workspace "$WS"
vulnarc va check --workspace "$WS"
```

`show` displays an overview; `read` verifies the selected report; `materials` checks each listed original.
Moving or changing an original file requires updating the archive's references through a reviewed maintenance process.
See the [VA guide](docs/va-quickstart.md) for details.

---

## 📂 Project Structure

```text
VulnArc/
├── src/vulnarc/      # CLI and application logic
│   ├── va.py        # Case registration and VA commands
│   ├── reading.py   # Report selection and verified text reading
│   ├── display.py   # Terminal report layout
│   ├── materials.py # Shared material verification
│   ├── models.py    # Record models
│   └── storage.py   # Workspace storage
├── schemas/         # Exported record schemas
├── templates/       # Research document templates
├── tests/           # Automated tests
├── docs/            # Usage guides and design notes
└── pyproject.toml   # Package and dependency configuration
```

The repository also retains hypothesis/experiment workflows and existing RPT record maintenance.
These are separate from the VA archive workflow; see [research workflow](docs/research-workflow.md)
and [RPT maintenance](docs/docs-zh/report-quickstart.md).

---

## 🛠️ Development Status

Report registration, terminal reading and material verification are implemented.
The next interface under consideration is a **keyboard-driven terminal workbench**:
a case list beside a reading pane, with views for the overview, report, translation and materials.

The workbench is currently a [design proposal](docs/workbench-design.md), not a shipped feature.
Search, interactive intake and VA update commands remain future work.

---

## 📖 Documentation

- [Installation](docs/installation.md)
- [First intake example](docs/va-intake-example.md)
- [VA usage guide](docs/va-quickstart.md)
- [Record and material maintenance](docs/maintenance.md)
- [Architecture](docs/architecture.md) · [Workspace model](docs/workspace-model.md)
- [Contributing](CONTRIBUTING.md) · [Disclosure](DISCLOSURE.md)

## 📄 License

VulnArc is licensed under [Apache-2.0](LICENSE).
