import json

from ..dump import dump  # noqa: F401
from .base_coder import Coder
from .editblock_coder import do_replace
from .editblock_func_prompts import EditBlockFunctionPrompts


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

    def update_cur_messages(self, content, edited):
        if self.partial_response_content:
            self.cur_messages += [dict(role="assistant", content=self.partial_response_content)]
        if self.partial_response_function_call:
            self.cur_messages += [
                dict(
                    role="assistant",
                    content=None,
                    function_call=self.partial_response_function_call,
                )
            ]

    def render_incremental_response(self, final=False):
        if self.partial_response_content:
            return self.partial_response_content

        args = self.parse_partial_args()
        res = json.dumps(args, indent=4)
        return res

    def update_files(self):
        name = self.partial_response_function_call.get("name")

        if name and name != "replace_lines":
            raise ValueError(f'Unknown function_call name="{name}", use name="replace_lines"')

        args = self.parse_partial_args()
        if not args:
            return

        edits = args.get("edits", [])

        edited = set()
        for edit in edits:
            path = get_arg(edit, "path")
            original = get_arg(edit, "original_lines")
            updated = get_arg(edit, "updated_lines")

            # gpt-3.5 returns lists even when instructed to return a string!
            if self.code_format == "list" or type(original) == list:
                original = "\n".join(original)
            if self.code_format == "list" or type(updated) == list:
                updated = "\n".join(updated)

            if original and not original.endswith("\n"):
                original += "\n"
            if updated and not updated.endswith("\n"):
                updated += "\n"

            full_path = self.allowed_to_edit(path)
            if not full_path:
                continue
            content = self.io.read_text(full_path)
            content = do_replace(full_path, content, original, updated)
            if content:
                self.io.write_text(full_path, content)
                edited.add(path)
                continue
            self.io.tool_error(f"Failed to apply edit to {path}")

        return edited


def get_arg(edit, arg):
    if arg not in edit:
        raise ValueError(f"Missing `{arg}` parameter: {edit}")
    return edit[arg]
