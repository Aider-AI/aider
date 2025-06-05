import difflib
import math
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

from aider import utils

from ..dump import dump  # noqa: F401
from .base_coder import Coder
from .editblock_prompts import EditBlockPrompts


class EditBlockCoder(Coder):
    """A coder that uses search/replace blocks for code modifications."""

    edit_format = "diff"
    gpt_prompts = EditBlockPrompts()

    def get_edits(self):
        content = self.partial_response_content

        # might raise ValueError for malformed ORIG/UPD blocks
        edits = list(
            utils.find_original_update_blocks(
                content,
                self.fence,
                self.get_inchat_relative_files(),
            )
        )

        self.shell_commands += [edit[1] for edit in edits if edit[0] is None]
        edits = [edit for edit in edits if edit[0] is not None]

        return edits

    def apply_edits_dry_run(self, edits):
        return self.apply_edits(edits, dry_run=True)

    def apply_edits(self, edits, dry_run=False):
        failed = []
        passed = []
        updated_edits = []

        for edit in edits:
            path, original, updated = edit
            full_path = self.abs_root_path(path)
            new_content = None

            if Path(full_path).exists():
                content = self.io.read_text(full_path)
                new_content = utils.do_replace(full_path, content, original, updated, self.fence)

            # If the edit failed, and
            # this is not a "create a new file" with an empty original...
            # https://github.com/Aider-AI/aider/issues/2258
            if not new_content and original.strip():
                # try patching any of the other files in the chat
                for other_full_path in self.abs_fnames:
                    if other_full_path == full_path:
                        continue
                    content = self.io.read_text(other_full_path)
                    new_content = utils.do_replace(other_full_path, content, original, updated, self.fence)
                    if new_content:
                        path = self.get_rel_fname(other_full_path)
                        break

            updated_edits.append((path, original, updated))

            if new_content:
                if not dry_run:
                    self.io.write_text(full_path, new_content)
                passed.append(edit)
            else:
                failed.append(edit)

        if dry_run:
            return updated_edits

        if not failed:
            return

        blocks = "block" if len(failed) == 1 else "blocks"

        res = f"# {len(failed)} SEARCH/REPLACE {blocks} failed to match!\n"
        for edit in failed:
            path, original, updated = edit

            full_path = self.abs_root_path(path)
            content = self.io.read_text(full_path)

            res += f"""
## SearchReplaceNoExactMatch: This SEARCH block failed to exactly match lines in {path}
<<<<<<< SEARCH
{original}=======
{updated}>>>>>>> REPLACE

"""
            did_you_mean = utils.find_similar_lines(original, content)
            if did_you_mean:
                res += f"""Did you mean to match some of these actual lines from {path}?

{self.fence[0]}
{did_you_mean}
{self.fence[1]}

"""

            if updated in content and updated:
                res += f"""Are you sure you need this SEARCH/REPLACE block?
The REPLACE lines are already in {path}!

"""
        res += (
            "The SEARCH section must exactly match an existing block of lines including all white"
            " space, comments, indentation, docstrings, etc\n"
        )
        if passed:
            pblocks = "block" if len(passed) == 1 else "blocks"
            res += f"""
# The other {len(passed)} SEARCH/REPLACE {pblocks} were applied successfully.
Don't re-send them.
Just reply with fixed versions of the {blocks} above that failed to match.
"""
        raise ValueError(res)


def main():
    history_md = Path(sys.argv[1]).read_text()
    if not history_md:
        return

    messages = utils.split_chat_history_markdown(history_md)

    for msg in messages:
        msg = msg["content"]
        edits = list(utils.find_original_update_blocks(msg))

        for fname, before, after in edits:
            print(fname)
            print(utils.strip_quoted_wrapping(before, fname))
            print("-" * 40)
            print(utils.strip_quoted_wrapping(after, fname))
            print("=" * 40)


if __name__ == "__main__":
    main()
