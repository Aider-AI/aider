from .udiff_coder import UnifiedDiffCoder
from .udiff_simple_prompts import UnifiedDiffSimplePrompts


class UnifiedDiffSimpleCoder(UnifiedDiffCoder):
    """
    A coder that uses unified diff format for code modifications.
    This variant uses a simpler prompt that doesn't mention specific
    diff rules like using `@@ ... @@` lines or avoiding line numbers.
    """

    edit_format = "udiff-simple"

    gpt_prompts = UnifiedDiffSimplePrompts()
