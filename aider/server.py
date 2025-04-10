import asyncio
import traceback

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from aider.main import main as cli_main


class ChatRequest(BaseModel):
    message: str
    stream: bool = True


class ChatResponse(BaseModel):
    content: str


async def process_generator(generator):
    """Convert the synchronous generator to an async one."""
    for chunk in generator:
        yield chunk
        await asyncio.sleep(0)


def create_app(coder):
    """Create a FastAPI application with a coder instance."""
    app = FastAPI(title="Aider API")

    @app.post("/chat")
    async def chat(request: ChatRequest):
        """Process a chat message and return the response from the coder."""
        try:
            if request.stream:
                generator = coder.run_stream(request.message)
                return StreamingResponse(process_generator(generator), media_type="text/plain")
            else:
                response = coder.run(with_message=request.message)
                return ChatResponse(content=response)
        except Exception as e:
            error_detail = f"{str(e)}\n{traceback.format_exc()}"
            raise HTTPException(status_code=500, detail=error_detail)

    return app


def start_server(argv, host="127.0.0.1", port=8000):
    """Start the FastAPI server, creating a new coder with the given args."""
    coder = cli_main(argv=argv, return_coder=True)
    app = create_app(coder)
    # Required to force the coder to return text from run and run_stream
    coder.stream = True
    coder.pretty = False
    uvicorn.run(app, host=host, port=port)
