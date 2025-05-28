import json
import logging
import os
import ssl
import time
import traceback

from typing import List, Tuple
from uuid import UUID, uuid4

from fastapi_sessions.backends.implementations import InMemoryBackend
from pydantic import BaseModel, Field
from session_data import SessionData, SessionPrompt
from fastapi.exception_handlers import http_exception_handler


from fastapi import Cookie, FastAPI, HTTPException, Response, WebSocket, WebSocketDisconnect, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from gpt_engineer.applications.cli.cli_agent import CliAgent
from gpt_engineer.applications.cli.main import (
    _main_async,
    handle_graph_mode,
    init_agent,
    init_ai,
    load_env_if_needed,
    process_prompt,
)
from gpt_engineer.core.ai import AI
from gpt_engineer.core.default.disk_memory import DiskMemory
from gpt_engineer.core.default.paths import memory_path

async def exception_handler(request, exc: Exception):
    """
    This is a wrapper to the default HTTPException handler of FastAPI.
    This function will be called when a HTTPException is explicitly raised.
    """
    logger.debug(request)
    logger.debug(exc)
    return await http_exception_handler(request, exc)

backend = InMemoryBackend[UUID, SessionData]()

app = FastAPI()
app.add_exception_handler(Exception, exception_handler)
# ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

# Enable logging
logger = logging.getLogger("uvicorn.error")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

# Load LLM environment variables
load_env_if_needed()
model: str = os.environ.get("MODEL_NAME", "gpt-4o")

# Maps session ID to a tuple of AI and CliAgent instances
ai_agent_map = {}


