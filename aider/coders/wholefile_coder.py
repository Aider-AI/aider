import os
from pathlib import Path

from aider import diffs

from .base_coder import Coder
from .wholefile_prompts import WholeFilePrompts


class WholeFileCoder(Coder):
    def __init__(self, *args, **kwargs):
        self.gpt_prompts = WholeFilePrompts()
        super().__init__(*args, **kwargs)

    def update_cur_messages(self, content, edited):
        if edited:
            self.cur_messages += [
                dict(role="assistant", content=self.gpt_prompts.redacted_edit_message)
            ]
        else:
            self.cur_messages += [dict(role="assistant", content=content)]

    def render_incremental_response(self, final):
        return self.update_files(mode="diff")

    def update_files(self, mode="update"):
        content = self.partial_response_content

        edited = set()
        chat_files = self.get_inchat_relative_files()

        output = []
        lines = content.splitlines(keepends=True)

        fname = None
        new_lines = []
        for i, line in enumerate(lines):
            if line.startswith("```"):
                if fname:
                    # ending an existing block
                    full_path = os.path.abspath(os.path.join(self.root, fname))

                    if mode == "diff":
                        with open(full_path, "r") as f:
                            orig_lines = f.readlines()

                        show_diff = diffs.diff_partial_update(
                            orig_lines,
                            new_lines,
                            final=True,
                        ).splitlines()
                        output += show_diff
                    else:
                        if self.allowed_to_edit(fname):
                            edited.add(fname)
                            if not self.dry_run:
                                new_lines = "".join(new_lines)
                                Path(full_path).write_text(new_lines)

                    fname = None
                    new_lines = []
                    continue

                # starting a new block
                if i == 0:
                    if len(chat_files) == 1:
                        fname = chat_files[0]
                    else:
                        # TODO: sense which file it is by diff size
                        raise ValueError("No filename provided before ``` block")
                else:
                    fname = lines[i - 1].strip()
            elif fname:
                new_lines.append(line)
            else:
                output.append(line)

        if mode == "diff":
            if fname:
                # ending an existing block
                full_path = os.path.abspath(os.path.join(self.root, fname))

                if mode == "diff":
                    with open(full_path, "r") as f:
                        orig_lines = f.readlines()

                    show_diff = diffs.diff_partial_update(
                        orig_lines,
                        new_lines,
                    ).splitlines()
                    output += show_diff

            return "\n".join(output)

        if fname and self.allowed_to_edit(fname):
            edited.add(fname)
            if not self.dry_run:
                new_lines = "".join(new_lines)
                Path(full_path).write_text(new_lines)

        return edited
