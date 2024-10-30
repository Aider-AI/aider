import json
from typing import Dict, List, Optional, Union
from dataclasses import dataclass

from ..dump import dump  # noqa: F401
from .base_coder import Coder
from .editblock_coder import do_replace
from .editblock_func_prompts import EditBlockFunctionPrompts


class EditOperation:
    path: str
    original_lines: Union[str, List[str]]
    updated_lines: Union[str, List[str]]


class EditBlockFunctionCoder(Coder):
    functions = [
        dict(
            name="replace_lines",
            description="create or update one or more files",
            parameters=dict(
                type="object",
                required=["explanation", "edits"],
                properties=dict(
                    explanation=dict(
                        type="string",
                        description=(
                            "Step by step plan for the changes to be made to the code (future"
                            " tense, markdown format)"
                        ),
                    ),
                    edits=dict(
                        type="array",
                        items=dict(
                            type="object",
                            required=["path", "original_lines", "updated_lines"],
                            properties=dict(
                                path=dict(
                                    type="string",
                                    description="Path of file to edit",
                                ),
                                original_lines=dict(
                                    type="array",
                                    items=dict(
                                        type="string",
                                    ),
                                    description=(
                                        "A unique stretch of lines from the original file,"
                                        " including all whitespace, without skipping any lines"
                                    ),
                                ),
                                updated_lines=dict(
                                    type="array",
                                    items=dict(
                                        type="string",
                                    ),
                                    description="New content to replace the `original_lines` with",
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    ]

    def __init__(self, code_format, *args, **kwargs):
        raise RuntimeError("Deprecated, needs to be refactored to support get_edits/apply_edits")
        self.code_format = code_format

        if code_format == "string":
            original_lines = dict(
                type="string",
                description=(
                    "A unique stretch of lines from the original file, including all"
                    " whitespace and newlines, without skipping any lines"
                ),
            )
            updated_lines = dict(
                type="string",
                description="New content to replace the `original_lines` with",
            )

            self.functions[0]["parameters"]["properties"]["edits"]["items"]["properties"][
                "original_lines"
            ] = original_lines
            self.functions[0]["parameters"]["properties"]["edits"]["items"]["properties"][
                "updated_lines"
            ] = updated_lines

        self.gpt_prompts = EditBlockFunctionPrompts()
        super().__init__(*args, **kwargs)

    def render_incremental_response(self, final=False):
        if self.partial_response_content:
            return self.partial_response_content

        args = self.parse_partial_args()
        res = json.dumps(args, indent=4)
        return res

    def _process_edit_operation(self, edit: Dict) -> Optional[EditOperation]:
        """Process and validate a single edit operation"""
        try:
            path = get_arg(edit, "path")
            original = get_arg(edit, "original_lines") 
            updated = get_arg(edit, "updated_lines")

            original = self._normalize_lines(original)
            updated = self._normalize_lines(updated)

            return EditOperation(path=path, original_lines=original, updated_lines=updated)
        except ValueError as e:
            self.io.tool_error(f"Invalid edit operation: {e}")
            return None

    def _normalize_lines(self, content: Union[str, List[str]]) -> str:
        """Normalize content to string format with proper line endings"""
        if isinstance(content, list):
            content = "\n".join(content)
        if content and not content.endswith("\n"):
            content += "\n"
        return content

    def _update_files(self) -> Optional[set]:
        name = self.partial_response_function_call.get("name")
        if name and name != "replace_lines":
            raise ValueError(f'Unknown function_call name="{name}", use name="replace_lines"')

        args = self.parse_partial_args()
        if not args:
            return None

        return self._process_edits(args.get("edits", []))

    def _process_edits(self, edits: List[Dict]) -> set:
        """Process multiple edit operations"""
        edited = set()
        for edit in edits:
            edit_op = self._process_edit_operation(edit)
            if not edit_op:
                continue
                
            if self._apply_edit(edit_op):
                edited.add(edit_op.path)
                
        return edited

    def _apply_edit(self, edit_op: EditOperation) -> bool:
        """Apply a single edit operation to file"""
        full_path = self.allowed_to_edit(edit_op.path)
        if not full_path:
            return False

        content = self.io.read_text(full_path)
        updated_content = do_replace(
            full_path, 
            content,
            edit_op.original_lines,
            edit_op.updated_lines
        )

        if not updated_content:
            self.io.tool_error(f"Failed to apply edit to {edit_op.path}")
            return False

        self.io.write_text(full_path, updated_content)
        return True


def get_arg(edit, arg):
    if arg not in edit:
        raise ValueError(f"Missing `{arg}` parameter: {edit}")
    return edit[arg]
