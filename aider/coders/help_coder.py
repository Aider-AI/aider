from ..dump import dump  # noqa: F401
from .base_coder import Coder
from .help_prompts import HelpPrompts


class HelpCoder(Coder):
    """Interactive help and documentation about aider."""

    edit_format = "help"
    gpt_prompts = HelpPrompts()

    def get_edits(self, mode="update"):
        return []

    def apply_edits(self, edits):
        pass

    def run(self, input_text):
        """Run the help request and clear context after"""
        # Get the response
        response = super().run(input_text)
        
        # Clear the context after providing help
        self.cur_messages = []  # Clear current messages
        self.done_messages = [] # Clear history
        
        return response
        
    def run(self, input_text):
        """Run the help request and clear context after"""
        response = super().run(input_text)
        
        # Clear help-specific context after providing help
        self.cur_messages = []
        self.done_messages = []
        
        return response
