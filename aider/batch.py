"""Opt-in batch mode for bulk, independent single-turn tasks via provider Batch APIs.

Batch requests run asynchronously at roughly half the realtime price, with a
completion window of up to 24 hours. Batch only wins over normal chat when
little of each request shares a cached prefix — normal chat turns are never
routed through this subsystem; it is only reachable via the explicit
`--batch-*` flags.

Commands (as flags, following aider's CLI conventions):

    aider --batch-check                        verify setup; nothing is billed
    aider --batch-run plan.json --batch-dry-run
                                                preview items + token estimate,
                                                print a snapshot hash, upload nothing
    aider --batch-run plan.json --batch-expect <snapshot>
                                                submit only if plan, sources and
                                                settings still match the preview
    aider --batch-collect <task-id> [--batch-wait]
                                                reconcile results; never auto-retry
                                                billed items

Plan file format (`plan.json`):

    {
      "model": "gpt-4o-mini",            // optional; falls back to --model
      "items": [
        {
          "id": "rename-config",          // optional; defaults to item-<n>
          "prompt": "Rename the setting to ...",
          "targets": ["src/config.py"],   // optional; files whose current
                                          // content is inlined into the request
          "messages": [                   // optional; overrides prompt
            {"role": "user", "content": "..."}
          ]
        }
      ]
    }

Task records live under `.aider/batch/` in the project (owner-only
permissions); results can land hours after approval, so targets are restricted
to in-project, non-hidden paths and every task records a snapshot hash of the
plan, the referenced source files, and the resolved settings.
"""

import hashlib
import json
import os
import stat
import time
from pathlib import Path

BATCH_DIR = ".aider/batch"
BATCH_COMPLETION_WINDOW = "24h"
BATCH_ENDPOINT = "/v1/chat/completions"

# Providers accepted for v1: OpenAI and any OpenAI-compatible endpoint that
# follows the files+batches API shape. Everything else fails check().
SUPPORTED_API_BASES = (
    "https://api.openai.com",
    "https://api.deepseek.com",
)


class BatchError(Exception):
    pass


def _plan_path(path):
    plan_path = Path(path)
    if not plan_path.is_file():
        raise BatchError(f"Plan file not found: {path}")
    return plan_path


def load_plan(path, git_root):
    """Parse and validate the plan file. Returns a normalized plan dict."""
    plan_path = _plan_path(path)
    try:
        plan = json.loads(plan_path.read_text())
    except (OSError, json.JSONDecodeError) as err:
        raise BatchError(f"Unable to parse plan file {path}: {err}")

    if not isinstance(plan, dict):
        raise BatchError("Plan file must be a JSON object")
    items = plan.get("items")
    if not isinstance(items, list) or not items:
        raise BatchError("Plan file must contain a non-empty 'items' list")

    root = Path(git_root).resolve() if git_root else Path.cwd().resolve()
    normalized = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise BatchError(f"Item #{index} must be a JSON object")
        item_id = item.get("id") or f"item-{index + 1}"
        if not isinstance(item_id, str) or not item_id.strip():
            raise BatchError(f"Item #{index} has an invalid 'id'")
        messages = item.get("messages")
        prompt = item.get("prompt")
        if not messages and not isinstance(prompt, str):
            raise BatchError(f"Item '{item_id}' needs a 'prompt' or 'messages'")
        if messages is not None and not (
            isinstance(messages, list)
            and all(isinstance(m, dict) and "role" in m and "content" in m for m in messages)
        ):
            raise BatchError(f"Item '{item_id}' has malformed 'messages'")

        targets = item.get("targets") or []
        if not isinstance(targets, list):
            raise BatchError(f"Item '{item_id}' has malformed 'targets'")
        resolved_targets = []
        for target in targets:
            resolved_targets.append(_validate_target(target, root))

        normalized.append(
            {
                "id": item_id.strip(),
                "prompt": prompt,
                "messages": messages,
                "targets": resolved_targets,
            }
        )

    return {
        "model": plan.get("model"),
        "items": normalized,
        "plan_path": plan_path,
        "root": root,
    }


