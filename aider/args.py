import argparse
import os

import configargparse

from aider import __version__, models


def get_parser(default_config_files, git_root):
    parser = configargparse.ArgumentParser(
        description="aider is GPT powered coding in your terminal",
        add_config_file_help=True,
        default_config_files=default_config_files,
        config_file_parser_class=configargparse.YAMLConfigFileParser,
        auto_env_var_prefix="AIDER_",
    )

    ##########
    group = parser.add_argument_group("Main")
    group.add_argument(
        "files",
        metavar="FILE",
        nargs="*",
        help="files to edit with an LLM (optional)",
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
        help="Specify the OpenAI API key",
    )
    default_model = models.DEFAULT_MODEL_NAME
    group.add_argument(
        "--model",
        metavar="MODEL",
        default=default_model,
        help=f"Specify the model to use for the main chat (default: {default_model})",
    )
    opus_model = "claude-3-opus-20240229"
    group.add_argument(
        "--opus",
        action="store_const",
        dest="model",
        const=opus_model,
        help=f"Use {opus_model} model for the main chat",
    )
    sonnet_model = "claude-3-sonnet-20240229"
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
    gpt_4_turbo_model = "gpt-4-turbo"
    group.add_argument(
        "--4-turbo-vision",
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

    ##########
    group = parser.add_argument_group("Model Settings")
    group.add_argument(
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
        "--edit-format",
        metavar="EDIT_FORMAT",
        default=None,
        help="Specify what edit format the LLM should use (default depends on model)",
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
        "--show-model-warnings",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Only work with models that have meta-data available (default: True)",
    )
    group.add_argument(
        "--map-tokens",
        type=int,
        default=1024,
        help="Max number of tokens to use for repo map, use 0 to disable (default: 1024)",
    )
    default_env_file = os.path.join(git_root, ".env") if git_root else ".env"
    group.add_argument(
        "--env-file",
        metavar="ENV_FILE",
        default=default_env_file,
        help="Specify the .env file to load (default: .env in git root)",
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
        help="Set the color for tool error messages (default: red)",
    )
    group.add_argument(
        "--assistant-output-color",
        default="#0088ff",
        help="Set the color for assistant output (default: #0088ff)",
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
        "--dry-run",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Perform a dry run without modifying files (default: False)",
    )
    group.add_argument(
        "--commit",
        action="store_true",
        help="Commit all pending changes with a suitable commit message, then exit",
        default=False,
    )

    ##########
    group = parser.add_argument_group("Other Settings")
    group.add_argument(
        "--voice-language",
        metavar="VOICE_LANGUAGE",
        default="en",
        help="Specify the language for voice using ISO 639-1 code (default: auto)",
    )
    group.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show the version number and exit",
    )
    group.add_argument(
        "--check-update",
        action="store_true",
        help="Check for updates and return status in the exit code",
        default=False,
    )
    group.add_argument(
        "--skip-check-update",
        action="store_true",
        help="Skips checking for the update when the program runs",
    )
    group.add_argument(
        "--apply",
        metavar="FILE",
        help="Apply the changes from the given file instead of running the chat (debug)",
    )
    group.add_argument(
        "--yes",
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

    return parser
