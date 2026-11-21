import json
import os
from unittest.mock import MagicMock, patch

import pytest

from aider import batch


@pytest.fixture
def io():
    io = MagicMock()
    io.tool_output = lambda *a, **k: None
    io.tool_error = lambda *a, **k: None
    io.tool_warning = lambda *a, **k: None
    return io


@pytest.fixture
def model():
    m = MagicMock()
    m.name = "gpt-4o-mini"
    m.info = MagicMock()
    m.token_count = lambda messages: sum(len(x.get("content") or "") for x in messages) // 4
    return m


def _write_plan(tmp_path, items, **extra):
    plan = {"items": items, **extra}
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan))
    return path


def _msg(text):
    return [{"role": "user", "content": text}]


class TestLoadPlan:
    def test_rejects_missing_file(self, tmp_path):
        with pytest.raises(batch.BatchError, match="not found"):
            batch.load_plan(tmp_path / "nope.json", tmp_path)

    def test_rejects_empty_items(self, tmp_path):
        path = _write_plan(tmp_path, [])
        with pytest.raises(batch.BatchError, match="non-empty 'items'"):
            batch.load_plan(path, tmp_path)

    def test_defaults_item_ids(self, tmp_path):
        path = _write_plan(tmp_path, [{"prompt": "do x"}])
        plan = batch.load_plan(path, tmp_path)
        assert plan["items"][0]["id"] == "item-1"

    def test_rejects_target_outside_project(self, tmp_path):
        path = _write_plan(tmp_path, [{"prompt": "x", "targets": ["../escape.py"]}])
        with pytest.raises(batch.BatchError, match="outside the project"):
            batch.load_plan(path, tmp_path)

    def test_rejects_hidden_target(self, tmp_path):
        path = _write_plan(tmp_path, [{"prompt": "x", "targets": [".secret/key.pem"]}])
        with pytest.raises(batch.BatchError, match="hidden"):
            batch.load_plan(path, tmp_path)

    def test_accepts_in_project_target(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "app.py").write_text("print(1)")
        path = _write_plan(tmp_path, [{"prompt": "x", "targets": ["src/app.py"]}])
        plan = batch.load_plan(path, tmp_path)
        assert str(plan["items"][0]["targets"][0]) == os.path.join("src", "app.py")


class TestSnapshot:
    def test_stable_snapshot(self, tmp_path):
        (tmp_path / "a.py").write_text("x = 1")
        path = _write_plan(tmp_path, [{"prompt": "p", "targets": ["a.py"]}])
        plan = batch.load_plan(path, tmp_path)
        s1 = batch.plan_snapshot(plan, {"model": "m"})
        s2 = batch.plan_snapshot(plan, {"model": "m"})
        assert s1 == s2 and len(s1) == 16

    def test_snapshot_changes_when_source_changes(self, tmp_path):
        src = tmp_path / "a.py"
        src.write_text("x = 1")
        path = _write_plan(tmp_path, [{"prompt": "p", "targets": ["a.py"]}])
        plan = batch.load_plan(path, tmp_path)
        s1 = batch.plan_snapshot(plan, {"model": "m"})
        src.write_text("x = 2")
        assert batch.plan_snapshot(plan, {"model": "m"}) != s1

    def test_snapshot_changes_when_settings_change(self, tmp_path):
        path = _write_plan(tmp_path, [{"prompt": "p"}])
        plan = batch.load_plan(path, tmp_path)
        assert batch.plan_snapshot(plan, {"model": "a"}) != batch.plan_snapshot(plan, {"model": "b"})


class TestCheck:
    def test_fails_without_api_key(self, model, io):
        with patch.dict(os.environ, {}, clear=True):
            assert batch.check(model, io) is False

    def test_passes_with_key(self, model, io):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=True):
            assert batch.check(model, io) is True

    def test_warns_on_unverified_base(self, model, io):
        env = {"OPENAI_API_KEY": "sk", "OPENAI_API_BASE": "https://example.invalid"}
        with patch.dict(os.environ, env, clear=True):
            assert batch.check(model, io) is False


