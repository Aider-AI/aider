import pytest  # noqa: F401

from aider.run_cmd import run_cmd


def test_run_cmd_echo():
    command = "echo Hello, World!"
    exit_code, output = run_cmd(command)

    assert exit_code == 0
    assert output.strip() == "Hello, World!"


def test_run_cmd_strips_ansi_osc(capsys):
    command = "printf 'hello\\033[2Jworld\\033]8;;https://example.com\\007link\\n'"
    exit_code, output = run_cmd(command)

    assert exit_code == 0
    assert "\x1b" not in output
    assert output.strip() == "helloworldlink"
    assert "\x1b" not in capsys.readouterr().out
