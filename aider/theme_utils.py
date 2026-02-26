from pygments.style import Style as PygmentsStyle
from pygments.util import ClassNotFound
from pygments.styles import get_style_by_name


class NoBackgroundStyle(PygmentsStyle):
    """A style wrapper that removes background colors from another style."""

    def __init__(self, base_style):
        # Get the base style's colors and settings
        self.styles = base_style.styles.copy()
        # Remove background colors from all token styles
        for token, style_string in self.styles.items():
            if style_string:
                # Split style into parts
                parts = style_string.split()
                # Filter out any bg:color settings
                parts = [p for p in parts if not p.startswith('bg:')]
                self.styles[token] = ' '.join(parts)


def get_code_theme(theme_name, no_background=False):
    """Get a Pygments style, optionally without backgrounds."""
    try:
        base_style = get_style_by_name(theme_name)
        if no_background:
            return NoBackgroundStyle(base_style)
        return base_style
    except ClassNotFound:
        # Fallback to default style
        base_style = get_style_by_name('default')
        if no_background:
            return NoBackgroundStyle(base_style)
        return base_style