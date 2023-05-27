import os
import sys
import git
import configargparse
from aider.coder import Coder
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

    default_config_files = [
        os.path.expanduser("~/.aider.conf.yml"),
    ]
    if git_root:
        default_config_files.insert(0, os.path.join(git_root, ".aider.conf.yml"))

    parser = configargparse.ArgumentParser(
        description="aider - chat with GPT about your code",
        add_config_file_help=True,
        default_config_files=default_config_files,
        config_file_parser_class=configargparse.YAMLConfigFileParser,
        auto_env_var_prefix="AIDER_",
    )

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
        default="gpt-4",
        help="Specify the model to use for the main chat (default: gpt-4)",
    )
    parser.add_argument(
        "-3",
        action="store_const",
        dest="model",
        const="gpt-3.5-turbo",
        help="Use gpt-3.5-turbo model for the main chat (not advised)",
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
        "--apply",
        metavar="FILE",
        help="Apply the changes from the given file instead of running the chat (debug)",
    )
    parser.add_argument(
        "--auto-commits",
        action="store_true",
        dest="auto_commits",
        default=True,
        help="Enable auto commit of changes (default: True)",
    )

    parser.add_argument(
        "--no-auto-commits",
        action="store_false",
        dest="auto_commits",
        help="Disable auto commit of changes",
    )
    parser.add_argument(
        "--dirty-commits",
        action="store_true",
        dest="dirty_commits",
        help="Enable dirty commit of changes",
        default=True,
    )
    parser.add_argument(
        "--no-dirty-commits",
        action="store_false",
        dest="dirty_commits",
        help="Disable dirty commit of changes",
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
        "--ctags",
        type=lambda x: (str(x).lower() == "true"),
        nargs="?",
        const=True,
        default=None,
        help=(
            "Add ctags to the chat to help GPT understand the codebase (default: check for ctags"
            " executable)"
        ),
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Always say yes to every confirmation",
        default=False,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output",
        default=False,
    )
    args = parser.parse_args(args)

    io = InputOutput(
        args.pretty,
        args.yes,
        args.input_history_file,
        args.chat_history_file,
        input=input,
        output=output,
    )

    if args.verbose:
        show = parser.format_values()
        io.tool(show)
        io.tool("Option settings:")
        for arg, val in sorted(vars(args).items()):
            io.tool(f"  - {arg}: {val}")

    io.tool(*sys.argv, log_only=True)

    coder = Coder(
        io,
        main_model=args.model,
        fnames=args.files,
        pretty=args.pretty,
        show_diffs=args.show_diffs,
        auto_commits=args.auto_commits,
        dirty_commits=args.dirty_commits,
        dry_run=args.dry_run,
        use_ctags=args.ctags,
        verbose=args.verbose,
    )
    if args.dirty_commits:
        coder.commit(ask=True, prefix="wip: ", which="repo_files")

    if args.apply:
        with open(args.apply, "r") as f:
            content = f.read()
        coder.update_files(content, inp="")
        return

    coder.run()


if __name__ == "__main__":
    status = main()
    sys.exit(status)
