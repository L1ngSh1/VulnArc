# Architecture

VulnArc is repo-first: Markdown is the durable reasoning record and YAML is structured metadata. Pydantic validates records, storage traverses `metadata.yaml`, lifecycle code enforces explicit transitions, and Typer exposes thin commands. There is no database, scanner, agent framework, model API, or publishing integration.
