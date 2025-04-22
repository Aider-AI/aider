"""
Run n silent LLM calls in parallel to generate image prompts,
then print all of them at once and ask the model to choose the best.
"""

import aider.helpers as ah
from concurrent.futures import as_completed

IDEA_PROMPT = (
    "Invent a fantastical, visually rich, 20‑word text prompt for an AI image."
)

def main(ctx, *, n: int = 5):
    n = int(n)

    # 1 · Spawn all jobs
    futs = [ah.spawn(f"> {IDEA_PROMPT}") for _ in range(n)]
    yield ah.log(f"# Launched {n} prompt generators in parallel…")

    # 2 · Wait silently
    # This list comprehension implicitly waits for all futures to complete
    ideas = [f.result().strip() for f in futs]

    # 3 · Emit the numbered list once
    numbered = "\n".join(f"{i+1}. {txt}" for i, txt in enumerate(ideas, 1))
    yield ah.log("\nAll prompts:\n" + numbered)

    # 4 · Ask model to pick the best
    best = yield ah.chat(
        "Choose the single most striking prompt below and repeat it verbatim:\n\n"
        + numbered
    )
    yield ah.log("\n🥇 Best prompt:\n" + best.strip())
