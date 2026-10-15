import sys

import pytest  # noqa: F401

from aider.run_cmd import child_process_environ, run_cmd, run_cmd_subprocess


def test_child_process_environ_strips_provider_credentials(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant")
    monkeypatch.setenv("HF_TOKEN", "hf-test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "aws-secret")
    monkeypatch.setenv("AWS_BEDROCK_API_KEY", "aws-bedrock")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp-keep")
    monkeypatch.setenv("PATH", "/usr/bin")

    env = child_process_environ()

    assert "OPENAI_API_KEY" not in env
    assert "ANTHROPIC_API_KEY" not in env
    assert "HF_TOKEN" not in env
    assert "AWS_SECRET_ACCESS_KEY" not in env
    assert "AWS_BEDROCK_API_KEY" not in env
    assert env["GITHUB_TOKEN"] == "ghp-keep"
    assert env["PATH"] == "/usr/bin"


def test_run_cmd_echo():
    command = "echo Hello, World!"
    exit_code, output = run_cmd(command)

    assert exit_code == 0
    assert output.strip() == "Hello, World!"


def test_run_cmd_subprocess_hides_provider_api_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-secret")
    monkeypatch.setenv("GITHUB_TOKEN", "gh-visible")
    command = (
        sys.executable
        + " -c 'import os; print(\"KEY=\" + os.environ.get(\"OPENAI_API_KEY\", \"\")); "
        + "print(\"GH=\" + os.environ.get(\"GITHUB_TOKEN\", \"\"))'"
    )
    exit_code, output = run_cmd_subprocess(command)

    assert exit_code == 0
    assert "KEY=" in output
    assert "KEY=sk-secret" not in output
    assert "GH=gh-visible" in output
