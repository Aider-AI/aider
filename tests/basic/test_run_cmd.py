import pytest

from aider.run_cmd import run_cmd


def test_run_cmd_echo():
    command = "echo Hello, World!"
    exit_code, output = run_cmd(command)

    assert exit_code == 0
    assert output.strip() == "Hello, World!"


def test_run_cmd_echo_with_quotes():
    command = 'echo "Hello, World!"'
    exit_code, output = run_cmd(command)

    assert exit_code == 0
    assert output.strip() == "Hello, World!"


def test_run_cmd_invalid_command():
    command = "invalid_command_that_does_not_exist"
    exit_code, output = run_cmd(command)

    assert exit_code != 0
    assert "command not found" in output.lower() or "is not recognized" in output.lower()
