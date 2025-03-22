from .base_coder import Coder
from .context_prompts import ContextPrompts


class ContextCoder(Coder):
    """Identify which files need to be edited for a given request."""

    edit_format = "context"
    gpt_prompts = ContextPrompts()
