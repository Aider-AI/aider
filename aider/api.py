from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from queue import Queue
import sys
import os

app = FastAPI()

# Store aider args globally so they can be set before starting uvicorn
AIDER_ARGS = []

class APIInputOutput:
    def __init__(self):
        self.current_response = []
        self.input_queue = Queue()
        self.coder = None
        self.pretty = False  # API mode doesn't need pretty output

    def tool_output(self, message="", log_only=False, bold=False):
        if not log_only:
            self.current_response.append({"type": "tool_output", "message": str(message)})

    def tool_error(self, message="", strip=True):
        self.current_response.append({"type": "error", "message": str(message)})

    def tool_warning(self, message="", strip=True):
        self.current_response.append({"type": "warning", "message": str(message)})

    def get_input(self, root, rel_fnames, addable_rel_fnames, commands, abs_read_only_fnames=None, edit_format=None):
        return self.input_queue.get()

    def print(self, message=""):
        self.current_response.append({"type": "print", "message": str(message)})

    def user_input(self, inp, log_only=True):
        if not log_only:
            self.current_response.append({"type": "user_input", "message": str(inp)})

    def append_chat_history(self, text, linebreak=False, blockquote=False, strip=True):
        # Only append blockquotes (system messages) here
        if blockquote:
            self.current_response.append({
                "type": "system",
                "message": str(text),
                "linebreak": linebreak,
                "blockquote": blockquote
            })

    def assistant_output(self, message, pretty=None):
        # This is the main method for AI responses
        self.current_response.append({
            "type": "assistant", 
            "message": str(message)
        })

    def rule(self):
        pass

    def confirm_ask(self, question, default="y", subject=None, explicit_yes_required=False, group=None, allow_never=False):
        return True  # Auto-confirm in API mode

    def add_to_input_history(self, inp):
        pass

    def read_text(self, filename, silent=False):
        try:
            with open(filename, 'r') as f:
                return f.read()
        except Exception as e:
            self.tool_error(f"Error reading {filename}: {e}")
            return None

    def write_text(self, filename, content):
        try:
            with open(filename, 'w') as f:
                f.write(content)
            return True
        except Exception as e:
            self.tool_error(f"Error writing {filename}: {e}")
            return False

    def get_assistant_mdstream(self):
        return None  # Disable streaming in API mode

class Message(BaseModel):
    content: str

def set_aider_args(args):
    """Set the aider arguments before starting the server"""
    global AIDER_ARGS
    AIDER_ARGS = args + ["--no-stream"]

@app.post("/init")
async def initialize_aider():
    from aider.main import main
    
    app.io = APIInputOutput()
    app.io.coder = main(AIDER_ARGS, input=None, output=None, return_coder=True, io=app.io)
    return {"status": "initialized"}

@app.post("/chat")
async def chat(message: Message):
    if not hasattr(app, "io") or not app.io.coder:
        raise HTTPException(status_code=400, detail="Aider not initialized")
    
    app.io.current_response = []
    app.io.input_queue.put(message.content)
    
    # Run one iteration of the chat loop
    app.io.coder.run(with_message=message.content)
    
    return {"responses": app.io.current_response}

@app.post("/stop")
async def stop_aider():
    if hasattr(app, "io"):
        app.io.input_queue.put("exit")
    return {"status": "stopped"}
