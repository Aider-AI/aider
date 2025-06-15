import os
import json
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from ..dump import dump  # noqa: F401
from .base_coder import Coder
from .morph_prompts import MorphPrompts


class MorphCoder(Coder):
    """A coder that uses a chat model to generate update snippets and morph to apply them."""

    edit_format = "morph"
    gpt_prompts = MorphPrompts()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Initialize morph client
        self.morph_client = None
        morph_api_key = os.environ.get('MORPH_API_KEY')
        if morph_api_key and OpenAI:
            self.morph_client = OpenAI(
                api_key=morph_api_key,
                base_url='https://api.morphllm.com/v1'
            )
        elif not morph_api_key:
            self.io.tool_warning("MORPH_API_KEY environment variable not set. Morph edit format will not work.")
        elif not OpenAI:
            self.io.tool_warning("OpenAI package not installed. Install with: pip install openai")

    def get_edits(self):
        content = self.partial_response_content

        chat_files = self.get_inchat_relative_files()
        
        edits = []
        lines = content.splitlines(keepends=True)

        fname = None
        new_lines = []
        for i, line in enumerate(lines):
            if line.startswith(self.fence[0]) or line.startswith(self.fence[1]):
                if fname is not None:
                    # ending an existing block
                    update_snippet = "".join(new_lines)
                    edits.append((fname, update_snippet))
                    fname = None
                    new_lines = []
                    continue

                # fname==None ... starting a new block
                if i > 0:
                    fname = lines[i - 1].strip()
                    fname = fname.strip("*")  # handle **filename.py**
                    fname = fname.rstrip(":")
                    fname = fname.strip("`")
                    fname = fname.lstrip("#")
                    fname = fname.strip()

                    # Issue #1232
                    if len(fname) > 250:
                        fname = ""

                    # Did gpt prepend a bogus dir? It especially likes to
                    # include the path/to prefix from the one-shot example in
                    # the prompt.
                    if fname and fname not in chat_files and Path(fname).name in chat_files:
                        fname = Path(fname).name

                if not fname:  # blank line? or ``` was on first line i==0
                    if len(chat_files) == 1:
                        fname = chat_files[0]
                    else:
                        # TODO: sense which file it is by diff size
                        raise ValueError(
                            f"No filename provided before {self.fence[0]} in update snippet"
                        )

            elif fname is not None:
                new_lines.append(line)

        if fname:
            update_snippet = "".join(new_lines)
            edits.append((fname, update_snippet))

        return edits

    def apply_edits(self, edits):
        if not self.morph_client:
            self.io.tool_error("Morph client not available. Cannot apply morph edits.")
            return

        for path, update_snippet in edits:
            full_path = self.abs_root_path(path)
            
            try:
                # Read the original file content
                if Path(full_path).exists():
                    original_code = self.io.read_text(full_path)
                else:
                    original_code = ""

                # Use Morph's fast apply API to generate the updated code
                response = self.morph_client.chat.completions.create(
                    model="morph-v2",
                    messages=[
                        {
                            "role": "user",
                            "content": f"<code>{original_code}</code>\n<update>{update_snippet}</update>"
                        }
                    ],
                    stream=False
                )
                
                updated_code = response.choices[0].message.content
                
                # Write the updated content back to the file
                self.io.write_text(full_path, updated_code)
                
                if self.verbose:
                    self.io.tool_output(f"Successfully applied morph edit to {path}")
                    
            except Exception as error:
                error_msg = f"Failed to apply morph edit to {path}: {error}"
                
                # Provide more specific error guidance
                if "api_key" in str(error).lower():
                    error_msg += "\nCheck your MORPH_API_KEY environment variable."
                elif "rate_limit" in str(error).lower():
                    error_msg += "\nMorph API rate limit exceeded. Please wait and retry."
                elif "network" in str(error).lower() or "connection" in str(error).lower():
                    error_msg += "\nNetwork error connecting to Morph API."
                
                self.io.tool_error(error_msg)
                raise ValueError(error_msg)

    def render_incremental_response(self, final):
        # For incremental display, just show the content as-is
        return self.partial_response_content 