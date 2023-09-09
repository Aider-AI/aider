import argparse
import os
import sys
from pathlib import Path

import configargparse
import git
import openai

from aider import __version__, models
from aider.coders import Coder
from aider.io import InputOutput
from aider.repo import GitRepo
from aider.versioncheck import check_version

from .dump import dump  # noqa: F401


def get_git_root():
    """Try and guess the git repo, since the conf.yml can be at the repo root"""
    try:
        repo = git.Repo(search_parent_directories=True)
        return repo.working_tree_dir
    except git.InvalidGitRepositoryError:
        return None


def guessed_wrong_repo(io, git_root, fnames, git_dname):
    """After we parse the args, we can determine the real repo. Did we guess wrong?"""

    try:
        check_repo = Path(GitRepo(io, fnames, git_dname).root).resolve()
    except FileNotFoundError:
        return

    # we had no guess, rely on the "true" repo result
    if not git_root:
        return str(check_repo)

    git_root = Path(git_root).resolve()
    if check_repo == git_root:
        return

    return str(check_repo)


def setup_git(git_root, io):
    if git_root:
        return git_root

    if not io.confirm_ask("No git repo found, create one to track GPT's changes (recommended)?"):
        return

    git_root = str(Path.cwd().resolve())

    check_gitignore(git_root, io, False)

    repo = git.Repo.init(git_root)
    global_git_config = git.GitConfigParser([str(Path.home() / ".gitconfig")], read_only=True)
    with repo.config_writer() as git_config:
        if not global_git_config.has_option("user", "name"):
            git_config.set_value("user", "name", "Your Name")
            io.tool_error('Update git name with: git config --global user.name "Your Name"')
        if not global_git_config.has_option("user", "email"):
            git_config.set_value("user", "email", "you@example.com")
            io.tool_error('Update git email with: git config --global user.email "you@example.com"')

    io.tool_output("Git repository created in the current working directory.")

    return repo.working_tree_dir


def check_gitignore(git_root, io, ask=True):
    if not git_root:
        return

    pat = ".aider*"

    gitignore_file = Path(git_root) / ".gitignore"
    if gitignore_file.exists():
        content = io.read_text(gitignore_file)
        if pat in content.splitlines():
            return
    else:
        content = ""

    if ask and not io.confirm_ask(f"Add {pat} to .gitignore (recommended)?"):
        return

    if content and not content.endswith("\n"):
        content += "\n"
    content += pat + "\n"
    io.write_text(gitignore_file, content)

    io.tool_output(f"Added {pat} to .gitignore")


