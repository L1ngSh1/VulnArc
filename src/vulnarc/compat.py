"""Compatibility shortcut: delegate to the installed CLI, never another source tree."""

import os
import sys
from pathlib import Path

from .cli import app


def main() -> None:
    args = sys.argv[1:]
    if args and args[0] in {"register", "show", "list", "check"}:
        explicit = any(
            arg in {"--workspace", "-w"}
            or arg.startswith("--workspace=")
            or (arg.startswith("-w") and len(arg) > 2)
            for arg in args
        )
        if not explicit:
            default = Path.home() / "Workspace/Projects/My-github-projects/VulnArc-Research"
            args += ["--workspace", os.environ.get("VULNARC_WORKSPACE", str(default))]
    app(args=["va", *args], prog_name="va")
