"""
parallel_image_prompts.py
-------------------------

1. Launch *n* silent chat requests in parallel, each asking the model to
   invent a vivid AI‑image prompt.
2. Wait for all replies.
3. Ask the model to pick the single “best” prompt.
4. Print that winning prompt.

Run with:
    /macro examples/parallel_image_prompts.py n=5
"""

import aider.helpers as ah
from concurrent.futures import as_completed

IDEA_PROMPT = (
    "Invent a fantastical, visually rich text prompt for an AI image. "
    "It should be roughly 20 words long and surprising."
)

def main(ctx, *, n: int = 5):
    n = int(n)

    # 1 · spawn N silent chat calls in parallel
    futures = [ah.spawn(f"> {IDEA_PROMPT}") for _ in range(n)]
    yield ah.log(f"# Collecting {n} ideas …")

    # Optional progress bar while they run
    done = 0
    for fut in as_completed(futures):
        done += 1
        yield ah.log("# [" + "#" * done + "." * (n - done) + "]")

    # 2 · gather results in original order
    ideas = [f.result().strip() for f in futures]

    # 3 · ask the model to choose the best
    joined = "\n".join(f"{i+1}. {txt}" for i, txt in enumerate(ideas))
    best = yield ah.chat(
        "Below are several candidate AI‑image prompts.\n\n"
        f"{joined}\n\n"
        "Pick the **single most striking** prompt and repeat it verbatim."
    )

    # 4 · show the winner
    yield ah.log("\n🥇  Best prompt:\n" + best.strip())
