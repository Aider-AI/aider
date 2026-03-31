import pytest  # noqa: F401

from aider.run_cmd import run_cmd, run_cmd_subprocess


def test_run_cmd_echo():
    command = "echo Hello, World!"
    exit_code, output = run_cmd(command)

    assert exit_code == 0
    assert output.strip() == "Hello, World!"


def test_run_cmd_subprocess_preserves_commas_in_powershell(monkeypatch):
    monkeypatch.setattr("aider.run_cmd.platform.system", lambda: "Windows")
    monkeypatch.setattr(
        "aider.run_cmd.get_windows_parent_process_name", lambda: "powershell.exe"
    )

    exit_code, output = run_cmd_subprocess("echo Hello, World!")

    assert exit_code == 0
    assert output.strip() == "Hello, World!"
