import argparse

class CustomHelpFormatter(argparse.HelpFormatter):
    def start_section(self, heading):
        super().start_section(f"## {heading}:")

    def _format_action(self, action):
        parts = []
        if action.help:
            parts.append(f"### --{action.dest}")
            parts.append(action.help)
            if action.default is not argparse.SUPPRESS:
                parts.append(f"Default: {action.default}")
        return "\n".join(parts)

    def _format_action_invocation(self, action):
        return ""

    def _format_args(self, action, default_metavar):
        return ""
