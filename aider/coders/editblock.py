from ..editors import EditBlockPrompts
from .base import Coder


class EditBlockCoder(Coder):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gpt_prompts = EditBlockPrompts()
