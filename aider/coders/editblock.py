import os
from pathlib import Path

from aider import utils

from ..editors import EditBlockPrompts
from .base import Coder


class EditBlockCoder(Coder):
    def __init__(self, *args, **kwargs):
        self.gpt_prompts = EditBlockPrompts()
        super().__init__(*args, **kwargs)

    def update_cur_messages(self, content, edited):
        self.cur_messages += [dict(role="assistant", content=content)]

    def update_files(self, content):
        # might raise ValueError for malformed ORIG/UPD blocks
        edits = list(utils.find_original_update_blocks(content))

        edited = set()
        for path, original, updated in edits:
            full_path = os.path.abspath(os.path.join(self.root, path))

            if full_path not in self.abs_fnames:
                if not Path(full_path).exists():
                    question = f"Allow creation of new file {path}?"  # noqa: E501
                else:
                    question = (
                        f"Allow edits to {path} which was not previously provided?"  # noqa: E501
                    )
                if not self.io.confirm_ask(question):
                    self.io.tool_error(f"Skipping edit to {path}")
                    continue

                if not Path(full_path).exists():
                    Path(full_path).parent.mkdir(parents=True, exist_ok=True)
                    Path(full_path).touch()

                self.abs_fnames.add(full_path)

                # Check if the file is already in the repo
                if self.repo:
                    tracked_files = set(self.repo.git.ls_files().splitlines())
                    relative_fname = self.get_rel_fname(full_path)
                    if relative_fname not in tracked_files and self.io.confirm_ask(
                        f"Add {path} to git?"
                    ):
                        self.repo.git.add(full_path)

            edited.add(path)
            if utils.do_replace(full_path, original, updated, self.dry_run):
                if self.dry_run:
                    self.io.tool_output(f"Dry run, did not apply edit to {path}")
                else:
                    self.io.tool_output(f"Applied edit to {path}")
            else:
                self.io.tool_error(f"Failed to apply edit to {path}")

        return edited
