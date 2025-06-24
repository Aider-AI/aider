import pytest  # noqa: F401

from aider.run_cmd import run_cmd


def test_run_cmd_echo():
    # echo can work the same in both Linux and Windows if only echoing one word
    command = "echo Hello!"
    exit_code, output = run_cmd(command)

    assert exit_code == 0
    assert output.strip() == "Hello!"