def _validate_target(target, root):
    """Targets must resolve inside the project to non-hidden paths."""
    if not isinstance(target, str) or not target.strip():
        raise BatchError("Target paths must be non-empty strings")
    resolved = (root / target).resolve()
    try:
        relative = resolved.relative_to(root)
    except ValueError:
        raise BatchError(f"Target '{target}' resolves outside the project")
    if any(part.startswith(".") for part in relative.parts):
        raise BatchError(f"Target '{target}' points into a hidden path")
    return relative


def _source_fingerprints(root, relative_targets):
    """Hash each referenced source file's current content."""
    fingerprints = {}
    for relative in relative_targets:
        path = root / relative
        try:
            content = path.read_bytes()
        except OSError:
            fingerprints[str(relative)] = {"exists": False, "sha256": None}
            continue
        fingerprints[str(relative)] = {
            "exists": True,
            "sha256": hashlib.sha256(content).hexdigest(),
        }
    return fingerprints


def plan_snapshot(plan, settings):
    """Stable hash over the plan, the referenced source files and the resolved
    settings. This is the value --batch-dry-run prints and --batch-expect
    requires to match before anything is submitted."""
    all_targets = sorted({str(t) for item in plan["items"] for t in item["targets"]})
    fingerprint = {
        "settings": settings,
        "items": [
            {
                "id": item["id"],
                "prompt": item["prompt"],
                "messages": item["messages"],
                "targets": [str(t) for t in item["targets"]],
            }
            for item in plan["items"]
        ],
        "sources": _source_fingerprints(plan["root"], all_targets),
    }
    encoded = json.dumps(fingerprint, sort_keys=True).encode()
    return hashlib.sha256(encoded).hexdigest()[:16]


def _item_messages(item, root):
    if item["messages"]:
        return item["messages"]
    parts = [item["prompt"]]
    for relative in item["targets"]:
        path = root / relative
        try:
            content = path.read_text()
        except OSError:
            parts.append(f"\n\nFile `{relative}` is not readable.")
            continue
        parts.append(f"\n\nFile `{relative}`:\n\n```\n{content}\n```")
    return [{"role": "user", "content": "".join(parts)}]


def estimate_tokens(plan, model, root):
    """Token estimate for the dry-run preview. Uses the model's tokenizer when
    available, falls back to a rough chars/4 heuristic."""
    total = 0
    for item in plan["items"]:
        messages = _item_messages(item, root)
        try:
            total += model.token_count(messages)
        except Exception:
            total += sum(len(m.get("content") or "") for m in messages) // 4
    return total


def target_directories(plan):
    return sorted({str(t.parent) for item in plan["items"] for t in item["targets"]})


def _task_dir(root):
    task_dir = Path(root) / BATCH_DIR
    task_dir.mkdir(parents=True, exist_ok=True)
    try:
        task_dir.chmod(stat.S_IRWXU)  # 0700: owner only
    except OSError:
        pass
    return task_dir


def _task_path(root, task_id):
    return _task_dir(root) / f"{task_id}.json"


def save_task(root, record):
    path = _task_path(root, record["task_id"])
    path.write_text(json.dumps(record, indent=2))
    try:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0600
    except OSError:
        pass
    return path


def load_task(root, task_id):
    if "/" in task_id or ".." in task_id:
        raise BatchError(f"Invalid task id: {task_id!r}")
    path = _task_path(root, task_id)
    if not path.is_file():
        raise BatchError(f"No batch task record found for {task_id!r} in {BATCH_DIR}")
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as err:
        raise BatchError(f"Unable to read task record {path}: {err}")


