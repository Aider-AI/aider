from .udiff_prompts import UnifiedDiffPrompts


class UnifiedDiffSimplePrompts(UnifiedDiffPrompts):
    """
    Prompts for the UnifiedDiffSimpleCoder.
    Inherits from UnifiedDiffPrompts and can override specific prompts
    if a simpler wording is desired for this edit format.
    """

    # For now, we inherit all prompts. Override specific ones below if needed.
    # For example, to override the main_system prompt:
    # main_system = """
    # A simpler version of the main system prompt for udiff-simple.
    # """
    pass
