from .ask_prompts import AskPrompts
from .base_coder import Coder
from .editblock_coder import find_original_update_blocks


class AskCoder(Coder):
    """Ask questions about code without making any changes."""

    edit_format = "ask"
    gpt_prompts = AskPrompts()

    def get_edits(self):
        content = self.partial_response_content
        try:
            edits = list(find_original_update_blocks(content, self.fence))
        except ValueError:
            return []

        self.shell_commands += [edit[1] for edit in edits if edit[0] is None]

        return []