def get_ai_agent_from_session(
    session_id: str, model: str, project_path: str, memory: DiskMemory
) -> Tuple[AI, CliAgent]:
    """
    Retrieve the AI and agent instances associated with the given session ID.
    """
    if session_id not in ai_agent_map:
        # Create a new AI instance
        ai = init_ai(
            model=model,
            temperature=0.1,
            azure_endpoint="",
            llm_via_clipboard=False,
            use_cache=False,
            to_std_out=False,
        )
        # Create a new agent instance
        memory = DiskMemory(memory_path(project_path))
        agent = init_agent(
            ai=ai,
            project_path=project_path,
            memory=memory,
            use_custom_preprompts=False,
            clarify_mode=False,
            lite_mode=False,
            self_heal_mode=False,
        )
        # Store the AI and agent instances in the map
        ai_agent_map[session_id] = ai, agent
    else:
        # Retrieve the existing AI agent instance
        ai, agent = ai_agent_map[session_id]

    return ai, agent


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for handling real-time communication with the client.
    Accepts incoming messages, processes them, and sends responses back to the client.
    """
    logger.debug("Request for websocket")
    await websocket.accept()
    try:
        while True:
            request = await websocket.receive_text()
            request_obj = json.loads(request)
            session_id = request_obj["session_id"]
            project_path = request_obj["project_path"]
            prompt = request_obj["prompt"]
            file_patterns = request_obj.get("file_patterns", ["*"])
            exclude_dirs = request_obj.get("exclude_dirs", [])
            exclude_hidden = request_obj.get("exclude_hidden", True)
            graph_mode = request_obj.get("graph_mode", True)

            if session_id is None:
                await websocket.send_text("Session ID is required.")
                continue
            if project_path is None:
                await websocket.send_text("Project path is required.")
                continue
            if prompt is None:
                await websocket.send_text("Prompt is required.")
                continue

            memory = DiskMemory(memory_path(project_path))
            ai, agent = get_ai_agent_from_session(
                session_id, model, project_path, memory
            )

            if graph_mode:
                checkpoints_db_path = os.path.join(
                    project_path, ".gpteng", "checkpoints.db"
                )
                await handle_graph_mode(
                    project_path=project_path,
                    ai=ai,
                    improve_mode=True,
                    clarify_mode=False,
                    use_custom_preprompts=False,
                    checkpoints_db=checkpoints_db_path,
                    websocket=websocket,
                    prompt=prompt,
                )
            else:
                await process_prompt(
                    ai=ai,
                    agent=agent,
                    memory=memory,
                    improve_mode=True,
                    project_path=project_path,
                    prompt_file=None,
                    entrypoint_prompt_file=None,
                    image_directory=None,
                    no_execution=False,
                    skip_file_selection=True,
                    diff_timeout=30,
                    file_patterns = ["*"],
                    exclude_dirs = [".git", "__pycache__", ".gradle", "node_modules"],
                    exclude_hidden = True,
                    http_mode=True,
                    http_prompt=prompt,
                    http_file_patterns=file_patterns,
                    http_exclude_dirs=exclude_dirs,
                    http_exclude_hidden=exclude_hidden,
                    websocket=websocket,
                )

            await websocket.send_text(
                "CodeDroid agent has finished processing the request."
            )

    except WebSocketDisconnect:
        print("Client disconnected")  # Log the disconnection
        # Perform any necessary cleanup (e.g., remove the client from a list)
    except HTTPException as e:
        logger.warning(e)
    finally:  # Important for cleanup
        # Ensure resources are cleaned up.
        pass


class CreateRequest(BaseModel):
    prompt: str
    project_path: str
    graph_mode: bool = Field(
        False, description="Whether to use the graph implementation"
    )


@app.post("/create", status_code=status.HTTP_201_CREATED)
async def create_request(
    request: CreateRequest, response: Response, codedroid: str = Cookie(default=None)
):
    # Current current time in nanoseconds
    current_time_ns = time.time_ns()

    # Check if cookie was sent by client
    cookie_present = False
    if codedroid:
        cookie_present = True

    # Call gpt-engineer CLI main function
    await _main_async(
        project_path=request.project_path,
        model=model,
        temperature=0.1,
        improve_mode=False,
        lite_mode=False,
        clarify_mode=False,
        llm_via_clipboard=False,
        azure_endpoint="",
        no_execution=False,
        sysinfo=False,
        http_mode=True,
        http_prompt=request.prompt,
        persistent_mode=False,
        graph_mode=request.graph_mode,
    )

    new_session = False
    session_data = None
    if cookie_present:
        # Attempt to read session data from the backend using the UUID from the cookie
        session = UUID(codedroid)
        session_data = await backend.read(session)

    if not cookie_present or session_data is None:
        # If no cookie or session ID is not found, then generate new session ID and data
        session = uuid4()
        session_data = SessionData()
        new_session = True

    # Create a new session prompt and append it to the session data
    session_prompt = SessionPrompt(timestamp=current_time_ns, prompt=request.prompt)
    session_data.prompts.append(session_prompt)

    for p in session_data.prompts:
        print("------------------------------------------------")
        print("Timestamp: ", p.timestamp)
        print("Prompt: ", p.prompt)

    # need to call backend.update if exists
    if new_session:
        await backend.create(session, session_data)
    else:
        await backend.update(session, session_data)

    str(session)

    json_str = jsonable_encoder(
        {"message": "Request received", "prompt": request.prompt}
    )
    response = JSONResponse(content=json_str)
    # Pass back session ID in cookie
    response.set_cookie(
        key="codedroid", value=str(session), max_age=172800, httponly=True
    )
    return response


class ImproveRequest(BaseModel):
    prompt: str
    files: List[str] = Field(
        default_factory=lambda: ["*"],
        description="file pattern like  ['*.py', 'README.md']",
    )
    project_path: str
    exclude_dirs: List[str] = Field(
        default_factory=lambda: [
            ".git",
            "__pycache__",
            ".gradle",
            "node_modules",
            "preprompts",
        ],
        description="directory to exclude",
    )
    exclude_hidden: bool = Field(True, description="exclude hidden files/directories")
    graph_mode: bool = Field(
        False, description="Whether to use the graph implementation"
    )


@app.post("/improve", status_code=status.HTTP_201_CREATED)
async def improve_request(
    request: ImproveRequest, response: Response, codedroid: str = Cookie(default=None)
):
    # Record current timestamp and check session cookie
    current_time_ns = time.time_ns()
    cookie_present = bool(codedroid)

    try:
        await _main_async(
            project_path=request.project_path,
            model=model,
            temperature=0.1,
            improve_mode=True,
            lite_mode=False,
            clarify_mode=False,
            llm_via_clipboard=False,
            azure_endpoint="",
            no_execution=False,
            sysinfo=False,
            diff_timeout=30,
            http_mode=True,
            http_prompt=request.prompt,
            http_file_patterns=request.files,
            http_exclude_dirs=request.exclude_dirs,
            http_exclude_hidden=request.exclude_hidden,
            persistent_mode=False,
            graph_mode=request.graph_mode,
        )

        session, session_data, new_session = await handle_session(
            codedroid, cookie_present, backend
        )

        session_data.prompts.append(
            SessionPrompt(
                timestamp=current_time_ns,
                prompt=f"[IMPROVE] {request.prompt}",
            )
        )

        await update_session(session, session_data, new_session, backend)

        return JSONResponse(content={"message": "Improvement applied"})

    except Exception as e:
        # Handle errors and return formatted response
        logger.exception("Improve failed")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Improvement failed",
                "details": str(e),
                "stacktrace": traceback.format_exc(),
            },
        )


async def handle_session(codedroid, cookie_present, backend):
    session_data = None
    if cookie_present:
        session = UUID(codedroid)
        session_data = await backend.read(session)

    if not cookie_present or not session_data:
        return uuid4(), SessionData(), True
    return session, session_data, False


async def update_session(session, session_data, new_session, backend):
    if new_session:
        await backend.create(session, session_data)
    else:
        await backend.update(session, session_data)


