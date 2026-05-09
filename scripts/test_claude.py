import asyncio

from aider.providers.claude_code import ClaudeCodeProvider


async def test():
    p = ClaudeCodeProvider()
    async for event in p.run_turn("say hello"):
        print(event)


asyncio.run(test())
