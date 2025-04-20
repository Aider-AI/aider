from .udiff_coder import UnifiedDiffCoder


class UnifiedDiffSimpleCoder(UnifiedDiffCoder):
    """
    A coder that uses unified diff format for code modifications.
    This variant uses a simpler prompt that doesn't mention specific
    diff rules like using `@@ ... @@` lines or avoiding line numbers.
    """

    edit_format = "udiff-simple"

    # We can inherit the prompts if they are suitable or override them here
    # For now, let's assume the base UnifiedDiffPrompts are sufficient
    # If specific prompts are needed for the "simple" version, they would be defined here.
    # gpt_prompts = UnifiedDiffSimplePrompts()