def _openai_client(io):
    """An OpenAI-compatible client for the resolved batch provider."""
    from openai import OpenAI

    api_key = os.environ.get("OPENAI_API_KEY")
    api_base = os.environ.get("OPENAI_API_BASE")
    if not api_key:
        raise BatchError("OPENAI_API_KEY is not set — batch submission would bill nothing.")
    if api_base and not any(api_base.startswith(base) for base in SUPPORTED_API_BASES):
        io.tool_warning(
            f"Batch API support is only verified for {', '.join(SUPPORTED_API_BASES)};"
            f" submitting anyway against {api_base}"
        )
    kwargs = {"api_key": api_key}
    if api_base:
        kwargs["base_url"] = api_base
    return OpenAI(**kwargs)


def check(model, io):
    """Validate provider/model selection for batch without billing anything."""
    problems = []
    if not os.environ.get("OPENAI_API_KEY"):
        problems.append("OPENAI_API_KEY is not set")
    api_base = os.environ.get("OPENAI_API_BASE") or getattr(model.info, "api_base", None)
    if api_base and not any(api_base.startswith(base) for base in SUPPORTED_API_BASES):
        problems.append(
            f"api_base {api_base} is not a verified batch endpoint"
            f" (expected one of {', '.join(SUPPORTED_API_BASES)})"
        )
    if model is None:
        problems.append("no model configured (use --model or aider.conf.yml)")

    for problem in problems:
        io.tool_error(f"batch check: {problem}")
    if problems:
        return False
    io.tool_output(
        f"batch check: OK — {model.name} via {api_base or 'https://api.openai.com'}."
        " Nothing was billed."
    )
    return True


def preview(plan, model, io):
    """Dry-run preview: item count, model, target directories, token estimate
    and the snapshot hash that --batch-expect will require. Uploads nothing."""
    items = plan["items"]
    tokens = estimate_tokens(plan, model, plan["root"])
    snapshot = plan_snapshot(
        plan, {"model": model.name if model else None, "plan": plan["plan_path"].name}
    )
    io.tool_output(f"Batch plan preview for {plan['plan_path']}:")
    io.tool_output(f"  items: {len(items)}")
    io.tool_output(f"  model: {model.name if model else '(unset)'}")
    io.tool_output(f"  token estimate: ~{tokens}")
    dirs = target_directories(plan)
    io.tool_output(f"  target directories ({len(dirs)}): {', '.join(dirs) if dirs else '(none)'}")
    io.tool_output(f"  snapshot: {snapshot}")
    io.tool_output("Nothing was uploaded or billed.")
    return snapshot


def run(plan, model, io, *, expect=None, yes=False):
    """Preview-then-submit. With --batch-expect the recorded snapshot must
    match the current plan/sources/settings or the run refuses before any
    upload happens."""
    snapshot = preview(plan, model, io)
    if expect is not None and expect != snapshot:
        raise BatchError(
            f"Plan snapshot {snapshot} does not match --batch-expect {expect};"
            " refusing to submit. Re-run with --batch-dry-run for a fresh preview."
        )
    if expect is None and not yes:
        raise BatchError(
            "Refusing to submit without --batch-expect <snapshot> (or --batch-yes to"
            " skip the preview gate). Preview first with --batch-dry-run."
        )

    client = _openai_client(io)
    model_name = plan.get("model") or model.name

    request_lines = []
    for item in plan["items"]:
        request_lines.append(
            {
                "custom_id": item["id"],
                "method": "POST",
                "url": BATCH_ENDPOINT,
                "body": {
                    "model": model_name,
                    "messages": _item_messages(item, plan["root"]),
                },
            }
        )
    task_dir = _task_dir(plan["root"])
    requests_path = task_dir / "requests.jsonl"
    requests_path.write_text("".join(json.dumps(line) + "\n" for line in request_lines))

    io.tool_output(f"Uploading {len(request_lines)} batch request(s)…")
    uploaded = client.files.create(file=requests_path.open("rb"), purpose="batch")
    batch = client.batches.create(
        input_file_id=uploaded.id,
        endpoint=BATCH_ENDPOINT,
        completion_window=BATCH_COMPLETION_WINDOW,
        metadata={"aider_plan": plan["plan_path"].name},
    )

    all_targets = sorted({str(t) for item in plan["items"] for t in item["targets"]})
    record = {
        "task_id": f"batch-{int(time.time())}",
        "batch_id": batch.id,
        "input_file_id": uploaded.id,
        "model": model_name,
        "snapshot": snapshot,
        "plan": str(plan["plan_path"].name),
        "created_at": int(time.time()),
        "items": [
            {"id": item["id"], "targets": [str(t) for t in item["targets"]]}
            for item in plan["items"]
        ],
        "sources": _source_fingerprints(plan["root"], all_targets),
        "status": batch.status,
    }
    save_task(plan["root"], record)
    io.tool_output(
        f"Batch {batch.id} submitted as task {record['task_id']}"
        f" ({len(request_lines)} item(s), window {BATCH_COMPLETION_WINDOW})."
        f" Track it with: aider --batch-collect {record['task_id']}"
    )
    return record


