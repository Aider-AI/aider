import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from aider.args import get_parser
from aider.coders import Coder
from aider.io import InputOutput
from aider.models import Model


def test_events_jsonl_arg_parsing():
    parser = get_parser([], None)
    args_default = parser.parse_args([])
    assert args_default.events_jsonl is None

    args_set = parser.parse_args(["--events-jsonl", "logs/events.jsonl"])
    assert args_set.events_jsonl == "logs/events.jsonl"


def test_llm_response_emits_exact_integer_tokens(tmp_path):
    events_path = tmp_path / "telemetry" / "events.jsonl"
    io = InputOutput(yes=True)
    model = Model("gpt-4o")
    coder = Coder.create(
        main_model=model,
        io=io,
        use_git=False,
        events_jsonl_file=str(events_path),
    )

    usage = SimpleNamespace(
        prompt_tokens=3142,
        completion_tokens=1427,
        prompt_cache_hit_tokens=128,
        cache_creation_input_tokens=64,
    )
    completion = SimpleNamespace(usage=usage)

    coder.calculate_and_show_tokens_and_cost([], completion=completion)

    lines = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
    assert len(lines) == 1
    ev = lines[0]
    assert ev["type"] == "llm_response"
    assert ev["model"] == model.name
    assert ev["prompt_tokens"] == 3142
    assert ev["completion_tokens"] == 1427
    assert ev["cache_hit_tokens"] == 128
    assert ev["cache_write_tokens"] == 64
    assert ev["message_tokens_sent"] == 3206
    assert ev["message_tokens_received"] == 1427
    assert isinstance(ev["prompt_tokens"], int)
    assert isinstance(ev["completion_tokens"], int)
    assert "3.2k" in coder.usage_report


def test_llm_response_emits_when_model_has_no_cost_info(tmp_path):
    events_path = tmp_path / "events_nocost.jsonl"
    io = InputOutput(yes=True)
    model = Model("unknown/custom-local-model")
    model.info = {}
    coder = Coder.create(
        main_model=model,
        io=io,
        use_git=False,
        events_jsonl_file=str(events_path),
    )

    usage = SimpleNamespace(prompt_tokens=512, completion_tokens=99)
    completion = SimpleNamespace(usage=usage)
    coder.calculate_and_show_tokens_and_cost([], completion=completion)

    lines = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
    assert len(lines) == 1
    assert lines[0]["type"] == "llm_response"
    assert lines[0]["prompt_tokens"] == 512
    assert lines[0]["completion_tokens"] == 99
    assert lines[0]["cost"] == 0.0


def test_file_edits_and_shell_command_events(tmp_path):
    events_path = tmp_path / "events_actions.jsonl"
    io = InputOutput(yes=True)
    io.confirm_ask = MagicMock(return_value=True)
    coder = Coder.create(
        main_model=Model("gpt-4o"),
        io=io,
        use_git=False,
        events_jsonl_file=str(events_path),
    )

    coder.get_edits = MagicMock(return_value=[("b.py",), ("a.py",)])
    coder.apply_edits_dry_run = MagicMock(side_effect=lambda edits: edits)
    coder.prepare_to_edit = MagicMock(side_effect=lambda edits: edits)
    coder.apply_edits = MagicMock()

    edited = coder.apply_updates()
    assert edited == {"a.py", "b.py"}

    with patch("aider.coders.base_coder.run_cmd", return_value=(13, "permission denied")):
        coder.handle_shell_commands("echo hi\n", group=None)

    lines = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
    assert [ev["type"] for ev in lines] == ["file_edits", "shell_command"]
    assert lines[0]["files"] == ["a.py", "b.py"]
    assert lines[0]["dry_run"] is False
    assert lines[1]["command"] == "echo hi"
    assert lines[1]["exit_status"] == 13
    assert lines[1]["output_chars"] == len("permission denied")


def test_no_file_created_when_events_jsonl_disabled(tmp_path):
    io = InputOutput(yes=True)
    coder = Coder.create(main_model=Model("gpt-4o"), io=io, use_git=False)
    usage = SimpleNamespace(prompt_tokens=10, completion_tokens=5)
    coder.calculate_and_show_tokens_and_cost([], completion=SimpleNamespace(usage=usage))
    assert list(tmp_path.iterdir()) == []
