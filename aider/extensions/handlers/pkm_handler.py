from ..handler import MutableContextHandler


pkm_system = """You are an expert personal knowledge manager.
Your goal is to help me organize my thoughts, ideas, and knowledge into a structured set of files.
You will be creating and editing markdown files.
When I share ideas with you, you should help me clarify them and then save them to the appropriate files.
You can ask me questions to better understand where to save the information or how to structure it.
Focus on creating a well-organized and easy-to-navigate knowledge base.
Do not write code unless I explicitly ask you to.
"""


class PkmHandler(MutableContextHandler):
    """
    Handler for Personal Knowledge Management mode.
    Switches to the PKM system prompt when this handler is active.
    """

    handler_name = "pkm"
    entrypoints = ["pre"]

    def __init__(self, main_coder, **kwargs):
        self.main_coder = main_coder

    def handle(self, messages):
        if self.main_coder.system_prompt_template != pkm_system:
            self.main_coder.system_prompt_template = pkm_system
            return True

        return False