class TestRun:
    def test_expect_mismatch_refuses_before_upload(self, tmp_path, model, io):
        path = _write_plan(tmp_path, [{"prompt": "p"}])
        plan = batch.load_plan(path, tmp_path)
        with pytest.raises(batch.BatchError, match="does not match"):
            batch.run(plan, model, io, expect="deadbeefdeadbeef", yes=True)

    def test_no_expect_requires_yes(self, tmp_path, model, io):
        path = _write_plan(tmp_path, [{"prompt": "p"}])
        plan = batch.load_plan(path, tmp_path)
        with pytest.raises(batch.BatchError, match="--batch-expect"):
            batch.run(plan, model, io)

    def test_submit_creates_task_record(self, tmp_path, model, io):
        (tmp_path / "a.py").write_text("print('hi')")
        path = _write_plan(
            tmp_path,
            [{"id": "doc-a", "prompt": "document it", "targets": ["a.py"]}],
        )
        plan = batch.load_plan(path, tmp_path)
        snapshot = batch.plan_snapshot(plan, {"model": model.name, "plan": "plan.json"})

        uploaded = MagicMock(id="file-1")
        batch_obj = MagicMock(id="batch_abc", status="validating")
        client = MagicMock()
        client.files.create.return_value = uploaded
        client.batches.create.return_value = batch_obj

        env = {"OPENAI_API_KEY": "sk-test"}
        with patch.dict(os.environ, env, clear=True):
            with patch("aider.batch._openai_client", return_value=client):
                record = batch.run(plan, model, io, expect=snapshot)

        assert record["batch_id"] == "batch_abc"
        assert record["items"][0]["id"] == "doc-a"
        assert record["sources"]["a.py"]["exists"] is True

        # Task record persisted under .aider/batch with owner-only perms
        task_path = tmp_path / ".aider" / "batch" / f"{record['task_id']}.json"
        assert task_path.is_file()
        if os.name != "nt":
            assert task_path.stat().st_mode & 0o777 == 0o600

        # The request file carries one JSONL entry per item
        requests = (tmp_path / ".aider" / "batch" / "requests.jsonl").read_text().strip()
        assert json.loads(requests)["custom_id"] == "doc-a"

    def test_target_content_inlined_into_request(self, tmp_path, model, io):
        (tmp_path / "a.py").write_text("SECRET_BODY = 42")
        path = _write_plan(tmp_path, [{"id": "i", "prompt": "p", "targets": ["a.py"]}])
        plan = batch.load_plan(path, tmp_path)
        messages = batch._item_messages(plan["items"][0], tmp_path)
        assert "SECRET_BODY = 42" in messages[0]["content"]


class TestCollect:
    def _task(self, tmp_path):
        src = tmp_path / "a.py"
        src.write_text("x = 1")
        task_dir = tmp_path / ".aider" / "batch"
        task_dir.mkdir(parents=True)
        record = {
            "task_id": "batch-1",
            "batch_id": "batch_abc",
            "model": "gpt-4o-mini",
            "snapshot": "x",
            "created_at": 0,
            "items": [
                {"id": "one", "targets": ["a.py"]},
                {"id": "two", "targets": []},
            ],
            "sources": {
                "a.py": batch._source_fingerprints(tmp_path, ["a.py"])["a.py"],
            },
            "status": "in_progress",
        }
        (task_dir / "batch-1.json").write_text(json.dumps(record))
        return record

    def test_collect_reports_delivered(self, tmp_path, io):
        record = self._task(tmp_path)

        batch_obj = MagicMock(status="completed", output_file_id="of-1")
        response_body = {
            "choices": [{"message": {"content": "done: added docstring"}}],
        }
        result_line = json.dumps({"custom_id": "one", "response": {"body": response_body}}) + "\n"
        result_line += json.dumps({"custom_id": "two", "error": {"code": "x"}})

        client = MagicMock()
        client.batches.retrieve.return_value = batch_obj
        client.files.content.return_value = MagicMock(content=result_line.encode())

        with patch("aider.batch._openai_client", return_value=client):
            out = batch.collect(tmp_path, record["task_id"], io)

        assert out["summary"] == {"delivered": 1, "held": 0, "failed": 1}
        assert (tmp_path / ".aider" / "batch" / "batch-1-one.md").read_text() == "done: added docstring"

    def test_collect_holds_when_source_changed(self, tmp_path, io):
        record = self._task(tmp_path)
        (tmp_path / "a.py").write_text("x = 2")  # source changed since submit

        batch_obj = MagicMock(status="completed", output_file_id="of-1")
        result_line = json.dumps(
            {"custom_id": "one", "response": {"body": {"choices": [{"message": {"content": "ok"}}]}}}
        )
        client = MagicMock()
        client.batches.retrieve.return_value = batch_obj
        client.files.content.return_value = MagicMock(content=result_line.encode())

        with patch("aider.batch._openai_client", return_value=client):
            out = batch.collect(tmp_path, record["task_id"], io)

        assert out["summary"]["held"] == 1
        assert not (tmp_path / ".aider" / "batch" / "batch-1-one.md").exists()

    def test_collect_still_running(self, tmp_path, io):
        record = self._task(tmp_path)
        batch_obj = MagicMock(status="in_progress")
        client = MagicMock()
        client.batches.retrieve.return_value = batch_obj

        with patch("aider.batch._openai_client", return_value=client):
            out = batch.collect(tmp_path, record["task_id"], io)

        assert out["status"] == "in_progress"


class TestPreview:
    def test_preview_uploads_nothing(self, tmp_path, model, io):
        path = _write_plan(tmp_path, [{"prompt": "p", "targets": []}])
        plan = batch.load_plan(path, tmp_path)
        snapshot = batch.preview(plan, model, io)
        assert len(snapshot) == 16
