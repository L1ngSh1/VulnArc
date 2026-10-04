# Architecture

VulnArc is repo-first: Markdown is the durable reasoning record and YAML is structured metadata. Pydantic validates records, storage traverses `metadata.yaml`, lifecycle code enforces explicit transitions, and Typer exposes thin commands. There is no database, scanner, agent framework, model API, or publishing integration.

## Existing-report registration and local transactions

Reports use independent submission and processing enums, optional material references, and
append-only `history` events in the same metadata file. Local writes use `.vulnarc/write.lock`
(`fcntl`, POSIX single-host), staged directory creation, atomic metadata replacement, optimistic
SHA-256 comparison and guarded byte backups. Recovery requires the exact post-write hash.
Dated historical feedback does not move current state backwards; corrections append events.
`report import-inventory` is restricted to the 2026-10-01 inventory, defaults to a zero-write
preview, and applies each record separately. Report counts never enter research validation rates.

## VA archives and shared material validation

VA cases and RPT reports remain independent; see the [maintenance contract](maintenance.md).
`materials.py` owns shared path, SHA-256 and evidence-line checks without Typer dependencies.
Storage calls that module directly, not the VA CLI. Report's relative paths/optional hashes
and VA's absolute paths/required hashes remain distinct. Registration documents are snapshots;
handwritten learning notes are preserved. See [installation](installation.md) for the single
maintained source and installed command; dated delivery directories are historical only.
