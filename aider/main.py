import os
import sys
import git
import configargparse
from dotenv import load_dotenv
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

    load_dotenv()
    env_prefix = "AIDER_"

    default_config_files = [
        os.path.expanduser("~/.aider.conf.yml"),
    ]
    git_root = get_git_root()
    if git_root:
        default_config_files.insert(0, os.path.join(git_root, ".aider.conf.yml"))

    parser = configargparse.ArgumentParser(
        description="aider - chat with GPT about your code",
        add_config_file_help=True,
        default_config_files=default_config_files,
    )

    parser.add_argument(
        "files",
        metavar="FILE",
        nargs="*",
        help="a list of source code files (optional)",
    )
    parser.add_argument(
        "--input-history-file",
        metavar="INPUT_HISTORY_FILE",
        env_var=f"{env_prefix}INPUT_HISTORY_FILE",
        default=".aider.input.history",
        help="Specify the chat input history file (default: .aider.input.history)",
    )
    parser.add_argument(
        "--chat-history-file",
        metavar="CHAT_HISTORY_FILE",
        env_var=f"{env_prefix}CHAT_HISTORY_FILE",
        default=".aider.chat.history.md",
        help="Specify the chat history file (default: .aider.chat.history.md)",
    )
    parser.add_argument(
        "--model",
        metavar="MODEL",
        env_var=f"{env_prefix}MODEL",
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
        "--no-pretty",
        action="store_false",
        dest="pretty",
        env_var=f"{env_prefix}PRETTY",
        help="Disable pretty, colorized output",
        default=True,
    )
    parser.add_argument(
        "--apply",
        metavar="FILE",
        help="Apply the changes from the given file instead of running the chat (debug)",
    )
    parser.add_argument(
        "--no-auto-commits",
        action="store_false",
        dest="auto_commits",
        env_var=f"{env_prefix}AUTO_COMMITS",
        help="Disable auto commit of changes",
        default=True,
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
        env_var=f"{env_prefix}SHOW_DIFFS",
        help="Show diffs when committing changes (default: False)",
        default=False,
    )
    parser.add_argument(
        "--ctags",
        action="store_true",
        env_var=f"{env_prefix}CTAGS",
        help="Add ctags to the chat to help GPT understand the codebase (default: False)",
        default=False,
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

    io.tool(*sys.argv, log_only=True)

    coder = Coder(
        io,
        main_model=args.model,
        fnames=args.files,
        pretty=args.pretty,
        show_diffs=args.show_diffs,
        auto_commits=args.auto_commits,
        dry_run=args.dry_run,
        use_ctags=args.ctags,
        verbose=args.verbose,
    )
    if args.auto_commits:
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
