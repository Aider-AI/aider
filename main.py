import os
import sys
import argparse
from dotenv import load_dotenv
from coder import Coder


def main():
    load_dotenv()
    env_prefix = "CODER_"
    parser = argparse.ArgumentParser(description="Chat with GPT about code")
    parser.add_argument(
        "files",
        metavar="FILE",
        nargs="+",
        help="a list of source code files",
    )
    parser.add_argument(
        "--history-file",
        metavar="HISTORY_FILE",
        default=os.environ.get("CODER_HISTORY_FILE", ".coder.history"),
        help="Specify the history file (default: .coder.history)",
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
        help="Use gpt-3.5-turbo model for the main chat",
    )
    parser.add_argument(
        "-4",
        action="store_const",
        dest="model",
        const="gpt-4",
        help="Use gpt-4 model for the main chat",
    )
    parser.add_argument(
        "--no-pretty",
        action="store_false",
        dest="pretty",
        help="Disable prettyd output of GPT responses",
        default=bool(int(os.environ.get(env_prefix + "PRETTY", 1))),
    )
    parser.add_argument(
        "--apply",
        metavar="FILE",
        help="Apply the changes from the given file instead of running the chat",
    )
    parser.add_argument(
        "--commit-dirty",
        action="store_true",
        help="Commit dirty files without confirmation (env: CODER_COMMIT_DIRTY)",
        default=bool(int(os.environ.get(env_prefix + "COMMIT_DIRTY", 0))),
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