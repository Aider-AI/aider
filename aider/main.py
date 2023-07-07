import os
import sys
from pathlib import Path

import configargparse
import git

from aider import __version__, models
from aider.coders import Coder
from aider.io import InputOutput


def get_git_root():
    try:
        repo = git.Repo(search_parent_directories=True)
        return repo.working_tree_dir
    except git.InvalidGitRepositoryError:
        return None


def main(args=None, input=None, output=None):
    if args is None:
        args = sys.argv[1:]

    git_root = get_git_root()

    conf_fname = Path(".aider.conf.yml")

    default_config_files = [conf_fname.resolve()]  # CWD
    if git_root:
        git_conf = Path(git_root) / conf_fname  # git root
        if git_conf not in default_config_files:
            default_config_files.append(git_conf)
    default_config_files.append(Path.home() / conf_fname)  # homedir
    default_config_files = list(map(str, default_config_files))

    parser = configargparse.ArgumentParser(
        description="aider is GPT powered coding in your terminal",
        add_config_file_help=True,
        default_config_files=default_config_files,
        config_file_parser_class=configargparse.YAMLConfigFileParser,
        auto_env_var_prefix="AIDER_",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show the version number and exit",
    )

    parser.add_argument(
        "-c",
        "--config",
        is_config_file=True,
        metavar="CONFIG_FILE",
        help=(
            "Specify the config file (default: search for .aider.conf.yml in git root, cwd"
            " or home directory)"
        ),
    )

    parser.add_argument(
        "files",
        metavar="FILE",
        nargs="*",
        help="a list of source code files (optional)",
    )
    default_input_history_file = (
        os.path.join(git_root, ".aider.input.history") if git_root else ".aider.input.history"
    )
    default_chat_history_file = (
        os.path.join(git_root, ".aider.chat.history.md") if git_root else ".aider.chat.history.md"
    )

    parser.add_argument(
        "--input-history-file",
        metavar="INPUT_HISTORY_FILE",
        default=default_input_history_file,
        help=f"Specify the chat input history file (default: {default_input_history_file})",
    )
    parser.add_argument(
        "--chat-history-file",
        metavar="CHAT_HISTORY_FILE",
        default=default_chat_history_file,
        help=f"Specify the chat history file (default: {default_chat_history_file})",
    )
    parser.add_argument(
        "--model",
        metavar="MODEL",
        default=models.GPT4.name,
        help=f"Specify the model to use for the main chat (default: {models.GPT4.name})",
    )
    parser.add_argument(
        "-3",
        action="store_const",
        dest="model",
        const=models.GPT35_16k.name,
        help=f"Use {models.GPT35_16k.name} model for the main chat (gpt-4 is better)",
    )
    parser.add_argument(
        "--edit-format",
        metavar="EDIT_FORMAT",
        default=None,
        help="Specify what edit format GPT should use (default depends on model)",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        default=True,
        help="Enable pretty, colorized output (default: True)",
    )
    parser.add_argument(
        "--no-pretty",
        action="store_false",
        dest="pretty",
        help="Disable pretty, colorized output",
    )
    parser.add_argument(
        "--no-stream",
        action="store_false",
        dest="stream",
        default=True,
        help="Disable streaming responses",
    )
    parser.add_argument(
        "--no-git",
        action="store_false",
        dest="git",
        default=True,
        help="Do not look for a git repo",
    )
    parser.add_argument(
        "--user-input-color",
        default="green",
        help="Set the color for user input (default: green)",
    )
    parser.add_argument(
        "--tool-output-color",
        default=None,
        help="Set the color for tool output (default: None)",
    )
    parser.add_argument(
        "--tool-error-color",
        default="red",
        help="Set the color for tool error messages (default: red)",
    )
    parser.add_argument(
        "--assistant-output-color",
        default="blue",
        help="Set the color for assistant output (default: blue)",
    )
    parser.add_argument(
        "--code-theme",
        default="default",
        help=(
            "Set the markdown code theme (default: default, other options include monokai,"
            " solarized-dark, solarized-light)"
        ),
    )
    parser.add_argument(
        "--apply",
        metavar="FILE",
        help="Apply the changes from the given file instead of running the chat (debug)",
    )
    parser.add_argument(
        "--auto-commits",
        action="store_true",
        dest="auto_commits",
        default=True,
        help="Enable auto commit of GPT changes (default: True)",
    )

    parser.add_argument(
        "--no-auto-commits",
        action="store_false",
        dest="auto_commits",
        help="Disable auto commit of GPT changes (implies --no-dirty-commits)",
    )
    parser.add_argument(
        "--dirty-commits",
        action="store_true",
        dest="dirty_commits",
        help="Enable commits when repo is found dirty",
        default=True,
    )
    parser.add_argument(
        "--no-dirty-commits",
        action="store_false",
        dest="dirty_commits",
        help="Disable commits when repo is found dirty",
    )
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="Specify the encoding to use when reading files (default: utf-8)",
    )
    parser.add_argument(
        "--openai-api-key",
        metavar="OPENAI_API_KEY",
        help="Specify the OpenAI API key",
        env_var="OPENAI_API_KEY",
    )
    parser.add_argument(
        "--openai-api-base",
        metavar="OPENAI_API_BASE",
        default="https://api.openai.com/v1",
        help="Specify the OpenAI API base endpoint (default: https://api.openai.com/v1)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without applying changes (default: False)",
        default=False,
    )
    parser.add_argument(
        "--show-diffs",
        action="store_true",
        help="Show diffs when committing changes (default: False)",
        default=False,
    )
    parser.add_argument(
        "--map-tokens",
        type=int,
        default=1024,
        help="Max number of tokens to use for repo map, use 0 to disable (default: 1024)",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Always say yes to every confirmation",
        default=None,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output",
        default=False,
    )
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
        dry_run=args.dry_run,
    )

    if not git_root and args.git:
        if io.confirm_ask("No git repo found, create one to track GPT's changes (recommended)?"):
            git.Repo.init(os.getcwd())
            io.tool_output("Git repository created in the current working directory.")

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
            io.tool_error(
                "No OpenAI API key provided. Use --openai-api-key or export OPENAI_API_KEY."
            )
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

    if args.dirty_commits:
        coder.commit(ask=True, which="repo_files")

    if args.apply:
        content = io.read_text(args.apply)
        if content is None:
            return
        coder.apply_updates(content)
        return

    io.tool_output("Use /help to see in-chat commands.")
    if args.message:
        io.tool_output()
        coder.run(with_message=args.message)
    else:
        coder.run()


if __name__ == "__main__":
    status = main()
    sys.exit(status)
