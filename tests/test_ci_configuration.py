"""Offline checks for the CI contract; no advisory services or credentials needed."""

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def config(path):
    # YAML 1.1 SafeLoader treats GitHub's `on` key as boolean True.
    return yaml.load((ROOT / path).read_text(), Loader=yaml.BaseLoader)


def test_ci_runs_for_pr_main_manual_and_weekly():
    workflow = config(".github/workflows/ci.yml")
    assert set(workflow["on"]) == {"push", "pull_request", "workflow_dispatch", "schedule"}
    assert workflow["on"]["push"]["branches"] == ["main"]
    assert workflow["on"]["schedule"][0]["cron"] == "17 1 * * 1"
    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["concurrency"]["cancel-in-progress"] == "true"


@pytest.mark.parametrize("job_name", ["quality", "dependency-audit"])
def test_ci_jobs_have_bounded_read_only_pinned_actions(job_name):
    job = config(".github/workflows/ci.yml")["jobs"][job_name]
    assert 0 < int(job["timeout-minutes"]) <= 15
    assert "permissions" not in job
    assert "continue-on-error" not in job
    for step in job["steps"]:
        assert "continue-on-error" not in step
        if "uses" in step:
            assert re.fullmatch(r"actions/(checkout|setup-python)@[a-f0-9]{40}", step["uses"])
            if step["uses"].startswith("actions/checkout@"):
                assert step["with"]["persist-credentials"] == "false"


def test_audit_checks_locked_versions_without_ignoring_failures():
    steps = config(".github/workflows/ci.yml")["jobs"]["dependency-audit"]["steps"]
    commands = "\n".join(step.get("run", "") for step in steps)
    for flag in ["uv export --locked", "--extra dev", "--no-emit-project", "--require-hashes",
                 "--disable-pip", "--strict"]:
        assert flag in commands
    for bypass in ["--ignore-vuln", "|| true", "--fix"]:
        assert bypass not in commands


def test_quality_uses_lock_and_independent_wheel():
    steps = config(".github/workflows/ci.yml")["jobs"]["quality"]["steps"]
    commands = "\n".join(step.get("run", "") for step in steps)
    for expected in ["uv sync --locked --extra dev", "--no-sync", "site-packages",
                     "env -u PYTHONPATH", "-o pythonpath=", "cp -R tests schemas .github"]:
        assert expected in commands


def test_dependabot_updates_project_tools_and_actions():
    updates = config(".github/dependabot.yml")["updates"]
    assert {(u["package-ecosystem"], u["directory"]) for u in updates} == {
        ("uv", "/"), ("pip", "/.github"), ("github-actions", "/"),
    }
    for update in updates:
        assert update["schedule"]["interval"] == "weekly"
        assert update["schedule"]["timezone"] == "Asia/Shanghai"
        assert int(update["open-pull-requests-limit"]) <= 3


def test_ci_tool_versions_are_exact_pins():
    lines = (ROOT / ".github/requirements.txt").read_text().splitlines()
    pins = [line for line in lines if line and not line.startswith("#")]
    assert {line.split("==")[0] for line in pins} == {"uv", "pip-audit"}
    assert all(re.fullmatch(r"[a-z-]+==\d+\.\d+\.\d+", line) for line in pins)
