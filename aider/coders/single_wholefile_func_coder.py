from aider import diffs

from ..dump import dump  # noqa: F401
from .base_coder import Coder
from .single_wholefile_func_prompts import SingleWholeFileFunctionPrompts


class SingleWholeFileFunctionCoder(Coder):
    edit_format = "func"

    functions = [
        dict(
            name="write_file",
            description="write new content into the file",
            # strict=True,
            parameters=dict(
                type="object",
                properties=dict(
                    explanation=dict(
                        type="string",
                        description=(
                            "Step by step plan for the changes to be made to the code (future"
                            " tense, markdown format)"
                        ),
                    ),
                    content=dict(
                        type="string",
                        description="Content to write to the file",
                    ),
                ),
                required=["explanation", "content"],
                additionalProperties=False,
            ),
        ),
    ]

    def __init__(self, *args, **kwargs):
        self.gpt_prompts = SingleWholeFileFunctionPrompts()
        super().__init__(*args, **kwargs)

    def update_cur_messages(self, edited):
        if edited:
            self.cur_messages += [
                dict(role="assistant", content=self.gpt_prompts.redacted_edit_message)
            ]
        else:
            self.cur_messages += [dict(role="assistant", content=self.partial_response_content)]

    def render_incremental_response(self, final=False):
        res = ""
        if self.partial_response_content:
            res += self.partial_response_content

        args = self.parse_partial_args()

        if not args:
            return ""

        for k, v in args.items():
            res += "\n"
            res += f"{k}:\n"
            res += v

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

    def get_edits(self):
        chat_files = self.get_inchat_relative_files()
        assert len(chat_files) == 1, chat_files

        args = self.parse_partial_args()
        if not args:
            return []

        res = chat_files[0], args["content"]
        dump(res)
        return [res]

    def apply_edits(self, edits):
        for path, content in edits:
            full_path = self.abs_root_path(path)
            self.io.write_text(full_path, content)
