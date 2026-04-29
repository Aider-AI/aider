---
id: KB-2026-002
type: limit
status: validated
created: 2026-04-27
updated: 2026-04-28
tags: [rate-limit, usage-window, error-signal, model-switching, claude-code, codex]
related: [KB-2026-001, KB-2026-004, KB-2026-006, KB-2026-010]
---

# Usage Window Exhaustion Signal Taxonomy

## Context

aider-relay must distinguish "transient rate limit — retry soon" from "usage window exhausted — switch providers now." This K-Brief records validated signals for Claude Code and the current gap for Codex.

## Claude Code — VALIDATED (2026-04-28)

`claude_agent_sdk` v0.1.69 exposes structured rate limit events via the `query()` async iterator.

### The Signal

When the usage window is exhausted, `query()` yields a `RateLimitEvent`:

```python
@dataclass
class RateLimitInfo:
    status: Literal["allowed", "allowed_warning", "rejected"]
    resets_at: int | None          # Unix timestamp of reset
    rate_limit_type: Literal[
        "five_hour", "seven_day",
        "seven_day_opus", "seven_day_sonnet",
        "overage"
    ] | None
    utilization: float | None      # 0.0–1.0 fraction consumed
    overage_status: str | None
    overage_resets_at: int | None

@dataclass
class RateLimitEvent:
    rate_limit_info: RateLimitInfo
    uuid: str
    session_id: str
```

**Exhaustion condition:** `rate_limit_info.status == "rejected"`

**Warning condition:** `rate_limit_info.status == "allowed_warning"` (approaching limit — use to trigger proactive context snapshots)

### Rate Limit Windows

| type | description |
|------|-------------|
| `five_hour` | Standard 5-hour usage window |
| `seven_day` | 7-day rolling window |
| `seven_day_opus` | Opus-specific 7-day window |
| `seven_day_sonnet` | Sonnet-specific 7-day window |
| `overage` | Pay-as-you-go overage |

### Detection Implementation

```python
from claude_agent_sdk import RateLimitEvent, query

async def run_with_exhaustion_detection(prompt: str):
    async for msg in query(prompt=prompt):
        if isinstance(msg, RateLimitEvent):
            info = msg.rate_limit_info
            if info.status == "rejected":
                # Switch provider — return reset timestamp for scheduling
                return "exhausted", info.resets_at, info.rate_limit_type
            elif info.status == "allowed_warning":
                # Proactively snapshot context
                trigger_context_snapshot()
        else:
            yield msg
```

### Key Value

`resets_at` is a **Unix timestamp** — enables precise auto-resume scheduling (KB-2026-005) without guessing.

## Codex — PARTIALLY VALIDATED (2026-04-28)

The `codex-app-server` Python package **does not exist on PyPI**. Integration is subprocess-based via `codex exec --json` (see KB-2026-010 for the full validated JSONL event taxonomy).

The Codex CLI exposes rate limit errors in `--json` mode as:

```json
{"type":"turn.failed","error":{"message":"...","code":"rate_limit_exceeded"}}
```

For Codex, the detection approach is a subprocess adapter reading JSONL from `codex exec --json` stdout. The specific error payload when a **subscription window** (vs TPM) is exhausted is not yet empirically validated — this requires deliberately exhausting a ChatGPT Plus session.

**Gap remaining for Codex:** Need to capture the exact JSONL payload when the 5-hour window (not TPM) is exhausted, and confirm whether a `retry_after` value distinguishes the two.

## Implications for Architecture

1. Claude Code exhaustion detection is first-class via the SDK — no string parsing needed
2. The `allowed_warning` event enables proactive context snapshotting before the limit hits
3. `resets_at` enables precise auto-resume scheduling
4. Codex detection will require subprocess-based JSONL parsing until a Python SDK is available

## Applicability

- ✅ Claude Code provider implementation — use `RateLimitEvent` directly
- ✅ Auto-resume scheduling (KB-2026-005) — use `resets_at`
- ⚠️ Codex — subprocess JSONL parsing until KB-2026-010 is resolved
