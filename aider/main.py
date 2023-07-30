import sys
from pathlib import Path

import openai

from aider import __version__
from aider.coders import Coder
from aider.io import InputOutput
from aider.repo import GitRepo
from aider.versioncheck import check_version

from .dump import dump  # noqa: F401


def setup_git(git_root, io):
    # ... (existing code)

def check_gitignore(git_root, io, ask=True):
    # ... (existing code)

def main(argv=None, input=None, output=None, force_git_root=None):
    # ... (existing code)

    # Configuring InputOutput
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

    # Processing files
    fnames = [str(Path(fn).resolve()) for fn in args.files]
    if len(args.files) > 1:
        good = all(not Path(fname).is_dir() for fname in args.files)
        if not good:
            io.tool_error("Provide either a single directory of a git repo, or a list of one or more files.")
            return 1

    git_dname = None
    if len(args.files) == 1:
        if Path(args.files[0]).is_dir() and args.git:
            git_dname = str(Path(args.files[0]).resolve())
            fnames = []

    # ... (existing code)

    # Configuring openai API settings
    openai.api_key = args.openai_api_key
    for attr in ("base", "type", "version", "deployment_id", "engine"):
        arg_key = f"openai_api_{attr}"
        val = getattr(args, arg_key)
        if val:
            mod_key = f"api_{attr}"
            setattr(openai, mod_key, val)
            io.tool_output(f"Setting openai.{mod_key}={val}")

    try:
        coder = Coder.create(
            main_model,
            args.edit_format,
            io,
            # ... (existing code)
        )
    except ValueError as err:
        io.tool_error(str(err))
        return 1

    # ... (existing code)


if __name__ == "__main__":
    status = main()
    sys.exit(status)
