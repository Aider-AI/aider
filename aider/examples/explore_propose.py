"""
ideate_explore_propose.py
-------------------------

Launch with something like:

    /macro examples/ideate_explore_propose.py goal="Design a minimal REST API" ideas=8

Flow
~~~~
1. **Explore / brainstorm** until we collect *ideas* distinct ideas.
2. **Cluster & analyse** the idea pool into themes.
3. **Plan** – write a concrete implementation plan.
4. **Propose** – draft code or an answer that fulfils the goal.
5. **Critique** – self‑review; identify weaknesses & bugs.
6. **Polish** – apply critique and present the final output.
"""

import aider.helpers as ah

def main(ctx, *, goal: str = "Solve the stated problem", ideas: int = 10):
    ideas = int(ideas)
    pool = []

    # 1 · EXPLORATION --------------------------------------------------------
    while len(pool) < ideas:
        idea = yield f"> 💡 Come up with a novel idea to achieve: {goal}"
        pool.append(idea.strip())
        yield ah.log(f"# Collected idea {len(pool)}/{ideas}")

    # 2 · CLUSTER + ANALYSE --------------------------------------------------
    clusters = yield from ah.code(
        "EXPLORATION.md",
        "The **IDEA POOL** is below.\n\n"
        + "\n".join(f"- {p}" for p in pool)
        + "\n\nTask:\n"
        "1. Cluster the ideas by similarity or shared approach.\n"
        "2. For each cluster, summarise its theme and note pros/cons."
    )

    # 3 · PLAN ---------------------------------------------------------------
    plan = yield from ah.code(
        "PLAN.md",
        "Based on the analysis in EXPLORATION.md, craft a **detailed, step‑by‑step "
        "implementation plan** that addresses the goal:\n\n"
        f"**GOAL:** {goal}\n\n"
        "The plan must be concrete: list modules, key data structures, API routes, "
        "algorithms, and any external services or tools required."
    )

    # 4 · PROPOSE ------------------------------------------------------------
    proposal = yield from ah.code(
        "PROPOSAL.md",
        "Implement the plan from PLAN.md.\n\n"
        "• If code changes are needed, output them in aider's file‑listing diff format.\n"
        "• If the deliverable is a written answer, write the full response here."
    )

    # 5 · CRITIQUE -----------------------------------------------------------
    critique = yield from ah.code(
        "CRITIQUE.md",
        "Critically review PROPOSAL.md.\n"
        "Address:\n"
        "• Correctness / bugs\n"
        "• Missing edge cases\n"
        "• Alternative approaches\n"
        "• Clarity and readability\n\n"
        "End with a severity rating (low / medium / high)."
    )

    # 6 · POLISH -------------------------------------------------------------
    yield ah.log("# Applying critique, producing polished result…")
    yield from ah.code(
        "PROPOSAL.md",
        "Incorporate feedback from CRITIQUE.md and deliver the final, polished output.\n"
        "Ensure all high‑severity issues are addressed."
    )

    yield ah.log("🎉 Ideate‑explore‑propose‑critique‑polish loop completed.")
