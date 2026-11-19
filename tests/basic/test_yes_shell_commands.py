from unittest.mock import patch

from aider.coders import Coder
from aider.io import InputOutput
from aider.models import Model


def test_yes_always_still_denies_explicit_yes_by_default():
    io = InputOutput(pretty=False, yes=True)
    assert io.confirm_ask("Apply edit?") is True
    assert io.confirm_ask("Run shell command?", explicit_yes_required=True) is False


def test_yes_shell_commands_allows_explicit_yes_when_opted_in():
    io = InputOutput(pretty=False, yes=True, yes_shell_commands=True)
    assert io.confirm_ask("Run shell command?", explicit_yes_required=True) is True


def test_message_mode_reflects_shell_output_and_clears_commands_per_step(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    io = InputOutput(pretty=False, yes=True, yes_shell_commands=True)
    model = Model("gpt-4o")
    coder = Coder.create(main_model=model, io=io, use_git=False, suggest_shell_commands=True)

    responses = [
        "Let me inspect first.\n```bash\necho PROBE_OK_42\n```\n",
        "Inspection complete; no more commands needed.",
    ]
    seen_messages = []

    def fake_send(messages, **kwargs):
        seen_messages.append(list(messages))
        reply = responses.pop(0)
        coder.partial_response_content = reply
        coder.partial_response_function_call = dict()
        return []

    with patch.object(coder, "send", side_effect=fake_send):
        coder.run(with_message="Run probe and report")

    assert len(seen_messages) == 2
    assert any("PROBE_OK_42" in str(m.get("content", "")) for m in seen_messages[1])
    assert coder.shell_commands == []
