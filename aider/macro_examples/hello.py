"""
hello_macro.py ― sanity check for the /macro engine.
✅ Expected behaviour:
   1. Logs “Hello, macro!” to the chat.
   2. Runs `echo "working"` in your shell and shows the output.
   3. Finishes after exactly one loop.
"""

import aider.helpers as ah

def main(ctx, *, loops: int | str = 1):
    loops = int(loops)            # <‑‑ add this line

    for i in range(loops):
        yield ah.log(f"👋 Hello, macro! (loop {i+1}/{loops})")
        out = yield from ah.run('echo "working"', capture="msg")
        yield ah.log(f"🔧 shell returned: {out.strip()}")
        yield ah.include("msg")

    yield ah.log("🎉 Done!")

