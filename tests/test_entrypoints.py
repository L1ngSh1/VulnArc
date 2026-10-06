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


@pytest.mark.parametrize('command', ['read', 'materials'])
@pytest.mark.parametrize('option', [["--workspace", "/explicit"], ["-w", "/explicit"],
                                    ["--workspace=/explicit"], ["-w/explicit"]])
def test_reading_shortcut_explicit_workspace_wins(monkeypatch, command, option):
    received = {}
    monkeypatch.setenv('VULNARC_WORKSPACE', '/environment')
    monkeypatch.setattr('sys.argv', ['va', command, 'VA-2026-0001', *option])
    monkeypatch.setattr(compat, 'app', lambda **kw: received.update(kw))
    compat.main()
    assert received['args'] == ['va', command, 'VA-2026-0001', *option]


@pytest.mark.parametrize('command', ['read', 'materials'])
@pytest.mark.parametrize('use_environment', [True, False])
def test_reading_shortcut_workspace_injection(monkeypatch, command, use_environment):
    received = {}
    if use_environment:
        monkeypatch.setenv('VULNARC_WORKSPACE', '/environment workspace')
    else:
        monkeypatch.delenv('VULNARC_WORKSPACE', raising=False)
    monkeypatch.setattr('sys.argv', ['va', command, 'VA-2026-0001'])
    monkeypatch.setattr(compat, 'app', lambda **kw: received.update(kw))
    compat.main()
    assert received['args'][:3] == ['va', command, 'VA-2026-0001']
    assert received['args'][-2] == '--workspace'
    if use_environment:
        assert received['args'][-1] == '/environment workspace'
    else:
        assert received['args'][-1].endswith(
            '/Workspace/Projects/My-github-projects/VulnArc-Research'
        )