def collect(root, task_id, io, *, wait=False, poll_seconds=60):
    """Reconcile a submitted batch: report each item delivered / held / failed.
    Never auto-retries billed items."""
    record = load_task(root, task_id)
    client = _openai_client(io)

    batch = client.batches.retrieve(record["batch_id"])
    while wait and batch.status in ("validating", "in_progress", "finalizing"):
        io.tool_output(f"batch {record['batch_id']} still {batch.status}; waiting {poll_seconds}s…")
        time.sleep(poll_seconds)
        batch = client.batches.retrieve(record["batch_id"])

    record["status"] = batch.status
    if batch.status != "completed":
        save_task(root, record)
        if batch.status in ("validating", "in_progress", "finalizing"):
            io.tool_output(f"batch {record['batch_id']} is {batch.status}; nothing to collect yet.")
            return record
        raise BatchError(
            f"batch {record['batch_id']} ended with status {batch.status}"
            f" (failed: {getattr(batch.request_counts, 'failed', '?')},"
            f" completed: {getattr(batch.request_counts, 'completed', '?')})."
            " Failed items are never auto-retried — a retry bills again."
        )

    output_file_id = getattr(batch, "output_file_id", None)
    results = {}
    if output_file_id:
        raw = client.files.content(output_file_id).content
        for line in raw.decode().splitlines():
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            results[entry.get("custom_id")] = entry

    delivered, held, failed = 0, 0, 0
    current_sources = _source_fingerprints(
        root, sorted({str(t) for item in record["items"] for t in item["targets"]})
    )
    for item in record["items"]:
        result = results.get(item["id"])
        if result is None or result.get("error"):
            failed += 1
            io.tool_error(f"  {item['id']}: failed — {(result or {}).get('error') or 'no result'}")
            continue
        changed = [
            t
            for t in item["targets"]
            if record["sources"].get(t) != current_sources.get(t)
        ]
        if changed:
            held += 1
            io.tool_warning(
                f"  {item['id']}: held — source changed since submit: {', '.join(changed)}"
            )
            continue
        delivered += 1
        body = ((result.get("response") or {}).get("body") or {})
        content = ""
        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            pass
        out_path = _task_dir(root) / f"{record['task_id']}-{item['id']}.md"
        out_path.write_text(content)
        try:
            out_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass
        io.tool_output(f"  {item['id']}: delivered → {out_path}")

    record["status"] = batch.status
    record["collected_at"] = int(time.time())
    record["summary"] = {"delivered": delivered, "held": held, "failed": failed}
    save_task(root, record)
    io.tool_output(f"batch {record['batch_id']}: {delivered} delivered, {held} held, {failed} failed.")
    return record
