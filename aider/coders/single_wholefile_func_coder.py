from aider import diffs

from ..dump import dump  # noqa: F401
from .base_coder import Coder
from .single_wholefile_func_prompts import SingleWholeFileFunctionPrompts


class SingleWholeFileFunctionCoder(Coder):
    functions = [
        dict(
            name="write_file",
            description="write new content into the file",
            parameters=dict(
                type="object",
                required=["explanation", "content"],
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

    def get_context_from_history(self, history):
        context = ""
        if history:
            context += "# Context:\n"
            for msg in history:
                if msg["role"] == "user":
                    context += msg["role"].upper() + ": " + msg["content"] + "\n"
        return context

    def render_incremental_response(self, final=False):
        if self.partial_response_content:
            return self.partial_response_content

        args = self.parse_partial_args()

        return str(args)

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

    def update_files(self):
        name = self.partial_response_function_call.get("name")
        if name and name != "write_file":
            raise ValueError(f'Unknown function_call name="{name}", use name="write_file"')

        args = self.parse_partial_args()
        if not args:
            return

        content = args["content"]
        path = self.get_inchat_relative_files()[0]
        if self.allowed_to_edit(path, content):
            return set([path])

        return set()
