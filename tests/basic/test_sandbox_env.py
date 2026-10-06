import os

import pytest

from aider.run_cmd import (
    SANDBOX_ENV_BASE_KEYS,
    SANDBOX_MODE,
    child_process_environ,
    run_cmd,
    set_sandbox_mode,
)


@pytest.fixture(autouse=True)
def _restore_sandbox_mode():
    saved = SANDBOX_MODE
    set_sandbox_mode(False)
    yield
    set_sandbox_mode(saved)


SANDBOX_BASE = {
    "PATH": "/usr/bin",
    "HOME": "/tmp/home",
    "SHELL": "/bin/sh",
    "LANG": "en_US.UTF-8",
    "LC_ALL": "en_US.UTF-8",
    "MY_CUSTOM_GATEWAY": "arbitrary-env-secret-value",
    "OPENAI_API_KEY": "arbitrary-env-secret-value",
    "MY_APP_TOKEN": "some-build-token-value",
    "BUILD_TOOL_HOST": "https://example.invalid",
}


def test_default_mode_inherits_full_environment():
    """Without --sandbox behavior is unchanged: the full env is inherited."""
    env = child_process_environ(base=dict(SANDBOX_BASE))
    assert env["PATH"] == "/usr/bin"
    assert env["MY_CUSTOM_GATEWAY"] == "arbitrary-env-secret-value"
    assert env["MY_APP_TOKEN"] == "some-build-token-value"
    assert env["BUILD_TOOL_HOST"] == "https://example.invalid"


def test_sandbox_keeps_minimal_base_and_locale():
    env = child_process_environ(base=dict(SANDBOX_BASE), sandbox=True)
    for key in ("PATH", "HOME", "SHELL", "LANG", "LC_ALL"):
        assert env[key] == SANDBOX_BASE[key]
    # Every surviving key belongs to the minimal base/locale set.
    for key in env:
        upper = key.upper()
        assert upper in SANDBOX_ENV_BASE_KEYS or upper == "LANGUAGE" or upper.startswith("LC_")


def test_sandbox_drops_arbitrary_name_and_business_vars():
    """Issue #5658 / PR #5692 gap: arbitrary .env names must not leak."""
    env = child_process_environ(base=dict(SANDBOX_BASE), sandbox=True)
    for key in (
        "MY_CUSTOM_GATEWAY",
        "OPENAI_API_KEY",
        "MY_APP_TOKEN",
        "BUILD_TOOL_HOST",
    ):
        assert key not in env


def test_sandbox_global_flag_matches_explicit_argument():
    set_sandbox_mode(True)
    env = child_process_environ(base=dict(SANDBOX_BASE))
    assert "MY_CUSTOM_GATEWAY" not in env
    # Explicit sandbox=False overrides the global flag.
    env = child_process_environ(base=dict(SANDBOX_BASE), sandbox=False)
    assert env["MY_CUSTOM_GATEWAY"] == "arbitrary-env-secret-value"


def test_sandbox_git_profile_keeps_git_and_ssh_vars():
    base = {
        "PATH": "/usr/bin",
        "GIT_CONFIG_GLOBAL": "/tmp/gitconfig",
        "SSH_AUTH_SOCK": "/tmp/ssh",
        "MY_CUSTOM_GATEWAY": "arbitrary-env-secret-value",
    }
    env = child_process_environ(base=base, profile="git", sandbox=True)
    assert env["GIT_CONFIG_GLOBAL"] == "/tmp/gitconfig"
    assert env["SSH_AUTH_SOCK"] == "/tmp/ssh"
    assert "MY_CUSTOM_GATEWAY" not in env


def test_sandbox_run_profile_does_not_keep_git_vars():
    base = {"PATH": "/usr/bin", "GIT_CONFIG_GLOBAL": "/tmp/gitconfig"}
    env = child_process_environ(base=base, sandbox=True)
    assert "GIT_CONFIG_GLOBAL" not in env


def test_extra_overlays_are_applied():
    env = child_process_environ(
        base=dict(SANDBOX_BASE), extra={"GIT_EDITOR": "true"}, profile="git", sandbox=True
    )
    assert env["GIT_EDITOR"] == "true"


def test_run_cmd_subprocess_sandbox_does_not_expose_arbitrary_var(monkeypatch):
    sentinel = "arbitrary-env-secret-value"
    monkeypatch.setenv("MY_CUSTOM_GATEWAY", sentinel)
    monkeypatch.setattr("aider.run_cmd.sys.stdin.isatty", lambda: False)
    set_sandbox_mode(True)
    if os.name == "nt":
        command = (
            "python -c \"import os,sys; sys.exit(0 if os.environ.get('MY_CUSTOM_GATEWAY') else 1)\""
        )
    else:
        command = 'test -n "$MY_CUSTOM_GATEWAY"'
    exit_code, _output = run_cmd(command)
    assert exit_code != 0


def test_run_cmd_subprocess_default_mode_exposes_arbitrary_var(monkeypatch):
    monkeypatch.setattr("aider.run_cmd.sys.stdin.isatty", lambda: False)
    if os.name == "nt":
        command = "python -c \"import os; os.environ.get('PATH') or exit(1)\""
    else:
        command = 'test -n "$PATH"'
    exit_code, _output = run_cmd(command)
    assert exit_code == 0
