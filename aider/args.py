#!/usr/bin/env python

import argparse
import os
import sys

import configargparse

from aider import __version__
from aider.args_formatter import (
    DotEnvFormatter,
    MarkdownHelpFormatter,
    YamlHelpFormatter,
)

from .dump import dump  # noqa: F401


def default_env_file(git_root):
    return os.path.join(git_root, ".env") if git_root else ".env"


def get_parser(default_config_files, git_root):
    parser = configargparse.ArgumentParser(
        description="aider is AI pair programming in your terminal",
        add_config_file_help=True,
        default_config_files=default_config_files,
        config_file_parser_class=configargparse.YAMLConfigFileParser,
        auto_env_var_prefix="AIDER_",
    )
    group = parser.add_argument_group("Main")
    group.add_argument(
        "files", metavar="FILE", nargs="*", help="files to edit with an LLM (optional)"
    )
    group.add_argument(
        "--openai-api-key",
        metavar="OPENAI_API_KEY",
        env_var="OPENAI_API_KEY",
        help="Specify the OpenAI API key",
    )
    group.add_argument(
        "--anthropic-api-key",
        metavar="ANTHROPIC_API_KEY",
        env_var="ANTHROPIC_API_KEY",
        help="Specify the Anthropic API key",
    )
    group.add_argument(
        "--model",
        metavar="MODEL",
        default=None,
        help="Specify the model to use for the main chat",
    )
    opus_model = "claude-3-opus-20240229"
    group.add_argument(
        "--opus",
        action="store_const",
        dest="model",
        const=opus_model,
        help=f"Use {opus_model} model for the main chat",
    )
    sonnet_model = "claude-3-5-sonnet-20241022"
    group.add_argument(
        "--sonnet",
        action="store_const",
        dest="model",
        const=sonnet_model,
        help=f"Use {sonnet_model} model for the main chat",
    )
    gpt_4_model = "gpt-4-0613"
    group.add_argument(
        "--4",
        "-4",
        action="store_const",
        dest="model",
        const=gpt_4_model,
        help=f"Use {gpt_4_model} model for the main chat",
    )
    gpt_4o_model = "gpt-4o-2024-08-06"
    group.add_argument(
        "--4o",
        action="store_const",
        dest="model",
        const=gpt_4o_model,
        help=f"Use {gpt_4o_model} model for the main chat",
    )
    gpt_4o_mini_model = "gpt-4o-mini"
    group.add_argument(
        "--mini",
        action="store_const",
        dest="model",
        const=gpt_4o_mini_model,
        help=f"Use {gpt_4o_mini_model} model for the main chat",
    )
    gpt_4_turbo_model = "gpt-4-1106-preview"
    group.add_argument(
        "--4-turbo",
        action="store_const",
        dest="model",
        const=gpt_4_turbo_model,
        help=f"Use {gpt_4_turbo_model} model for the main chat",
    )
    gpt_3_model_name = "gpt-3.5-turbo"
    group.add_argument(
        "--35turbo",
        "--35-turbo",
        "--3",
        "-3",
        action="store_const",
        dest="model",
        const=gpt_3_model_name,
        help=f"Use {gpt_3_model_name} model for the main chat",
    )
    deepseek_model = "deepseek/deepseek-coder"
    group.add_argument(
        "--deepseek",
        action="store_const",
        dest="model",
        const=deepseek_model,
        help=f"Use {deepseek_model} model for the main chat",
    )
    o1_mini_model = "o1-mini"
    group.add_argument(
        "--o1-mini",
        action="store_const",
        dest="model",
        const=o1_mini_model,
        help=f"Use {o1_mini_model} model for the main chat",
    )
    o1_preview_model = "o1-preview"
    group.add_argument(
        "--o1-preview",
        action="store_const",
        dest="model",
        const=o1_preview_model,
        help=f"Use {o1_preview_model} model for the main chat",
    )

    ##########
    group = parser.add_argument_group("Model Settings")
    group.add_argument(
        "--list-models",
        "--models",
        metavar="MODEL",
        help="List known models which match the (partial) MODEL name",
    )
    group.add_argument(
        "--openai-api-base",
        metavar="OPENAI_API_BASE",
        env_var="OPENAI_API_BASE",
        help="Specify the api base url",
    )
    group.add_argument(
        "--openai-api-type",
        metavar="OPENAI_API_TYPE",
        env_var="OPENAI_API_TYPE",
        help="Specify the api_type",
    )
    group.add_argument(
        "--openai-api-version",
        metavar="OPENAI_API_VERSION",
        env_var="OPENAI_API_VERSION",
        help="Specify the api_version",
    )
    group.add_argument(
        "--openai-api-deployment-id",
        metavar="OPENAI_API_DEPLOYMENT_ID",
        env_var="OPENAI_API_DEPLOYMENT_ID",
        help="Specify the deployment_id",
    )
    group.add_argument(
        "--openai-organization-id",
        metavar="OPENAI_ORGANIZATION_ID",
        env_var="OPENAI_ORGANIZATION_ID",
        help="Specify the OpenAI organization ID",
    )
    group.add_argument(
        "--model-settings-file",
        metavar="MODEL_SETTINGS_FILE",
        default=".aider.model.settings.yml",
        help="Specify a file with aider model settings for unknown models",
    )
    group.add_argument(
        "--model-metadata-file",
        metavar="MODEL_METADATA_FILE",
        default=".aider.model.metadata.json",
        help="Specify a file with context window and costs for unknown models",
    )
    group.add_argument(
        "--verify-ssl",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Verify the SSL cert when connecting to models (default: True)",
    )
    group.add_argument(
        "--edit-format",
        "--chat-mode",
        metavar="EDIT_FORMAT",
        default=None,
        help="Specify what edit format the LLM should use (default depends on model)",
    )
    group.add_argument(
        "--architect",
        action="store_const",
        dest="edit_format",
        const="architect",
        help="Use architect edit format for the main chat",
    )
    group.add_argument(
        "--weak-model",
        metavar="WEAK_MODEL",
        default=None,
        help=(
            "Specify the model to use for commit messages and chat history summarization (default"
            " depends on --model)"
        ),
    )
    group.add_argument(
        "--editor-model",
        metavar="EDITOR_MODEL",
        default=None,
        help="Specify the model to use for editor tasks (default depends on --model)",
    )
    group.add_argument(
        "--editor-edit-format",
        metavar="EDITOR_EDIT_FORMAT",
        default=None,
        help="Specify the edit format for the editor model (default: depends on editor model)",
    )
    group.add_argument(
        "--show-model-warnings",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Only work with models that have meta-data available (default: True)",
    )
    group.add_argument(
        "--max-chat-history-tokens",
        type=int,
        default=None,
        help=(
            "Soft limit on tokens for chat history, after which summarization begins."
            " If unspecified, defaults to the model's max_chat_history_tokens."
        ),
    )
    # This is a duplicate of the argument in the preparser and is a no-op by this time of
    # argument parsing, but it's here so that the help is displayed as expected.
    group.add_argument(
        "--env-file",
        metavar="ENV_FILE",
        default=default_env_file(git_root),
        help="Specify the .env file to load (default: .env in git root)",
    )

    ##########
    group = parser.add_argument_group("Cache Settings")
    group.add_argument(
        "--cache-prompts",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Enable caching of prompts (default: False)",
    )
    group.add_argument(
        "--cache-keepalive-pings",
        type=int,
        default=0,
        help="Number of times to ping at 5min intervals to keep prompt cache warm (default: 0)",
    )

    ##########
    group = parser.add_argument_group("Repomap Settings")
    group.add_argument(
        "--map-tokens",
        type=int,
        default=None,
        help="Suggested number of tokens to use for repo map, use 0 to disable (default: 1024)",
    )
    group.add_argument(
        "--map-refresh",
        choices=["auto", "always", "files", "manual"],
        default="auto",
        help=(
            "Control how often the repo map is refreshed. Options: auto, always, files, manual"
            " (default: auto)"
        ),
    )
    group.add_argument(
        "--map-multiplier-no-files",
        type=float,
        default=2,
        help="Multiplier for map tokens when no files are specified (default: 2)",
    )

    ##########
    group = parser.add_argument_group("History Files")
    default_input_history_file = (
        os.path.join(git_root, ".aider.input.history") if git_root else ".aider.input.history"
    )
    default_chat_history_file = (
        os.path.join(git_root, ".aider.chat.history.md") if git_root else ".aider.chat.history.md"
    )
    group.add_argument(
        "--input-history-file",
        metavar="INPUT_HISTORY_FILE",
        default=default_input_history_file,
        help=f"Specify the chat input history file (default: {default_input_history_file})",
    )
    group.add_argument(
        "--chat-history-file",
        metavar="CHAT_HISTORY_FILE",
        default=default_chat_history_file,
        help=f"Specify the chat history file (default: {default_chat_history_file})",
    )
    group.add_argument(
        "--restore-chat-history",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Restore the previous chat history messages (default: False)",
    )
    group.add_argument(
        "--llm-history-file",
        metavar="LLM_HISTORY_FILE",
        default=None,
        help="Log the conversation with the LLM to this file (for example, .aider.llm.history)",
    )

    ##########
    group = parser.add_argument_group("Output Settings")
    group.add_argument(
        "--dark-mode",
        action="store_true",
        help="Use colors suitable for a dark terminal background (default: False)",
        default=False,
    )
    group.add_argument(
        "--light-mode",
        action="store_true",
        help="Use colors suitable for a light terminal background (default: False)",
        default=False,
    )
    group.add_argument(
        "--pretty",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable/disable pretty, colorized output (default: True)",
    )
    group.add_argument(
        "--stream",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable/disable streaming responses (default: True)",
    )
    group.add_argument(
        "--user-input-color",
        default="#00cc00",
        help="Set the color for user input (default: #00cc00)",
    )
    group.add_argument(
        "--tool-output-color",
        default=None,
        help="Set the color for tool output (default: None)",
    )
    group.add_argument(
        "--tool-error-color",
        default="#FF2222",
        help="Set the color for tool error messages (default: #FF2222)",
    )
    group.add_argument(
        "--tool-warning-color",
        default="#FFA500",
        help="Set the color for tool warning messages (default: #FFA500)",
    )
    group.add_argument(
        "--assistant-output-color",
        default="#0088ff",
        help="Set the color for assistant output (default: #0088ff)",
    )
    group.add_argument(
        "--completion-menu-color",
        metavar="COLOR",
        default=None,
        help="Set the color for the completion menu (default: terminal's default text color)",
    )
    group.add_argument(
        "--completion-menu-bg-color",
        metavar="COLOR",
        default=None,
        help=(
            "Set the background color for the completion menu (default: terminal's default"
            " background color)"
        ),
    )
    group.add_argument(
        "--completion-menu-current-color",
        metavar="COLOR",
        default=None,
        help=(
            "Set the color for the current item in the completion menu (default: terminal's default"
            " background color)"
        ),
    )
    group.add_argument(
        "--completion-menu-current-bg-color",
        metavar="COLOR",
        default=None,
        help=(
            "Set the background color for the current item in the completion menu (default:"
            " terminal's default text color)"
        ),
    )
    group.add_argument(
        "--code-theme",
        default="default",
        help=(
            "Set the markdown code theme (default: default, other options include monokai,"
            " solarized-dark, solarized-light)"
        ),
    )
    group.add_argument(
        "--show-diffs",
        action="store_true",
        help="Show diffs when committing changes (default: False)",
        default=False,
    )

    ##########
    group = parser.add_argument_group("Git Settings")
    group.add_argument(
        "--git",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable/disable looking for a git repo (default: True)",
    )
    group.add_argument(
        "--gitignore",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable/disable adding .aider* to .gitignore (default: True)",
    )
    default_aiderignore_file = (
        os.path.join(git_root, ".aiderignore") if git_root else ".aiderignore"
    )
    group.add_argument(
        "--aiderignore",
        metavar="AIDERIGNORE",
        default=default_aiderignore_file,
        help="Specify the aider ignore file (default: .aiderignore in git root)",
    )
    group.add_argument(
        "--subtree-only",
        action="store_true",
        help="Only consider files in the current subtree of the git repository",
        default=False,
    )
    group.add_argument(
        "--auto-commits",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable/disable auto commit of LLM changes (default: True)",
    )
    group.add_argument(
        "--dirty-commits",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable/disable commits when repo is found dirty (default: True)",
    )
    group.add_argument(
        "--attribute-author",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Attribute aider code changes in the git author name (default: True)",
    )
    group.add_argument(
        "--attribute-committer",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Attribute aider commits in the git committer name (default: True)",
    )
    group.add_argument(
        "--attribute-commit-message-author",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Prefix commit messages with 'aider: ' if aider authored the changes (default: False)",
    )
    group.add_argument(
        "--attribute-commit-message-committer",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Prefix all commit messages with 'aider: ' (default: False)",
    )
    group.add_argument(
        "--commit",
        action="store_true",
        help="Commit all pending changes with a suitable commit message, then exit",
        default=False,
    )
    group.add_argument(
        "--commit-prompt",
        metavar="PROMPT",
        help="Specify a custom prompt for generating commit messages",
    )
    group.add_argument(
        "--dry-run",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Perform a dry run without modifying files (default: False)",
    )
    group.add_argument(
        "--skip-sanity-check-repo",
        action="store_true",
        help="Skip the sanity check for the git repository (default: False)",
        default=False,
    )
    group = parser.add_argument_group("Fixing and committing")
    group.add_argument(
        "--lint",
        action="store_true",
        help="Lint and fix provided files, or dirty files if none provided",
        default=False,
    )
    group.add_argument(
        "--lint-cmd",
        action="append",
        help=(
            'Specify lint commands to run for different languages, eg: "python: flake8'
            ' --select=..." (can be used multiple times)'
        ),
        default=[],
    )
    group.add_argument(
        "--auto-lint",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable/disable automatic linting after changes (default: True)",
    )
    group.add_argument(
        "--test-cmd",
        help="Specify command to run tests",
        default=[],
    )
    group.add_argument(
        "--auto-test",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Enable/disable automatic testing after changes (default: False)",
    )
    group.add_argument(
        "--test",
        action="store_true",
        help="Run tests and fix problems found",
        default=False,
    )

    ##########
    group = parser.add_argument_group("Other Settings")
    group.add_argument(
        "--file",
        action="append",
        metavar="FILE",
        help="specify a file to edit (can be used multiple times)",
    )
    group.add_argument(
        "--read",
        action="append",
        metavar="FILE",
        help="specify a read-only file (can be used multiple times)",
    )
    group.add_argument(
        "--vim",
        action="store_true",
        help="Use VI editing mode in the terminal (default: False)",
        default=False,
    )
    group.add_argument(
        "--chat-language",
        metavar="CHAT_LANGUAGE",
        default=None,
        help="Specify the language to use in the chat (default: None, uses system settings)",
    )
    group.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show the version number and exit",
    )
    group.add_argument(
        "--just-check-update",
        action="store_true",
        help="Check for updates and return status in the exit code",
        default=False,
    )
    group.add_argument(
        "--check-update",
        action=argparse.BooleanOptionalAction,
        help="Check for new aider versions on launch",
        default=True,
    )
    group.add_argument(
        "--install-main-branch",
        action="store_true",
        help="Install the latest version from the main branch",
        default=False,
    )
    group.add_argument(
        "--upgrade",
        "--update",
        action="store_true",
        help="Upgrade aider to the latest version from PyPI",
        default=False,
    )
    group.add_argument(
        "--apply",
        metavar="FILE",
        help="Apply the changes from the given file instead of running the chat (debug)",
    )
    group.add_argument(
        "--yes-always",
        action="store_true",
        help="Always say yes to every confirmation",
        default=None,
    )
    group.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output",
        default=False,
    )
    group.add_argument(
        "--show-repo-map",
        action="store_true",
        help="Print the repo map and exit (debug)",
        default=False,
    )
    group.add_argument(
        "--show-prompts",
        action="store_true",
        help="Print the system prompts and exit (debug)",
        default=False,
    )
    group.add_argument(
        "--exit",
        action="store_true",
        help="Do all startup activities then exit before accepting user input (debug)",
        default=False,
    )
    group.add_argument(
        "--message",
        "--msg",
        "-m",
        metavar="COMMAND",
        help=(
            "Specify a single message to send the LLM, process reply then exit (disables chat mode)"
        ),
    )
    group.add_argument(
        "--message-file",
        "-f",
        metavar="MESSAGE_FILE",
        help=(
            "Specify a file containing the message to send the LLM, process reply, then exit"
            " (disables chat mode)"
        ),
    )
    group.add_argument(
        "--encoding",
        default="utf-8",
        help="Specify the encoding for input and output (default: utf-8)",
    )
    group.add_argument(
        "-c",
        "--config",
        is_config_file=True,
        metavar="CONFIG_FILE",
        help=(
            "Specify the config file (default: search for .aider.conf.yml in git root, cwd"
            " or home directory)"
        ),
    )
    group.add_argument(
        "--gui",
        "--browser",
        action="store_true",
        help="Run aider in your browser",
        default=False,
    )
    group.add_argument(
        "--suggest-shell-commands",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable/disable suggesting shell commands (default: True)",
    )
    group.add_argument(
        "--fancy-input",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable/disable fancy input with history and completion (default: True)",
    )

    ##########
    group = parser.add_argument_group("Voice Settings")
    group.add_argument(
        "--voice-format",
        metavar="VOICE_FORMAT",
        default="wav",
        choices=["wav", "mp3", "webm"],
        help="Audio format for voice recording (default: wav). webm and mp3 require ffmpeg",
    )
    group.add_argument(
        "--voice-language",
        metavar="VOICE_LANGUAGE",
        default="en",
        help="Specify the language for voice using ISO 639-1 code (default: auto)",
    )

    return parser


def get_md_help():
    os.environ["COLUMNS"] = "70"
    sys.argv = ["aider"]
    parser = get_parser([], None)

    # This instantiates all the action.env_var values
    parser.parse_known_args()

    parser.formatter_class = MarkdownHelpFormatter

    return argparse.ArgumentParser.format_help(parser)


def get_sample_yaml():
    os.environ["COLUMNS"] = "100"
    sys.argv = ["aider"]
    parser = get_parser([], None)

    # This instantiates all the action.env_var values
    parser.parse_known_args()

    parser.formatter_class = YamlHelpFormatter

    return argparse.ArgumentParser.format_help(parser)


def get_sample_dotenv():
    os.environ["COLUMNS"] = "120"
    sys.argv = ["aider"]
    parser = get_parser([], None)

    # This instantiates all the action.env_var values
    parser.parse_known_args()

    parser.formatter_class = DotEnvFormatter

    return argparse.ArgumentParser.format_help(parser)


def main():
    arg = sys.argv[1] if len(sys.argv[1:]) else None

    if arg == "md":
        print(get_md_help())
    elif arg == "dotenv":
        print(get_sample_dotenv())
    else:
        print(get_sample_yaml())


if __name__ == "__main__":
    status = main()
    sys.exit(status)
