"""
A minimal re‑implementation of the legacy `/architect` command as a **macro**.
Demonstrates generator style.
"""

# import aider_helpers as ah  # shipped with the fork’s examples # Commented out as aider_helpers is not provided

def main(ctx, goal: str = "scaffold a new project", max_rounds: int = 6):
    io = ctx["io"]

    io.tool_comment(f"🏗  Architect macro started – goal: {goal!r}")

    for n in range(1, max_rounds + 1):
        # Ask the LLM to propose an architectural plan
        plan = yield f"Design phase {n}: create / refine the architecture to {goal}"

        # Let the user (or another LLM) critique & accept
        verdict = yield (
            "Critique the above plan. If it is good, reply with **YES** on the first line, "
            "else **NO** and list improvements."
        )

        if verdict.strip().upper().startswith("YES"):
            io.tool_comment("✅ Plan accepted – exiting architect macro.")
            return

        # Feed suggested improvements back into the loop
        goal = verdict  # next iteration refines

    io.tool_comment("🚫 Architect macro gave up after max rounds.")
