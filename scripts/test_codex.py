import asyncio
from aider.providers.codex import CodexProvider


async def test():
    p = CodexProvider()
    async for event in p.run_turn("say hello"):
        print(event)


asyncio.run(test())
