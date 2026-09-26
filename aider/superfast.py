# Superfast Decision Gate -- System One front-door classifier (shadow mode).
#
# Concept and reference implementation by Andrea Bruno, released under the
# Creative Commons Attribution 4.0 license (CC BY 4.0). See the white paper
# "harness-superfast" for the full design. The decision models themselves
# (Von, OpenJev, Laya) are third-party open models; only this integration
# architecture and routing method are covered by the attribution above.
#
# A small, non-autoregressive "System One" decision model evaluates the pending
# user turn in a single forward pass and returns typed, calibrated answers
# without generating text. This module turns those answers into a conservative
# routing recommendation.
#
# Design contract:
#   - Off by default. Nothing runs unless SUPERFAST_ENABLED is set to a truthy
#     value. A user who does nothing sees the exact current behavior.
#   - Shadow mode. This increment only classifies and logs the recommendation.
#     It never changes routing, never skips the model call, and never alters any
#     user-visible behavior. Acting on the route is a later, validated step.
#   - Fail open. Any error, timeout, non-2xx response, unreachable backend, or
#     malformed body yields "no opinion" (None). It never raises into the agent
#     loop and never adds latency to the real turn (the call runs off-thread).
#   - No new dependencies. Talks to a local Jev-compatible endpoint with the
#     ``requests`` client that aider already uses elsewhere in the codebase.

import os
import threading
import time

import requests

DEFAULT_ENDPOINT = "http://localhost:8000/v1/systemone"
DEFAULT_MODEL = "von-1.2.0"
DEFAULT_TIMEOUT_MS = 150

# Minimum calibrated intent confidence required for the plain_chat fast route.
PLAIN_CHAT_CONFIDENCE_FLOOR = 0.5

# Standard question set for classifying an incoming user turn. Kept small so the
# single forward pass stays well under the timeout budget.
TURN_QUESTIONS = {
    "needs_tool": {
        "type": "noul",
        "instructions": (
            "Does answering this request require taking an action with a tool"
            " (reading, writing, running, searching), rather than replying from"
            " what is already known?"
        ),
    },
    "answerable_from_context": {
        "type": "noul",
        "instructions": (
            "Can this request be answered from information already present in"
            " the conversation, without any new investigation?"
        ),
    },
    "intent": {
        "type": "choice",
        "instructions": "Classify the primary intent of the user request.",
        "criteria": {
            "code_change": "Create, edit, or delete code or files.",
            "code_question": "Explain or reason about code without changing it.",
            "command": "Run a command or operation.",
            "chat": "Casual conversation or a question needing no tools.",
            "other": "None of the above.",
        },
    },
}


def _truthy(value):
    """Interpret an environment-variable string as a boolean, defaulting to False."""
    if value is None:
        return False
    return value.strip().lower() in ("1", "true", "yes", "on")


def enabled():
    """Master switch: True only when SUPERFAST_ENABLED is set to a truthy value."""
    return _truthy(os.environ.get("SUPERFAST_ENABLED"))


def _endpoint():
    return os.environ.get("SUPERFAST_ENDPOINT") or DEFAULT_ENDPOINT


def _model():
    return os.environ.get("SUPERFAST_MODEL") or DEFAULT_MODEL


def _timeout_seconds():
    raw = os.environ.get("SUPERFAST_TIMEOUT_MS")
    try:
        ms = int(raw)
    except (TypeError, ValueError):
        ms = DEFAULT_TIMEOUT_MS
    if ms <= 0:
        ms = DEFAULT_TIMEOUT_MS
    return ms / 1000.0


def _read_noul(answer):
    """Return a noul probability only when it is a real finite value in [0, 1].

    Anything else (absent, NaN, Infinity, out of range, wrong type) is treated as
    "no evidence" (None), so a mis-scaled or missing answer can never produce a
    decisive fast route.
    """
    if not isinstance(answer, dict):
        return None
    value = answer.get("noul")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if value != value:  # NaN guard
        return None
    return value if 0.0 <= value <= 1.0 else None


def _confident(answer, floor):
    """True only for a real, finite confidence in [0, 1] at or above the floor."""
    if not isinstance(answer, dict):
        return False
    value = answer.get("confidence")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if value != value:  # NaN guard
        return False
    return 0.0 <= value <= 1.0 and value >= floor


def derive_route(answers):
    """Derive a conservative route from the decision answers.

    The gate only recommends a fast route when the relevant probabilities are
    decisive; otherwise it returns "unknown" so the caller falls back to the
    normal path.
    """
    if not isinstance(answers, dict):
        return "unknown"

    needs_tool = _read_noul(answers.get("needs_tool"))
    from_context = _read_noul(answers.get("answerable_from_context"))

    # Decisive "needs a tool" wins first -- the harness must not skip work.
    if needs_tool is not None and needs_tool >= 0.85:
        return "needs_tool"

    # Strongly answerable from context, with a present and low tool-need signal.
    if (
        from_context is not None
        and from_context >= 0.85
        and needs_tool is not None
        and needs_tool <= 0.3
    ):
        return "answer_from_context"

    # Clearly chat, with a calibrated intent and a present, low tool-need signal.
    intent = answers.get("intent")
    if (
        isinstance(intent, dict)
        and intent.get("choice") == "chat"
        and _confident(intent, PLAIN_CHAT_CONFIDENCE_FLOOR)
        and needs_tool is not None
        and needs_tool <= 0.2
    ):
        return "plain_chat"

    return "unknown"


def query_system_one(state, questions, endpoint, model, timeout):
    """Issue one System One request.

    Returns the parsed answers dict on success, or None on any failure
    (connection error, timeout, non-2xx, malformed body). Never raises.
    """
    try:
        resp = requests.post(
            endpoint,
            json={"model": model, "state": state, "questions": questions},
            timeout=timeout,
        )
    except Exception:
        # Connection error, timeout, DNS failure, refused, etc. Fail open.
        return None

    if resp.status_code < 200 or resp.status_code >= 300:
        return None

    try:
        data = resp.json()
    except ValueError:
        return None

    if not isinstance(data, dict):
        return None

    answers = data.get("answers")
    if not isinstance(answers, dict):
        return None

    return answers


def classify_turn(message):
    """Classify a user turn through the gate.

    Returns a dict with the derived route and the measured latency in ms, or
    None when the gate is disabled or unavailable (fail-open).
    """
    if not enabled():
        return None

    started = time.time()
    answers = query_system_one(message, TURN_QUESTIONS, _endpoint(), _model(), _timeout_seconds())
    latency_ms = int((time.time() - started) * 1000)
    if answers is None:
        return None

    return {"route": derive_route(answers), "latency_ms": latency_ms}


def shadow_log(io, message):
    """Run the gate in shadow mode and record the recommendation off the turn.

    Returns immediately so the real turn never waits on the decision backend.
    The classification runs on a daemon thread and is recorded through the
    project's existing log-only output. Any failure is swallowed (fail-open).
    """
    if not enabled() or not message:
        return

    def _run():
        try:
            result = classify_turn(message)
            if result is None:
                io.tool_output("[superfast] gate: no opinion (fail-open)", log_only=True)
                return
            io.tool_output(
                f"[superfast] shadow route={result['route']} latency_ms={result['latency_ms']}",
                log_only=True,
            )
        except Exception:
            # Shadow mode must never affect the agent.
            pass

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
