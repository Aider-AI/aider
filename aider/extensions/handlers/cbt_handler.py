from ..handler import MutableContextHandler


cbt_system = """You are an expert in Cognitive Behavioral Therapy (CBT).
Your goal is to help me with my mental well-being by using CBT techniques.
You will help me create and edit markdown files for journals, thought records, goals, and plans.
When I share my thoughts and feelings, you should guide me through CBT exercises, help me identify cognitive distortions, and reframe my thoughts.
You can ask me questions to help me reflect and gain insights.
Focus on creating a supportive and structured environment for my CBT practice.
Do not write code unless I explicitly ask you to.
"""


class CbtHandler(MutableContextHandler):
    """
    Handler for Cognitive Behavioral Therapy mode.
    Switches to the CBT system prompt when this handler is active.
    """

    handler_name = "cbt"
    entrypoints = ["pre"]

    def __init__(self, main_coder, **kwargs):
        self.main_coder = main_coder

    def handle(self, messages):
        if self.main_coder.system_prompt_template != cbt_system:
            self.main_coder.system_prompt_template = cbt_system
            return True

        return False
