import argparse

from .dump import dump  # noqa: F401


class MarkdownHelpFormatter(argparse.HelpFormatter):
    def start_section(self, heading):
        super().start_section(f"## {heading}")

    def _format_usage(self, usage, actions, groups, prefix):
        res = super()._format_usage(usage, actions, groups, prefix)
        quote = "```\n"
        return quote + res + quote

    def _format_text(self, text):
        return ""

    def _format_action(self, action):
        parts = [""]

        metavar = action.metavar
        if not metavar and isinstance(action, argparse._StoreAction):
            metavar = "VALUE"

        if metavar:
            parts.append(f"### `--{action.dest} {metavar}`")
        else:
            parts.append(f"### `--{action.dest}`")
        if action.help:
            parts.append(action.help + "  ")

        if action.default not in (argparse.SUPPRESS, None):
            parts.append(f"Default: {action.default}  ")

        if action.env_var:
            parts.append(f"Environment variable: `{action.env_var}`  ")

        if len(action.option_strings) > 1:
            parts.append("Aliases:")
            for switch in action.option_strings:
                if metavar:
                    parts.append(f"  - `{switch} {metavar}`")
                else:
                    parts.append(f"  - `{switch}`")

        return "\n".join(parts) + "\n"

    def _format_action_invocation(self, action):
        return ""

    def _format_args(self, action, default_metavar):
        return ""
