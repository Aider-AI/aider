import argparse

from aider import urls

from .dump import dump  # noqa: F401


class DotEnvFormatter(argparse.HelpFormatter):
    def start_section(self, heading):
        res = "\n\n"
        res += "#" * (len(heading) + 3)
        res += f"\n# {heading}"
        super().start_section(res)

    def _format_usage(self, usage, actions, groups, prefix):
        return ""

    def _format_text(self, text):
        return f"""
##########################################################
# Sample aider .env file.
# Place at the root of your git repo.
# Or use `aider --env <fname>` to specify.
##########################################################

#################
# LLM parameters:
#
# Include xxx_API_KEY parameters and other params needed for your LLMs.
# See {urls.llms} for details.

## OpenAI
#OPENAI_API_KEY=

## Anthropic
#ANTHROPIC_API_KEY=

##...
"""

    def _format_action(self, action):
        if not action.option_strings:
            return ""

        if not action.env_var:
            return

        parts = [""]

        default = action.default
        if default == argparse.SUPPRESS:
            default = ""
        elif isinstance(default, str):
            pass
        elif isinstance(default, list) and not default:
            default = ""
        elif action.default is not None:
            default = "true" if default else "false"
        else:
            default = ""

        if action.help:
            parts.append(f"## {action.help}")

        if action.env_var:
            env_var = action.env_var
            if default:
                parts.append(f"#{env_var}={default}\n")
            else:
                parts.append(f"#{env_var}=\n")

        return "\n".join(parts) + "\n"

    def _format_action_invocation(self, action):
        return ""

    def _format_args(self, action, default_metavar):
        return ""


class YamlHelpFormatter(argparse.HelpFormatter):
    def start_section(self, heading):
        res = "\n\n"
        res += "#" * (len(heading) + 3)
        res += f"\n# {heading}"
        super().start_section(res)

    def _format_usage(self, usage, actions, groups, prefix):
        return ""

    def _format_text(self, text):
        return """
##########################################################
# Sample .aider.conf.yml
# This file lists *all* the valid configuration entries.
# Place in your home dir, or at the root of your git repo.
##########################################################

# Note: You can only put OpenAI and Anthropic API keys in the yaml
# config file. Keys for all APIs can be stored in a .env file
# https://aider.chat/docs/config/dotenv.html

"""

    def _format_action(self, action):
        if not action.option_strings:
            return ""

        parts = [""]

        metavar = action.metavar
        if not metavar and isinstance(action, argparse._StoreAction):
            metavar = "VALUE"

        default = action.default
        if default == argparse.SUPPRESS:
            default = ""
        elif isinstance(default, str):
            pass
        elif isinstance(default, list) and not default:
            default = ""
        elif action.default is not None:
            default = "true" if default else "false"
        else:
            default = ""

        if action.help:
            parts.append(f"## {action.help}")

        for switch in action.option_strings:
            if switch.startswith("--"):
                break
        switch = switch.lstrip("-")

        if isinstance(action, argparse._StoreTrueAction):
            default = False
        elif isinstance(action, argparse._StoreConstAction):
            default = False

        if default is False:
            default = "false"
        if default is True:
            default = "true"

        if default:
            if "#" in default:
                parts.append(f'#{switch}: "{default}"\n')
            else:
                parts.append(f"#{switch}: {default}\n")
        elif action.nargs in ("*", "+") or isinstance(action, argparse._AppendAction):
            parts.append(f"#{switch}: xxx")
            parts.append("## Specify multiple values like this:")
            parts.append(f"#{switch}:")
            parts.append("#  - xxx")
            parts.append("#  - yyy")
            parts.append("#  - zzz")
        else:
            if switch.endswith("color"):
                parts.append(f'#{switch}: "xxx"\n')
            else:
                parts.append(f"#{switch}: xxx\n")

        ###
        # parts.append(str(action))

        return "\n".join(parts) + "\n"

    def _format_action_invocation(self, action):
        return ""

    def _format_args(self, action, default_metavar):
        return ""


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
        if not action.option_strings:
            return ""

        parts = [""]

        metavar = action.metavar
        if not metavar and isinstance(action, argparse._StoreAction):
            metavar = "VALUE"

        for switch in action.option_strings:
            if switch.startswith("--"):
                break

        if metavar:
            parts.append(f"### `{switch} {metavar}`")
        else:
            parts.append(f"### `{switch}`")
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
