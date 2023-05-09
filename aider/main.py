import os
import sys
import argparse
from dotenv import load_dotenv
from aider.coder import Coder

def main():
    load_dotenv()
    env_prefix = "AIDER_"
    parser = argparse.ArgumentParser(
        description="aider - chat with GPT about your code"
    )
    parser.add_argument(
        "files",
        metavar="FILE",
        nargs="+",
        help="a list of source code files",
    )
    parser.add_argument(
        "--history-file",
        metavar="HISTORY_FILE",
        default=os.environ.get(f"{env_prefix}HISTORY_FILE", ".aider.history"),
        help=f"Specify the history file (default: .aider.history, ${env_prefix}HISTORY_FILE)",
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
        help="Use gpt-3.5-turbo model for the main chat (basically won't work)",
    )
    parser.add_argument(
        "--no-pretty",
        action="store_false",
        dest="pretty",
        help=f"Disable pretty, colorized output (${env_prefix}PRETTY)",
        default=bool(int(os.environ.get(f"{env_prefix}PRETTY", 1))),
    )
    parser.add_argument(
        "--apply",
        metavar="FILE",
        help="Apply the changes from the given file instead of running the chat",
    )
    parser.add_argument(
        "--commit-dirty",
        action="store_true",
        help=f"On launch, commit dirty files w/o confirmation (default: False, ${env_prefix}COMMIT_DIRTY)",  # noqa: E501
        default=bool(int(os.environ.get(f"{env_prefix}COMMIT_DIRTY", 0))),
    )
    args = parser.parse_args()

    fnames = args.files
    pretty = args.pretty

    coder = Coder(args.model, fnames, pretty, args.history_file)
    coder.commit(ask=not args.commit_dirty, prefix="WIP: ")

    if args.apply:
        with open(args.apply, "r") as f:
            content = f.read()
        coder.update_files(content, inp="")
        return

    coder.run()


if __name__ == "__main__":
    status = main()
    sys.exit(status)
