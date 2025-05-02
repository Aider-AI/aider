"""
examples/hello_loop.py
Tiny sanity‑check macro that loops N times
-----------------------------------------

Run with:
    /macro examples/hello_loop.py loops=3
"""

import aider.helpers as ah          # <-- helper API

def main(ctx, *, loops: int = 1):
    loops = int(loops)              # kwargs arrive as int/float/str
    for i in range(1, loops + 1):
        yield ah.log(f"Hello! (loop {i}/{loops})")
    yield ah.log("🎉 Done!")
