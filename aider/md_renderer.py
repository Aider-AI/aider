from rich.markdown import Markdown, Padding
from rich.syntax import Syntax

from .theme_utils import get_code_theme

class CustomMarkdown(Markdown):
    """Custom Markdown renderer that handles code block backgrounds"""
    
    def __init__(self, text, code_theme="default", code_theme_no_background=False, **kwargs):
        self.code_theme_name = code_theme
        self.code_theme_no_background = code_theme_no_background
        super().__init__(text, **kwargs)

    def render_code_block(self, block, width):
        """Render a code block with optional background removal."""
        code = block.text.rstrip()
        lexer = block.lexer_name if hasattr(block, "lexer_name") else "default"
        
        theme = get_code_theme(self.code_theme_name, self.code_theme_no_background)
        syntax = Syntax(
            code,
            lexer,
            theme=theme,
            word_wrap=False,
            padding=0,
            background_color=None if self.code_theme_no_background else "default",
        )
        return Padding(syntax, pad=(0, 0))