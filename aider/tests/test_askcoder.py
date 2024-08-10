import pytest
from unittest.mock import Mock

from aider.coders import AskCoder
from aider.coders.ask_prompts import AskPrompts
from aider.coders.ask_prompts_aiden import AskPrompts as AskPromptsAiden

def test_askcoder_prompt_variant():
    # Test with default prompt variant
    coder = AskCoder(main_model=Mock(), io=Mock(), prompt_variant="default")
    assert isinstance(coder.gpt_prompts, AskPrompts)

    # Test with Aiden prompt variant
    coder = AskCoder(main_model=Mock(), io=Mock(), prompt_variant="aiden")
    assert isinstance(coder.gpt_prompts, AskPromptsAiden)

    # Test with non-existent prompt variant
    with pytest.raises(ValueError):
        AskCoder(main_model=Mock(), io=Mock(), prompt_variant="non_existent")
