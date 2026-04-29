---
id: KB-2026-023
type: standard
status: validated
created: 2026-04-29
updated: 2026-04-29
tags: [validation, phase1, testing, relay-loop, sim-exhaust, git-handoff]
related: [KB-2026-007, KB-2026-017, KB-2026-002]
---

# Phase 1 Validation Results

## Scope

Validation of three Phase 1 gaps identified at the end of the implementation sprint:

1. Multi-turn continuity — second user prompt is passed to the active provider
2. Sim-exhaust ping-pong — `--sim-exhaust-after N` correctly triggers both-providers-exhausted stop
3. Git diff in handoff prompt — handoff prompt contains real diff output when file changes exist

## Automated Test Results (2026-04-29)

**30/30 unit tests passing** (`tests/test_relay.py`) in devcontainer (Python 3.12.11, pytest 9.0.2).

### What was tested automatically (mock providers, no real API calls)

| Area | Tests | Result |
|---|---|---|
| `git_context()` structure and fallback | 4 | ✅ Pass |
| `handoff_prompt()` content and framing | 4 | ✅ Pass |
| `run_turn()` event handling (text, exhausted, error, done) | 5 | ✅ Pass |
| Relay state machine — sim_exhaust_after=1 switches and stops | 2 | ✅ Pass |
| Relay state machine — sim_exhaust_after=2 two-turn primary | 2 | ✅ Pass |
| Relay state machine — real exhaustion switch | 2 | ✅ Pass |
| Relay state machine — both exhausted stops | 2 | ✅ Pass |
| Relay state machine — handoff prompt content on switch | 2 | ✅ Pass |
| Relay state machine — initial prompt is the task, not handoff | 1 | ✅ Pass |
| Multi-turn: second user prompt passed to provider | 1 | ✅ Pass |
| Multi-turn: empty input stops relay | 1 | ✅ Pass |
| Multi-turn: EOFError stops relay gracefully | 1 | ✅ Pass |
| ProviderEvent dataclass defaults | 3 | ✅ Pass |

### Bug found and fixed during testing

`git_context()` caught only `subprocess.CalledProcessError` — a `FileNotFoundError` (raised when git is not on PATH, `OSError` subclass) would propagate uncaught. Fixed to catch `(subprocess.CalledProcessError, OSError)`.

## Manual Validation Required (in devcontainer)

The following three scenarios require real provider calls and cannot be automated without live credentials. Run these in the devcontainer.

### Test 1: Sim-exhaust ping-pong (primary validation)

**What it validates:** Provider switching, handoff prompt delivery, both-exhausted stop.

```bash
# In devcontainer
cd /workspaces/aider-relay
source .venv/bin/activate
python scripts/relay_loop.py --sim-exhaust-after 1 "say hello and list the files in this repository"
```

**Expected output sequence:**
1. `[RELAY] Primary: CLAUDE | Fallback: CODEX`
2. Claude responds with hello + file list
3. `[RELAY] (sim) Simulating exhaustion after 1 turn(s) on CLAUDE. Switching to CODEX...`
4. `[RELAY] Switching to CODEX...`
5. Codex responds (with handoff prompt — should acknowledge "continuing" task)
6. `[RELAY] (sim) Simulating exhaustion after 1 turn(s) on CODEX. Switching to CLAUDE...`
7. `[RELAY] Both providers exhausted. Stopping.`

**Pass criteria:**
- Both providers produce output
- Handoff prompt framing visible in Codex's response (it should acknowledge "previous assistant")
- Process exits cleanly without exception

### Test 2: Multi-turn continuity

**What it validates:** User follow-up prompt is passed to the active provider as a new turn.

```bash
python scripts/relay_loop.py "what is 2 + 2?"
# At the You: prompt, type: "now multiply that by 3"
# At the next You: prompt, press Enter to stop
```

**Expected output sequence:**
1. Claude responds with "4" (or equivalent)
2. `You: ` prompt appears
3. After typing follow-up, Claude responds with "12" (or equivalent)
4. Second `You: ` prompt appears, Enter stops relay

**Pass criteria:**
- Provider correctly handles the follow-up as a new prompt
- Second response references the first (shows conversational context is NOT carried — each turn is independent prompt, no history relay)
- Note: context is NOT carried between turns at Phase 1 — this is expected and documented (KB-2026-017)

### Test 3: Git diff in handoff prompt

**What it validates:** Handoff prompt contains real diff output when uncommitted changes exist.

```bash
# Create an uncommitted change
echo "# test change" >> /workspaces/aider-relay/README.md

# Run with sim-exhaust to trigger handoff
python scripts/relay_loop.py --sim-exhaust-after 1 "describe any recent changes to this repository"
```

**Expected output sequence:**
1. Claude describes the repo
2. Handoff triggered; Codex receives handoff prompt
3. Codex's response should reference the README change (it's in the `git diff HEAD` output injected into the handoff prompt)

**Pass criteria:**
- Handoff prompt contains the README.md diff (visually confirm by adding `print(prompt)` to `run_turn` temporarily, or observe Codex referencing the change)
- Clean up: `git checkout README.md` after test

**Known limitation at Phase 1:** The diff only captures uncommitted changes (`git diff HEAD`). If Claude made commits during its turn, those appear in `git log` output in the handoff, not the diff. Both are included in the handoff prompt.

## Phase 1 Verdict

| Gap | Automated | Manual required | Status |
|---|---|---|---|
| Multi-turn continuity | ✅ Proven by unit test | Verify context not relayed (expected) | Automated PASS |
| Sim-exhaust ping-pong | ✅ State machine proven | Verify real provider output + clean exit | Automated PASS |
| Git diff in handoff | ✅ Prompt construction proven | Verify diff appears when changes exist | Manual needed |
| Bug: `git_context` OSError | ✅ Fixed + tested | — | Fixed |

Phase 1 automated validation complete. Manual devcontainer validation covers the live-provider scenarios.
