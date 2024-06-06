import argparse

from .dump import dump  # noqa: F401

class MarkdownHelpFormatter(argparse.HelpFormatter):
    def start_section(self, heading):
        super().start_section(f"## {heading}")

    def _format_action(self, action):
        parts = [""]

        #action: _StoreAction(option_strings=['--message', '--msg', '-m'], dest='message', nargs=None, const=None, default=None, type=None, choices=None, required=False, help='Specify a single message to send the LLM, process reply then exit (disables chat mode)', metavar='COMMAND')
        dump(action)

        metavar = action.metavar
        if not metavar and isinstance(action, argparse._StoreAction):
            metavar = 'VALUE'

        if metavar:
            parts.append(f"### --{action.dest} {metavar}")
        else:
            parts.append(f"### --{action.dest}")
        if action.help:
            parts.append(action.help)

        if action.default is not argparse.SUPPRESS:
            parts.append(f"- Default: {action.default}")

        if len(action.option_strings) > 1:
            parts.append("- Aliases:")
            for switch in action.option_strings:
                if metavar:
                    parts.append(f"  - {switch} {metavar}")
                else:
                    parts.append(f"  - {switch}")

        if action.env_var:
            parts.append(f"- Env: {action.env_var}")

        return "\n".join(parts) + '\n'

    def _format_action_invocation(self, action):
        return ""

    def _format_args(self, action, default_metavar):
        return ""
