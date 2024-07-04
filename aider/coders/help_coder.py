from ..dump import dump  # noqa: F401
from .base_coder import Coder
from .help_prompts import HelpPrompts


class HelpCoder(Coder):
    edit_format = "help"

    def __init__(self, *args, **kwargs):
        self.gpt_prompts = HelpPrompts()
        super().__init__(*args, **kwargs)

    def get_edits(self, mode="update"):
        return []

    def apply_edits(self, edits):
        pass
