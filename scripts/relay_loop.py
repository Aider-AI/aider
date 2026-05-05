#!/usr/bin/env python3
"""Compatibility shim — relay logic lives in aider.relay.loop."""
from aider.relay.loop import (  # noqa: F401
    _check_interrupt,
    _run_turn_events,
    git_context,
    handoff_prompt,
    main,
    make_provider,
    relay,
    run_turn,
)

if __name__ == "__main__":
    main()
