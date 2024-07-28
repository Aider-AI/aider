from ..dump import dump  # noqa: F401
from .base_coder import Coder
from .help_prompts import HelpPrompts


class HelpCoder(Coder):
    """A coder that provides help and documentation."""
    edit_format = "help"
    gpt_prompts = HelpPrompts()

    def get_edits(self, mode="update"):
        return []

    def apply_edits(self, edits):
        pass
