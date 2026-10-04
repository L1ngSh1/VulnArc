"""The same templates work from source checkouts and installed wheels."""

from importlib.resources import files
from pathlib import Path


def template_text(name: str) -> str:
    bundled = files("vulnarc").joinpath("templates", name)
    if bundled.is_file():
        return bundled.read_text(encoding="utf-8")
    return (Path(__file__).parents[2] / "templates" / name).read_text(encoding="utf-8")
