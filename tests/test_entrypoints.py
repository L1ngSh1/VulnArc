import pytest

from vulnarc import compat


@pytest.mark.parametrize("option", [["--workspace", "/explicit"], ["-w", "/explicit"],
                                    ["--workspace=/explicit"], ["-w/explicit"]])
def test_shortcut_explicit_workspace_wins(monkeypatch, option):
    received = {}
    monkeypatch.setenv("VULNARC_WORKSPACE", "/environment")
    monkeypatch.setattr("sys.argv", ["va", "list", *option])
    monkeypatch.setattr(compat, "app", lambda **kw: received.update(kw))
    compat.main()
    assert received == {"args": ["va", "list", *option], "prog_name": "va"}


def test_shortcut_uses_workspace_environment(monkeypatch):
    received = {}
    monkeypatch.setenv("VULNARC_WORKSPACE", "/environment")
    monkeypatch.setattr("sys.argv", ["va", "check"])
    monkeypatch.setattr(compat, "app", lambda **kw: received.update(kw))
    compat.main()
    assert received["args"] == ["va", "check", "--workspace", "/environment"]


def test_shortcut_keeps_existing_default(monkeypatch):
    received = {}
    monkeypatch.delenv("VULNARC_WORKSPACE", raising=False)
    monkeypatch.setattr("sys.argv", ["va", "list"])
    monkeypatch.setattr(compat, "app", lambda **kw: received.update(kw))
    compat.main()
    assert received["args"][-1].endswith("/Workspace/Projects/My-github-projects/VulnArc-Research")


def test_shortcut_help_has_no_workspace_injection(monkeypatch):
    received = {}
    monkeypatch.setattr("sys.argv", ["va", "--help"])
    monkeypatch.setattr(compat, "app", lambda **kw: received.update(kw))
    compat.main()
    assert received["args"] == ["va", "--help"]
