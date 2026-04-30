# MTARP Phase 1 Implementation Task

## What you are building

Implement the MTARP (Multi-Turn Agentic Routing Protocol) Phase 1 session envelope for aider-relay.
This makes aider-relay write a `session.json` file whenever it switches providers due to exhaustion,
recording who was working on what and what git state they left behind.

## Authoritative specifications

Read these files before writing any code:
- `.kbriefs/KB-2026-021-multi-turn-agentic-routing-protocol.md` — full protocol spec
- `.kbriefs/KB-2026-022-mtarp-protocol-definition.md` — protocol definition
- `.kbriefs/KB-2026-007-higher-level-context-relay.md` — design context and RelayContext schema
- `tests/test_mtarp_session.py` — TDD tests you MUST make pass (read these first)
- `scripts/relay_loop.py` — current relay implementation to update
- `aider/providers/base.py` — BaseProvider and ProviderTier definitions
- `tests/helpers.py` — MockProvider and test helpers

## Exact files to create/modify

### 1. CREATE: `aider/relay/__init__.py`
Empty file to make `aider.relay` a package.

### 2. CREATE: `aider/relay/session.py`
Implement the `MTARPSession` dataclass. Key requirements:

```python
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import json
import subprocess
import uuid

@dataclass
class MTARPSession:
    schema_version: str = "1.0"
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_description: str = ""
    task_created_at: str = ""
    git_head: str = ""
    git_branch: str = ""
    git_diff_since: str = ""   # git SHA at session START (diff from here shows what was done)
    handoff_reason: str = "exhausted"
    handoff_at: str = ""
    outgoing_provider: str = ""
    outgoing_tier: str = "agentic_cli"
    provider_history: list = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize to MTARP schema structure (nested, not flat)."""
        # Must produce: {schema_version, session_id, task: {description, created_at},
        #  git: {head, branch, diff_since}, handoff: {reason, at, outgoing_provider, outgoing_tier},
        #  provider_history: [...]}

    def write(self, path: Path) -> None:
        """Write session.json, creating parent directories as needed."""

    @classmethod
    def read(cls, path: Path) -> "MTARPSession":
        """Read and deserialize session.json."""

    @classmethod
    def create(cls, task: str, primary_provider: str) -> "MTARPSession":
        """Factory: create session capturing current git state. Graceful if git unavailable."""
        # Capture: git rev-parse HEAD → git_head and git_diff_since
        #          git rev-parse --abbrev-ref HEAD → git_branch
        #          datetime.now(utc).isoformat() → task_created_at

    def add_provider_run(self, *, provider: str, tier: str, session_id: str,
                         started_at: str, ended_at: str | None, end_reason: str) -> None:
        """Append a completed provider run to provider_history."""
```

### 3. MODIFY: `scripts/relay_loop.py`

Add `session_dir: str = ".aider-relay"` parameter to `relay()`.

At relay start:
```python
session = MTARPSession.create(task=task, primary_provider=primary)
provider_started_at = datetime.now(tz=timezone.utc).isoformat()
```

When exhaustion is detected (result == "exhausted"), BEFORE switching:
```python
ended_at = datetime.now(tz=timezone.utc).isoformat()
session.add_provider_run(
    provider=active,
    tier=providers[active].tier,
    session_id=providers[active].current_session_id or "",
    started_at=provider_started_at,
    ended_at=ended_at,
    end_reason="exhausted",
)
session.outgoing_provider = active
session.handoff_at = ended_at
# Capture current git HEAD (may have changed during session)
try:
    session.git_head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True
    ).strip()
except (subprocess.CalledProcessError, OSError):
    pass
session_path = Path(session_dir) / "session.json"
session_path.parent.mkdir(parents=True, exist_ok=True)
session.write(session_path)
# Reset timer for next provider
provider_started_at = datetime.now(tz=timezone.utc).isoformat()
```

Also update `handoff_prompt()` to accept an optional `session: MTARPSession | None = None`
and when provided, append a note like:
```
## MTARP Session Envelope
A session record has been written to .aider-relay/session.json capturing the task,
git state at handoff, and which provider was working. You can inspect it with:
  cat .aider-relay/session.json
```

Import `MTARPSession` at the top of relay_loop.py:
```python
from aider.relay.session import MTARPSession
```

And add `from datetime import datetime, timezone` if not already present.

### 4. UPDATE: `main()` in `scripts/relay_loop.py`

Pass `session_dir=".aider-relay"` through to `relay()`:
```python
asyncio.run(relay(task, args.primary, args.fallback, args.sim_exhaust_after, session_dir=".aider-relay"))
```

## Running the tests

After implementing, verify ALL tests pass:

```bash
cd /workspaces/aider-relay
source .venv/bin/activate
pytest tests/ -v
```

All 30 existing tests in `tests/test_relay.py` must still pass.
All new tests in `tests/test_mtarp_session.py` must pass.

## Definition of done

- [ ] `aider/relay/__init__.py` exists
- [ ] `aider/relay/session.py` exists with `MTARPSession` class
- [ ] `scripts/relay_loop.py` has `session_dir` parameter and writes `session.json` on exhaustion
- [ ] `pytest tests/ -v` exits 0 with no failures
- [ ] Running `python scripts/relay_loop.py --sim-exhaust-after 1 "test"` creates `.aider-relay/session.json`

## Notes on test structure

`tests/helpers.py` contains `MockProvider`, `success_turn`, `exhausted_turn`, `error_turn`.
`tests/test_relay.py` imports from `tests.helpers`.
`tests/test_mtarp_session.py` imports from `tests.helpers`.
Do not duplicate helpers across test files.
