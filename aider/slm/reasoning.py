from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ReasoningDecision:
    prompt: str
    files: list[str] | None = None


class ReasoningEngine:
    """Turn raw log lines into concrete Aider instructions."""

    GAS_BURN_PATTERN = "Gas Burned > Expected Profit"

    # Only react to errors that look relevant to trading execution / profitability.
    _RELEVANT_ERROR_PATTERN = re.compile(
        r"(expected profit|gas burned|out of gas|slippage|revert|insufficient funds|priority fee|base fee)",
        re.IGNORECASE,
    )

    def decision_from_log(self, log_line: str) -> ReasoningDecision | None:
        line = log_line.strip()
        if not line:
            return None

        # Required: Gas strategy self-healing.
        if self.GAS_BURN_PATTERN in line:
            return ReasoningDecision(
                prompt=(
                    "/code Refactor gas strategy in src/main.rs. "
                    "Minimize gas use and adjust prioritization/fee strategy so that expected "
                    "profit exceeds gas burned with safety margins. "
                    "Include any relevant tests.\n\n"
                    f"Trigger log: {line}"
                ),
                files=["src/main.rs"],
            )

        # Allow operators to inject prompts directly from logs.
        # Example: "SLM_PROMPT: please investigate why /health is slow"
        m = re.search(r"\bSLM_PROMPT:\s*(.+)$", line)
        if m:
            return ReasoningDecision(prompt=m.group(1).strip())

        # Best-effort signal extraction from application logs.
        # Keep this conservative to avoid spamming Aider on unrelated errors.
        if any(tok in line for tok in ("ERROR", "FATAL", "WARN")) and self._RELEVANT_ERROR_PATTERN.search(line):
            return ReasoningDecision(
                prompt=(
                    "/code Investigate and fix the following trading-related log issue. "
                    "If changes are required, implement them in this repo.\n\n"
                    f"Log line:\n{line}"
                )
            )

        return None
