import aider.helpers as ah

def main(ctx, *, max_tries=10):
    max_tries = int(max_tries)
    for attempt in range(1, max_tries + 1):
        out = yield from ah.run("pytest -q", capture="t_out")
        if ctx["exit_code"] == 0:
            yield ah.log(f"✅ tests passed on try {attempt}")
            return
        yield ah.log(f"🔴 tests failed (try {attempt}) — fixing")
        yield ah.include("t_out")
        yield from ah.code("{Fix failing tests using t_out above}")
    yield ah.log("🚫 could not fix tests after max_tries")
