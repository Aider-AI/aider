"""
hello_loop.py – sanity‑check macro.

Run with:
    /macro examples/hello_loop.py loops=5
"""

import aider.helpers as ah   # log / run / code / include

def main(ctx, **kwargs):
    # kwargs already contains all CLI key=value pairs
    yield ah.log(f"[macro] kwargs = {kwargs!r}")

    # Grab the number of loops (default=1)
    loops = int(kwargs.get("loops", 1))

    for i in range(1, loops + 1):
        yield ah.log(f"Hello! (loop {i}/{loops})")

    yield ah.log("🎉 Done!")
