from aider import diffs

from ..dump import dump  # noqa: F401
from .base_coder import Coder
from .wholefile_func_prompts import WholeFileFunctionPrompts


class WholeFileFunctionCoder(Coder):
    functions = [
        dict(
            name="write_file",
            description="create or update one or more files",
            parameters=dict(
                type="object",
                required=["explanation", "files"],
                properties=dict(
                    explanation=dict(
                        type="string",
                        description=(
                            "Step by step plan for the changes to be made to the code (future"
                            " tense, markdown format)"
                        ),
                    ),
                    files=dict(
                        type="array",
                        items=dict(
                            type="object",
                            required=["path", "content"],
                            properties=dict(
                                path=dict(
                                    type="string",
                                    description="Path of file to write",
                                ),
                                content=dict(
                                    type="string",
                                    description="Content to write to the file",
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    ]

    def __init__(self, *args, **kwargs):
        raise RuntimeError("Deprecated, needs to be refactored to support get_edits/apply_edits")

        self.gpt_prompts = WholeFileFunctionPrompts()
        super().__init__(*args, **kwargs)

    def add_assistant_reply_to_cur_messages(self, edited):
        if edited:
            self.cur_messages += [
                dict(role="assistant", content=self.gpt_prompts.redacted_edit_message)
            ]
        else:
            self.cur_messages += [dict(role="assistant", content=self.partial_response_content)]

    def render_incremental_response(self, final=False):
        if self.partial_response_content:
            return self.partial_response_content

        args = self.parse_partial_args()

        if not args:
            return

        explanation = args.get("explanation")
        files = args.get("files", [])

        res = ""
        if explanation:
            res += f"{explanation}\n\n"

        for i, file_upd in enumerate(files):
            path = file_upd.get("path")
            if not path:
                continue
            content = file_upd.get("content")
            if not content:
                continue

            this_final = (i < len(files) - 1) or final
            res += self.live_diffs(path, content, this_final)

        return res

    def live_diffs(self, fname, content, final):
        lines = content.splitlines(keepends=True)

        # ending an existing block
        full_path = self.abs_root_path(fname)

        content = self.io.read_text(full_path)
        if content is None:
            orig_lines = []
        else:
            orig_lines = content.splitlines()

        show_diff = diffs.diff_partial_update(
            orig_lines,
            lines,
            final,
            fname=fname,
        ).splitlines()

        return "\n".join(show_diff)

    def _update_files(self):
        name = self.partial_response_function_call.get("name")
        if name and name != "write_file":
            raise ValueError(f'Unknown function_call name="{name}", use name="write_file"')

        args = self.parse_partial_args()
        if not args:
            return

        files = args.get("files", [])

        edited = set()
        for file_upd in files:
            path = file_upd.get("path")
            if not path:
                raise ValueError(f"Missing path parameter: {file_upd}")

            content = file_upd.get("content")
            if not content:
                raise ValueError(f"Missing content parameter: {file_upd}")

            if self.allowed_to_edit(path, content):
                edited.add(path)

        return edited
