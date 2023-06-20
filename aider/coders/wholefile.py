from ..editors import WholeFilePrompts
from .base import Coder


class WholeFileCoder(Coder):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gpt_prompts = WholeFilePrompts()
