import io
import unittest

from pygments.token import Token
from rich.console import Console

from aider.mdstream import FallbackPygmentsSyntaxTheme, NoInsetMarkdown, get_code_theme


class TestCodeTheme(unittest.TestCase):
    def test_unstyled_token_falls_back_to_parent(self):
        theme = FallbackPygmentsSyntaxTheme("default")
        # The default Pygments style has no entry for YAML plain scalars
        plain = theme.get_style_for_token(Token.Literal.Scalar.Plain)
        self.assertEqual(plain, theme.get_style_for_token(Token.Literal))
        self.assertIsNotNone(plain.color)

    def test_rich_builtin_theme_passed_through(self):
        self.assertEqual(get_code_theme("ansi_dark"), "ansi_dark")

    def test_yaml_plain_scalar_has_foreground_color(self):
        buf = io.StringIO()
        console = Console(file=buf, force_terminal=True, color_system="truecolor", width=60)
        console.print(
            NoInsetMarkdown(
                "```yaml\nkey: text without quotes\n```", code_theme=get_code_theme("default")
            )
        )
        line = buf.getvalue().splitlines()[1]
        # The value must carry an explicit foreground color (38;2;...), not just the
        # light theme background, or it is invisible on light-on-dark terminals.
        self.assertIn("38;2;0;0;0;48;2;248;248;248mtext", line)


if __name__ == "__main__":
    unittest.main()
