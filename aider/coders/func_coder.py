import os

from aider import diffs

from .base_coder import Coder
from .func_prompts import FunctionPrompts


class FunctionCoder(Coder):
    functions = [
        dict(
            name="write_file",
            description="create or update a file",
            parameters=dict(
                type="object",
                required=["explanation", "file_path", "file_content"],
                properties=dict(
                    explanation=dict(
                        type="string",
                        description=(
                            "Explanation of the changes to be made to the code (markdown format)"
                        ),
                    ),
                    file_path=dict(
                        type="string",
                        description="Path of file to write",
                    ),
                    file_content=dict(
                        type="string",
                        description="Content to write to the file",
                    ),
                ),
            ),
        ),
    ]

    def __init__(self, *args, **kwargs):
        self.gpt_prompts = FunctionPrompts()
        super().__init__(*args, **kwargs)

    def update_cur_messages(self, content, edited):
        if edited:
            self.cur_messages += [
                dict(role="assistant", content=self.gpt_prompts.redacted_edit_message)
            ]
        else:
            self.cur_messages += [dict(role="assistant", content=content)]

    def modify_incremental_response(self):
        args = self.parse_partial_args()
        if not args:
            return

        path = args.get("file_path")
        explanation = args.get("explanation")
        content = args.get("file_content")

        res = ""

        if explanation:
            res += f"{explanation}\n"

        if not path:
            return res

        if path:
            if res:
                res += "\n"

            res += path + "\n"

        if not content:
            return res

        res += self.live_diffs(path, content)
        return res

    def live_diffs(self, fname, content):
        lines = content.splitlines(keepends=True)

        # ending an existing block
        full_path = os.path.abspath(os.path.join(self.root, fname))

        with open(full_path, "r") as f:
            orig_lines = f.readlines()

        show_diff = diffs.diff_partial_update(
            orig_lines,
            lines,
            final=True,
        ).splitlines()

        return "\n".join(show_diff)

    def update_files(self, content):
        pass
