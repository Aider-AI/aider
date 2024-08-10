import unittest
from unittest.mock import Mock

from aider.coders import AskCoder
from aider.coders.ask_prompts import AskPrompts
from aider.coders.ask_prompts_aiden import AskPromptsAiden


class TestCoder(unittest.TestCase):
    def test_askcoder_prompt_variant(self):
        # Test with implicit default prompt variant
        coder = AskCoder(main_model=Mock(), io=Mock())
        assert isinstance(coder.gpt_prompts, AskPrompts)

        # Test with explicit default prompt variant
        coder = AskCoder(main_model=Mock(), io=Mock(), prompt_variant="default")
        assert isinstance(coder.gpt_prompts, AskPrompts)

        # Test with Aiden prompt variant
        coder = AskCoder(main_model=Mock(), io=Mock(), prompt_variant="aiden")
        assert isinstance(coder.gpt_prompts, AskPromptsAiden)

        # Test with non-existent prompt variant
        with self.assertRaises(ValueError):
            AskCoder(main_model=Mock(), io=Mock(), prompt_variant="non_existent")
