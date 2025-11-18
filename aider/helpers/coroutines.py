import asyncio  # noqa: F401


def is_active(coroutine):
    if not coroutine or coroutine.done() or coroutine.cancelled():
        return False

    return True