def main(argv=None, input=None, output=None, force_git_root=None):
    if argv is None:
        argv = sys.argv[1:]

    if force_git_root:
        git_root = force_git_root
    else:
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

    ##########
    core_group = parser.add_argument_group("Main")
    core_group.add_argument(
        "files",
        metavar="FILE",
        nargs="*",
        help="the directory of a git repo, or a list of files to edit with GPT (optional)",
    )
    core_group.add_argument(
        "--openai-api-key",
        metavar="OPENAI_API_KEY",
        help="Specify the OpenAI API key",
        env_var="OPENAI_API_KEY",
    )
    core_group.add_argument(
        "--model",
        metavar="MODEL",
        default=models.GPT4.name,
        help=f"Specify the model to use for the main chat (default: {models.GPT4.name})",
    )
    core_group.add_argument(
        "--skip-model-availability-check",
        metavar="SKIP_MODEL_AVAILABILITY_CHECK",
        default=False,
        help="Override to skip model availability check (default: False)",
    )
    core_group.add_argument(
        "-3",
        action="store_const",
        dest="model",
        const=models.GPT35_16k.name,
        help=f"Use {models.GPT35_16k.name} model for the main chat (gpt-4 is better)",
    )
    core_group.add_argument(
        "--voice-language",
        metavar="VOICE_LANGUAGE",
        default="en",
        help="Specify the language for voice using ISO 639-1 code (default: auto)",
    )

    ##########
    model_group = parser.add_argument_group("Advanced Model Settings")
    model_group.add_argument(
        "--openai-api-base",
        metavar="OPENAI_API_BASE",
        help="Specify the openai.api_base (default: https://api.openai.com/v1)",
    )
    model_group.add_argument(
        "--openai-api-type",
        metavar="OPENAI_API_TYPE",
        help="Specify the openai.api_type",
    )
    model_group.add_argument(
        "--openai-api-version",
        metavar="OPENAI_API_VERSION",
        help="Specify the openai.api_version",
    )
    model_group.add_argument(
        "--openai-api-deployment-id",
        metavar="OPENAI_API_DEPLOYMENT_ID",
        help="Specify the deployment_id arg to be passed to openai.ChatCompletion.create()",
    )
    model_group.add_argument(
        "--openai-api-engine",
        metavar="OPENAI_API_ENGINE",
        help="Specify the engine arg to be passed to openai.ChatCompletion.create()",
    )
    model_group.add_argument(
        "--edit-format",
        metavar="EDIT_FORMAT",
        default=None,
        help="Specify what edit format GPT should use (default depends on model)",
    )
    model_group.add_argument(
        "--map-tokens",
        type=int,
        default=1024,
        help="Max number of tokens to use for repo map, use 0 to disable (default: 1024)",
    )

    ##########
    history_group = parser.add_argument_group("History Files")
    default_input_history_file = (
        os.path.join(git_root, ".aider.input.history") if git_root else ".aider.input.history"
    )
    default_chat_history_file = (
        os.path.join(git_root, ".aider.chat.history.md") if git_root else ".aider.chat.history.md"
    )
    history_group.add_argument(
        "--input-history-file",
        metavar="INPUT_HISTORY_FILE",
        default=default_input_history_file,
        help=f"Specify the chat input history file (default: {default_input_history_file})",
    )
    history_group.add_argument(
        "--chat-history-file",
        metavar="CHAT_HISTORY_FILE",
        default=default_chat_history_file,
        help=f"Specify the chat history file (default: {default_chat_history_file})",
    )

    ##########
    output_group = parser.add_argument_group("Output Settings")
    output_group.add_argument(
        "--dark-mode",
        action="store_true",
        help="Use colors suitable for a dark terminal background (default: False)",
        default=False,
    )
    output_group.add_argument(
        "--light-mode",
        action="store_true",
        help="Use colors suitable for a light terminal background (default: False)",
        default=False,
    )
    output_group.add_argument(
        "--pretty",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable/disable pretty, colorized output (default: True)",
    )
    output_group.add_argument(
        "--stream",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable/disable streaming responses (default: True)",
    )
    output_group.add_argument(
        "--user-input-color",
        default="#00cc00",
        help="Set the color for user input (default: #00cc00)",
    )
    output_group.add_argument(
        "--tool-output-color",
        default=None,
        help="Set the color for tool output (default: None)",
    )
    output_group.add_argument(
        "--tool-error-color",
        default="#FF2222",
        help="Set the color for tool error messages (default: red)",
    )
    output_group.add_argument(
        "--assistant-output-color",
        default="#0088ff",
        help="Set the color for assistant output (default: #0088ff)",
    )
    output_group.add_argument(
        "--code-theme",
        default="default",
        help=(
            "Set the markdown code theme (default: default, other options include monokai,"
            " solarized-dark, solarized-light)"
        ),
    )
    output_group.add_argument(
        "--show-diffs",
        action="store_true",
        help="Show diffs when committing changes (default: False)",
        default=False,
    )

    ##########
    git_group = parser.add_argument_group("Git Settings")
    git_group.add_argument(
        "--git",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable/disable looking for a git repo (default: True)",
    )
    git_group.add_argument(
        "--auto-commits",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable/disable auto commit of GPT changes (default: True)",
    )
    git_group.add_argument(
        "--dirty-commits",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable/disable commits when repo is found dirty (default: True)",
    )
    git_group.add_argument(
        "--dry-run",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Enable/disable performing a dry run without modifying files (default: False)",
    )

    ##########
    other_group = parser.add_argument_group("Other Settings")
    other_group.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show the version number and exit",
    )
    other_group.add_argument(
        "--apply",
        metavar="FILE",
        help="Apply the changes from the given file instead of running the chat (debug)",
    )
    other_group.add_argument(
        "--yes",
        action="store_true",
        help="Always say yes to every confirmation",
        default=None,
    )
    other_group.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output",
        default=False,
    )
    other_group.add_argument(
        "--show-repo-map",
        action="store_true",
        help="Print the repo map and exit (debug)",
        default=False,
    )
    other_group.add_argument(
        "--message",
        "--msg",
        "-m",
        metavar="COMMAND",
        help="Specify a single message to send GPT, process reply then exit (disables chat mode)",
    )
    other_group.add_argument(
        "-c",
        "--config",
        is_config_file=True,
        metavar="CONFIG_FILE",
        help=(
            "Specify the config file (default: search for .aider.conf.yml in git root, cwd"
            " or home directory)"
        ),
    )

    args = parser.parse_args(argv)

    if args.dark_mode:
        args.user_input_color = "#32FF32"
        args.tool_error_color = "#FF3333"
        args.assistant_output_color = "#00FFFF"
        args.code_theme = "monokai"

    if args.light_mode:
        args.user_input_color = "green"
        args.tool_error_color = "red"
        args.assistant_output_color = "blue"
        args.code_theme = "default"

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

    fnames = [str(Path(fn).resolve()) for fn in args.files]
    if len(args.files) > 1:
        good = True
        for fname in args.files:
            if Path(fname).is_dir():
                io.tool_error(f"{fname} is a directory, not provided alone.")
                good = False
        if not good:
            io.tool_error(
                "Provide either a single directory of a git repo, or a list of one or more files."
            )
            return 1

    git_dname = None
    if len(args.files) == 1:
        if Path(args.files[0]).is_dir():
            if args.git:
                git_dname = str(Path(args.files[0]).resolve())
                fnames = []
            else:
                io.tool_error(f"{args.files[0]} is a directory, but --no-git selected.")
                return 1

    # We can't know the git repo for sure until after parsing the args.
    # If we guessed wrong, reparse because that changes things like
    # the location of the config.yml and history files.
    if args.git and not force_git_root:
        right_repo_root = guessed_wrong_repo(io, git_root, fnames, git_dname)
        if right_repo_root:
            return main(argv, input, output, right_repo_root)

    io.tool_output(f"Aider v{__version__}")

    check_version(io.tool_error)

    if "VSCODE_GIT_IPC_HANDLE" in os.environ:
        args.pretty = False
        io.tool_output("VSCode terminal detected, pretty output has been disabled.")

    if args.git:
        git_root = setup_git(git_root, io)
        check_gitignore(git_root, io)

    def scrub_sensitive_info(text):
        # Replace sensitive information with placeholder
        return text.replace(args.openai_api_key, "***")

    if args.verbose:
        show = scrub_sensitive_info(parser.format_values())
        io.tool_output(show)
        io.tool_output("Option settings:")
        for arg, val in sorted(vars(args).items()):
            io.tool_output(f"  - {arg}: {scrub_sensitive_info(str(val))}")

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

    openai.api_key = args.openai_api_key
    for attr in ("base", "type", "version", "deployment_id", "engine"):
        arg_key = f"openai_api_{attr}"
        val = getattr(args, arg_key)
        if val is not None:
            mod_key = f"api_{attr}"
            setattr(openai, mod_key, val)
            io.tool_output(f"Setting openai.{mod_key}={val}")

    main_model = models.Model.create(args.model)

    try:
        coder = Coder.create(
            main_model,
            args.edit_format,
            io,
            args.skip_model_availability_check,
            ##
            fnames=fnames,
            git_dname=git_dname,
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
            voice_language=args.voice_language,
        )
    except ValueError as err:
        io.tool_error(str(err))
        return 1

    if args.show_repo_map:
        repo_map = coder.get_repo_map()
        if repo_map:
            io.tool_output(repo_map)
        return

    if args.apply:
        content = io.read_text(args.apply)
        if content is None:
            return
        coder.partial_response_content = content
        coder.apply_updates()
        return

    io.tool_output("Use /help to see in-chat commands, run with --help to see cmd line args")

    if args.message:
        io.tool_output()
        coder.run(with_message=args.message)
    else:
        coder.run()


if __name__ == "__main__":
    status = main()
    sys.exit(status)
