import inspect
import textwrap
from pathlib import Path

from aider.macro_runner import MacroSecurityError, run_macro
import pytest # Added import for pytest

def test_plain_function(tmp_path, mocker):
    code = """
def main(ctx, **kw):
    ctx['io'].tool_comment('plain macro ran')
"""
    macro = tmp_path / "plain.py"
    macro.write_text(textwrap.dedent(code))

    dummy_ctx = {"io": mocker.Mock(), "coder": mocker.Mock(), "commands": mocker.Mock()}
    run_macro(macro, dummy_ctx)

    dummy_ctx["io"].tool_comment.assert_called_once_with("plain macro ran")


def test_generator_round_trip(tmp_path, mocker):
    code = '''
def main(ctx, **kw):
    answer = yield "/echo hi"
    ctx["io"].tool_comment(f"round‑trip → {answer}")
'''
    macro = tmp_path / "gen.py"
    macro.write_text(textwrap.dedent(code))

    dummy_ctx = {
        "io": mocker.Mock(),
        "coder": mocker.Mock(),
        "commands": mocker.Mock(process_user_message=lambda s: s.upper()),
    }
    run_macro(macro, dummy_ctx)

    dummy_ctx["io"].tool_comment.assert_called_with("round‑trip → /ECHO HI")


def test_allow_list(tmp_path, monkeypatch):
    macro = tmp_path / "blocked.py"
    macro.write_text("def main(ctx): pass")

    allow = tmp_path / "macro.allowlist"
    allow.write_text("")  # empty list blocks everything
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

    with pytest.raises(MacroSecurityError):
        run_macro(macro, {"io": None, "coder": None, "commands": None})
