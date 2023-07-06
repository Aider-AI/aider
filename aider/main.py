# Importing necessary Python libraries and custom modules from the 'aider' package.
import os
import sys

import configargparse
import git

from aider import __version__, models
from aider.coders import Coder
from aider.io import InputOutput


# Function to get the root directory of the current Git repository
# This function is used to determine the root directory of the Git repository that the script is being run from
def get_git_root():
    try:
        # Attempt to find the root directory of the Git repository containing the script.
        repo = git.Repo(search_parent_directories=True)
        # If successful, return the root directory path.
        return repo.working_tree_dir
    except git.InvalidGitRepositoryError:
        # If unsuccessful, return None.
        return None


# Main function that runs the program
# This function is the entry point for the script. It takes command line arguments, sets up the necessary objects, and starts the main loop
def main(args=None, input=None, output=None):
    # Function to handle command-line arguments, set up the necessary objects, and start the main execution loop.

    if args is None:
        # If no arguments provided, take them from the command line.
        args = sys.argv[1:]

    # Get the root directory of the Git repository containing the script, if it exists.
    git_root = get_git_root()

    # Define the default configuration files.
    default_config_files = [
        os.path.expanduser("~/.aider.conf.yml"),
    ]

    if git_root:
        default_config_files.insert(0, os.path.join(git_root, ".aider.conf.yml"))

    # Initialize the argument parser.
    parser = configargparse.ArgumentParser(
        description="aider is GPT powered coding in your terminal",
        add_config_file_help=True,
        default_config_files=default_config_files,
        config_file_parser_class=configargparse.YAMLConfigFileParser,
        auto_env_var_prefix="AIDER_",
    )

    # --version option to print the version number of the program.
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show the version number and exit",
    )

    # --config option to specify the configuration file.
    parser.add_argument(
        "-c",
        "--config",
        is_config_file=True,
        metavar="CONFIG_FILE",
        help=(
            "Specify the config file (default: search for .aider.conf.yml in git root or home"
            " directory)"
        ),
    )

    # Positional argument to accept a list of source code files.
    parser.add_argument(
        "files",
        metavar="FILE",
        nargs="*",
        help="a list of source code files (optional)",
    )

    # Define the default input history file and chat history file.
    default_input_history_file = (
        os.path.join(git_root, ".aider.input.history") if git_root else ".aider.input.history"
    )
    default_chat_history_file = (
        os.path.join(git_root, ".aider.chat.history.md") if git_root else ".aider.chat.history.md"
    )

    # --input-history-file option to specify the chat input history file.
    parser.add_argument(
        "--input-history-file",
        metavar="INPUT_HISTORY_FILE",
        default=default_input_history_file,
        help=f"Specify the chat input history file (default: {default_input_history_file})",
    )

    # --chat-history-file option to specify the chat history file.
    parser.add_argument(
        "--chat-history-file",
        metavar="CHAT_HISTORY_FILE",
        default=default_chat_history_file,
        help=f"Specify the chat history file (default: {default_chat_history_file})",
    )

    # --model option to specify the GPT model to use for the main chat.
    parser.add_argument(
        "--model",
        metavar="MODEL",
        default=models.GPT4.name,
        help=f"Specify the model to use for the main chat (default: {models.GPT4.name})",
    )

    # -3 option that is a shortcut for using the GPT3.5 model for the main chat.
    parser.add_argument(
        "-3",
        action="store_const",
        dest="model",
        const=models.GPT35_16k.name,
        help=f"Use {models.GPT35_16k.name} model for the main chat (gpt-4 is better)",
    )

    # --edit-format option to specify the format that GPT should use for edits.
    parser.add_argument(
        "--edit-format",
        metavar="EDIT_FORMAT",
        default=None,
        help="Specify what edit format GPT should use (default depends on model)",
    )

    # --pretty option to enable pretty, colorized output.
    parser.add_argument(
        "--pretty",
        action="store_true",
        default=True,
        help="Enable pretty, colorized output (default: True)",
    )

    # --no-pretty option to disable pretty, colorized output.
    parser.add_argument(
        "--no-pretty",
        action="store_false",
        dest="pretty",
        help="Disable pretty, colorized output",
    )

    # --no-stream option to disable streaming responses.
    parser.add_argument(
        "--no-stream",
        action="store_false",
        dest="stream",
        default=True,
        help="Disable streaming responses",
    )

    # --no-git option to disable looking for a Git repository.
    parser.add_argument(
        "--no-git",
        action="store_false",
        dest="git",
        default=True,
        help="Do not look for a git repo",
    )

    # --user-input-color option to set the color for user input.
    parser.add_argument(
        "--user-input-color",
        default="green",
        help="Set the color for user input (default: green)",
    )

    # --tool-output-color option to set the color for tool output.
    parser.add_argument(
        "--tool-output-color",
        default=None,
        help="Set the color for tool output (default: None)",
    )

    # --tool-error-color option to set the color for tool error messages.
    parser.add_argument(
        "--tool-error-color",
        default="red",
        help="Set the color for tool error messages (default: red)",
    )

    # --assistant-output-color option to set the color for assistant output.
    parser.add_argument(
        "--assistant-output-color",
        default="blue",
        help="Set the color for assistant output (default: blue)",
    )

    # --code-theme option to set the markdown code theme.
    parser.add_argument(
        "--code-theme",
        default="default",
        help=(
            "Set the markdown code theme (default: default, other options include monokai,"
            " solarized-dark, solarized-light)"
        ),
    )

    # --apply option to apply the changes from a specific file and for debugging.
    parser.add_argument(
        "--apply",
        metavar="FILE",
        help="Apply the changes from the given file instead of running the chat (debug)",
    )

    # --auto-commits option to enable automatic commits of GPT changes.
    parser.add_argument(
        "--auto-commits",
        action="store_true",
        dest="auto_commits",
        default=True,
        help="Enable auto commit of GPT changes (default: True)",
    )

    # --no-auto-commits option to disable automatic commits of GPT changes.
    parser.add_argument(
        "--no-auto-commits",
        action="store_false",
        dest="auto_commits",
        help="Disable auto commit of GPT changes (implies --no-dirty-commits)",
    )

    # --dirty-commits option to enable commits when the repository found dirty.
    parser.add_argument(
        "--dirty-commits",
        action="store_true",
        dest="dirty_commits",
        help="Enable commits when repo is found dirty",
        default=True,
    )

    # --no-dirty-commits option to disable commits when the repository found dirty.
    parser.add_argument(
        "--no-dirty-commits",
        action="store_false",
        dest="dirty_commits",
        help="Disable commits when repo is found dirty",
    )

    # The --openai-api-key option to specify the OpenAI API key.
    parser.add_argument(
        "--openai-api-key",
        metavar="OPENAI_API_KEY",
        help="Specify the OpenAI API key",
        env_var="OPENAI_API_KEY",
    )

    # The --openai-api-base option to specify the OpenAI API base endpoint.
    parser.add_argument(
        "--openai-api-base",
        metavar="OPENAI_API_BASE",
        default="https://api.openai.com/v1",
        help="Specify the OpenAI API base endpoint (default: https://api.openai.com/v1)",
    )

    # --dry-run option to perform a dry run without actually applying any changes.
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without applying changes (default: False)",
        default=False,
    )

    # --show-diffs option to show the diffs when committing changes.
    parser.add_argument(
        "--show-diffs",
        action="store_true",
        help="Show diffs when committing changes (default: False)",
        default=False,
    )

    # --map-tokens option to specify the max number of tokens for the repository map.
    parser.add_argument(
        "--map-tokens",
        type=int,
        default=1024,
        help="Max number of tokens to use for repo map, use 0 to disable (default: 1024)",
    )

    # --yes option to always automatically say 'yes' to every confirmation.
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Always say yes to every confirmation",
        default=None,
    )

    # --verbose option to, if activated, enable verbose output.
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output",
        default=False,
    )

    # --message option to specify a single message to send to GPT, process the reply, and then exit.
    parser.add_argument(
        "--message",
        "--msg",
        "-m",
        metavar="COMMAND",
        help="Specify a single message to send GPT, process reply then exit (disables chat mode)",
    )

    args = parser.parse_args(args)

    io = InputOutput(
        args.pretty,
        args.yes,
        args.input_history_file,
        args.chat_history_file,
        input=input,
        output=output,
        user_input_color=args.user_input_color,
        tool_output_color=args.tool_output_color,
        tool_error_color=args.tool_error_color,
    )

    if args.verbose:
        show = parser.format_values()
        io.tool_output(show)
        io.tool_output("Option settings:")
        for arg, val in sorted(vars(args).items()):
            io.tool_output(f"  - {arg}: {val}")

    io.tool_output(*sys.argv, log_only=True)

    if not args.openai_api_key:
        if os.name == "nt":
            io.tool_error(
                "No OpenAI API key provided. Use --openai-api-key or setx OPENAI_API_KEY."
            )
        else:
            io.tool_error("No OpenAI API key provided. Use --openai-api-key or env OPENAI_API_KEY.")
        return 1

    main_model = models.Model(args.model)

    coder = Coder.create(
        main_model,
        args.edit_format,
        io,
        args.openai_api_key,
        args.openai_api_base,
        ##
        fnames=args.files,
        pretty=args.pretty,
        show_diffs=args.show_diffs,
        auto_commits=args.auto_commits,
        dirty_commits=args.dirty_commits,
        dry_run=args.dry_run,
        map_tokens=args.map_tokens,
        verbose=args.verbose,
        assistant_output_color=args.assistant_output_color,
        code_theme=args.code_theme,
        stream=args.stream,
        use_git=args.git,
    )

    # If the dirty_commits argument is true, the script commits any changes in the repository files
    # This is useful for keeping track of changes made by the script
    if args.dirty_commits:
        coder.commit(ask=True, which="repo_files")

    # If an apply argument is provided, the script applies the changes from the given file and then exits
    # This is useful for testing and debugging
    if args.apply:
        with open(args.apply, "r") as f:
            content = f.read()
        coder.apply_updates(content)
        return

    io.tool_output("Use /help to see in-chat commands.")

    # If a message argument is provided, the script sends that message to the GPT model and processes the reply
    # Otherwise, it starts the main loop of the script
    if args.message:
        io.tool_output()
        coder.run(with_message=args.message)
    else:
        coder.run()


# Point of entry when the script is run from the command line.
if __name__ == "__main__":
    status = main()
    sys.exit(status)
