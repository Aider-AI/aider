import configparser
import json
import os
import re
import sys
import threading
import traceback
from pathlib import Path

import git
import importlib_resources
from dotenv import load_dotenv
from prompt_toolkit.enums import EditingMode

from aider import __version__, models, urls, utils
from aider.args import get_parser
from aider.coders import Coder
from aider.commands import Commands, SwitchCoder
from aider.format_settings import format_settings, scrub_sensitive_info
from aider.history import ChatSummary
from aider.io import InputOutput
from aider.llm import litellm  # noqa: F401; properly init litellm on launch
from aider.repo import ANY_GIT_ERROR, GitRepo
from aider.report import report_uncaught_exceptions
from aider.versioncheck import check_version, install_from_main_branch, install_upgrade

from .dump import dump  # noqa: F401


def check_config_files_for_yes(config_files):
    found = False
    for config_file in config_files:
        if Path(config_file).exists():
            try:
                with open(config_file, "r") as f:
                    for line in f:
                        if line.strip().startswith("yes:"):
                            print("Configuration error detected.")
                            print(f"The file {config_file} contains a line starting with 'yes:'")
                            print("Please replace 'yes:' with 'yes-always:' in this file.")
                            found = True
            except Exception:
                pass
    return found


def get_git_root():
    """Try and guess the git repo, since the conf.yml can be at the repo root"""
    try:
        repo = git.Repo(search_parent_directories=True)
        return repo.working_tree_dir
    except (git.InvalidGitRepositoryError, FileNotFoundError):
        return None


def guessed_wrong_repo(io, git_root, fnames, git_dname):
    """After we parse the args, we can determine the real repo. Did we guess wrong?"""

    try:
        check_repo = Path(GitRepo(io, fnames, git_dname).root).resolve()
    except (OSError,) + ANY_GIT_ERROR:
        return

    # we had no guess, rely on the "true" repo result
    if not git_root:
        return str(check_repo)

    git_root = Path(git_root).resolve()
    if check_repo == git_root:
        return

    return str(check_repo)


def make_new_repo(git_root, io):
    try:
        repo = git.Repo.init(git_root)
        check_gitignore(git_root, io, False)
    except ANY_GIT_ERROR as err:  # issue #1233
        io.tool_error(f"Unable to create git repo in {git_root}")
        io.tool_output(str(err))
        return

    io.tool_output(f"Git repository created in {git_root}")
    return repo


def setup_git(git_root, io):
    repo = None

    if git_root:
        repo = git.Repo(git_root)
    elif Path.cwd() == Path.home():
        io.tool_warning("You should probably run aider in a directory, not your home dir.")
        return
    elif io.confirm_ask("No git repo found, create one to track aider's changes (recommended)?"):
        git_root = str(Path.cwd().resolve())
        repo = make_new_repo(git_root, io)

    if not repo:
        return

    user_name = None
    user_email = None
    with repo.config_reader() as config:
        try:
            user_name = config.get_value("user", "name", None)
        except (configparser.NoSectionError, configparser.NoOptionError):
            pass
        try:
            user_email = config.get_value("user", "email", None)
        except (configparser.NoSectionError, configparser.NoOptionError):
            pass

    if user_name and user_email:
        return repo.working_tree_dir

    with repo.config_writer() as git_config:
        if not user_name:
            git_config.set_value("user", "name", "Your Name")
            io.tool_warning('Update git name with: git config user.name "Your Name"')
        if not user_email:
            git_config.set_value("user", "email", "you@example.com")
            io.tool_warning('Update git email with: git config user.email "you@example.com"')

    return repo.working_tree_dir


def check_gitignore(git_root, io, ask=True):
    if not git_root:
        return

    try:
        repo = git.Repo(git_root)
        if repo.ignored(".aider") and repo.ignored(".env"):
            return
    except ANY_GIT_ERROR:
        pass

    patterns = [".aider*", ".env"]
    patterns_to_add = []

    gitignore_file = Path(git_root) / ".gitignore"
    if gitignore_file.exists():
        content = io.read_text(gitignore_file)
        if content is None:
            return
        existing_lines = content.splitlines()
        for pat in patterns:
            if pat not in existing_lines:
                patterns_to_add.append(pat)
    else:
        content = ""
        patterns_to_add = patterns

    if not patterns_to_add:
        return

    if ask and not io.confirm_ask(f"Add {', '.join(patterns_to_add)} to .gitignore (recommended)?"):
        return

    if content and not content.endswith("\n"):
        content += "\n"
    content += "\n".join(patterns_to_add) + "\n"
    io.write_text(gitignore_file, content)

    io.tool_output(f"Added {', '.join(patterns_to_add)} to .gitignore")


def check_streamlit_install(io):
    return utils.check_pip_install_extra(
        io,
        "streamlit",
        "You need to install the aider browser feature",
        ["aider-chat[browser]"],
    )


def launch_gui(args):
    from streamlit.web import cli

    from aider import gui

    print()
    print("CONTROL-C to exit...")

    target = gui.__file__

    st_args = ["run", target]

    st_args += [
        "--browser.gatherUsageStats=false",
        "--runner.magicEnabled=false",
        "--server.runOnSave=false",
    ]

    if "-dev" in __version__:
        print("Watching for file changes.")
    else:
        st_args += [
            "--global.developmentMode=false",
            "--server.fileWatcherType=none",
            "--client.toolbarMode=viewer",  # minimal?
        ]

    st_args += ["--"] + args

    cli.main(st_args)

    # from click.testing import CliRunner
    # runner = CliRunner()
    # from streamlit.web import bootstrap
    # bootstrap.load_config_options(flag_options={})
    # cli.main_run(target, args)
    # sys.argv = ['streamlit', 'run', '--'] + args


def parse_lint_cmds(lint_cmds, io):
    err = False
    res = dict()
    for lint_cmd in lint_cmds:
        if re.match(r"^[a-z]+:.*", lint_cmd):
            pieces = lint_cmd.split(":")
            lang = pieces[0]
            cmd = lint_cmd[len(lang) + 1 :]
            lang = lang.strip()
        else:
            lang = None
            cmd = lint_cmd

        cmd = cmd.strip()

        if cmd:
            res[lang] = cmd
        else:
            io.tool_error(f'Unable to parse --lint-cmd "{lint_cmd}"')
            io.tool_output('The arg should be "language: cmd --args ..."')
            io.tool_output('For example: --lint-cmd "python: flake8 --select=E9"')
            err = True
    if err:
        return
    return res


def generate_search_path_list(default_file, git_root, command_line_file):
    files = []
    files.append(Path.home() / default_file)  # homedir
    if git_root:
        files.append(Path(git_root) / default_file)  # git root
    files.append(default_file)
    if command_line_file:
        files.append(command_line_file)

    resolved_files = []
    for fn in files:
        try:
            resolved_files.append(Path(fn).resolve())
        except OSError:
            pass

    files = resolved_files
    files.reverse()
    uniq = []
    for fn in files:
        if fn not in uniq:
            uniq.append(fn)
    uniq.reverse()
    files = uniq
    files = list(map(str, files))
    files = list(dict.fromkeys(files))

    return files


def register_models(git_root, model_settings_fname, io, verbose=False):
    model_settings_files = generate_search_path_list(
        ".aider.model.settings.yml", git_root, model_settings_fname
    )

    try:
        files_loaded = models.register_models(model_settings_files)
        if len(files_loaded) > 0:
            if verbose:
                io.tool_output("Loaded model settings from:")
                for file_loaded in files_loaded:
                    io.tool_output(f"  - {file_loaded}")  # noqa: E221
        elif verbose:
            io.tool_output("No model settings files loaded")
    except Exception as e:
        io.tool_error(f"Error loading aider model settings: {e}")
        return 1

    if verbose:
        io.tool_output("Searched for model settings files:")
        for file in model_settings_files:
            io.tool_output(f"  - {file}")

    return None


def load_dotenv_files(git_root, dotenv_fname, encoding="utf-8"):
    dotenv_files = generate_search_path_list(
        ".env",
        git_root,
        dotenv_fname,
    )
    loaded = []
    for fname in dotenv_files:
        try:
            if Path(fname).exists():
                load_dotenv(fname, override=True, encoding=encoding)
                loaded.append(fname)
        except OSError as e:
            print(f"OSError loading {fname}: {e}")
        except Exception as e:
            print(f"Error loading {fname}: {e}")
    return loaded


def register_litellm_models(git_root, model_metadata_fname, io, verbose=False):
    model_metatdata_files = generate_search_path_list(
        ".aider.model.metadata.json", git_root, model_metadata_fname
    )

    # Add the resource file path
    resource_metadata = importlib_resources.files("aider.resources").joinpath("model-metadata.json")
    model_metatdata_files.append(str(resource_metadata))

    try:
        model_metadata_files_loaded = models.register_litellm_models(model_metatdata_files)
        if len(model_metadata_files_loaded) > 0 and verbose:
            io.tool_output("Loaded model metadata from:")
            for model_metadata_file in model_metadata_files_loaded:
                io.tool_output(f"  - {model_metadata_file}")  # noqa: E221
    except Exception as e:
        io.tool_error(f"Error loading model metadata models: {e}")
        return 1


def sanity_check_repo(repo, io):
    if not repo:
        return True

    if not repo.repo.working_tree_dir:
        io.tool_error("The git repo does not seem to have a working tree?")
        return False

    bad_ver = False
    try:
        repo.get_tracked_files()
        if not repo.git_repo_error:
            return True
        error_msg = str(repo.git_repo_error)
    except ANY_GIT_ERROR as exc:
        error_msg = str(exc)
        bad_ver = "version in (1, 2)" in error_msg
    except AssertionError as exc:
        error_msg = str(exc)
        bad_ver = True

    if bad_ver:
        io.tool_error("Aider only works with git repos with version number 1 or 2.")
        io.tool_output("You may be able to convert your repo: git update-index --index-version=2")
        io.tool_output("Or run aider --no-git to proceed without using git.")
        io.tool_output(urls.git_index_version)
        return False

    io.tool_error("Unable to read git repository, it may be corrupt?")
    io.tool_output(error_msg)
    return False


def main(argv=None, input=None, output=None, force_git_root=None, return_coder=False):
    report_uncaught_exceptions()

    if argv is None:
        argv = sys.argv[1:]

    if force_git_root:
        git_root = force_git_root
    else:
        git_root = get_git_root()

    conf_fname = Path(".aider.conf.yml")

    default_config_files = []
    try:
        default_config_files += [conf_fname.resolve()]  # CWD
    except OSError:
        pass

    if git_root:
        git_conf = Path(git_root) / conf_fname  # git root
        if git_conf not in default_config_files:
            default_config_files.append(git_conf)
    default_config_files.append(Path.home() / conf_fname)  # homedir
    default_config_files = list(map(str, default_config_files))

    parser = get_parser(default_config_files, git_root)
    try:
        args, unknown = parser.parse_known_args(argv)
    except AttributeError as e:
        if all(word in str(e) for word in ["bool", "object", "has", "no", "attribute", "strip"]):
            if check_config_files_for_yes(default_config_files):
                return 1
        raise e

    if args.verbose:
        print("Config files search order, if no --config:")
        for file in default_config_files:
            exists = "(exists)" if Path(file).exists() else ""
            print(f"  - {file} {exists}")

    default_config_files.reverse()

    parser = get_parser(default_config_files, git_root)

    args, unknown = parser.parse_known_args(argv)

    # Load the .env file specified in the arguments
    loaded_dotenvs = load_dotenv_files(git_root, args.env_file, args.encoding)

    # Parse again to include any arguments that might have been defined in .env
    args = parser.parse_args(argv)

    if not args.verify_ssl:
        import httpx

        os.environ["SSL_VERIFY"] = ""
        litellm._load_litellm()
        litellm._lazy_module.client_session = httpx.Client(verify=False)
        litellm._lazy_module.aclient_session = httpx.AsyncClient(verify=False)

    if args.dark_mode:
        args.user_input_color = "#32FF32"
        args.tool_error_color = "#FF3333"
        args.tool_warning_color = "#FFFF00"
        args.assistant_output_color = "#00FFFF"
        args.code_theme = "monokai"

    if args.light_mode:
        args.user_input_color = "green"
        args.tool_error_color = "red"
        args.tool_warning_color = "#FFA500"
        args.assistant_output_color = "blue"
        args.code_theme = "default"

    if return_coder and args.yes_always is None:
        args.yes_always = True

    editing_mode = EditingMode.VI if args.vim else EditingMode.EMACS

    def get_io(pretty):
        return InputOutput(
            pretty,
            args.yes_always,
            args.input_history_file,
            args.chat_history_file,
            input=input,
            output=output,
            user_input_color=args.user_input_color,
            tool_output_color=args.tool_output_color,
            tool_warning_color=args.tool_warning_color,
            tool_error_color=args.tool_error_color,
            completion_menu_color=args.completion_menu_color,
            completion_menu_bg_color=args.completion_menu_bg_color,
            completion_menu_current_color=args.completion_menu_current_color,
            completion_menu_current_bg_color=args.completion_menu_current_bg_color,
            assistant_output_color=args.assistant_output_color,
            code_theme=args.code_theme,
            dry_run=args.dry_run,
            encoding=args.encoding,
            llm_history_file=args.llm_history_file,
            editingmode=editing_mode,
            fancy_input=args.fancy_input,
        )

    io = get_io(args.pretty)
    try:
        io.rule()
    except UnicodeEncodeError as err:
        if not io.pretty:
            raise err
        io = get_io(False)
        io.tool_warning("Terminal does not support pretty output (UnicodeDecodeError)")

    if args.gui and not return_coder:
        if not check_streamlit_install(io):
            return
        launch_gui(argv)
        return

    if args.verbose:
        for fname in loaded_dotenvs:
            io.tool_output(f"Loaded {fname}")

    all_files = args.files + (args.file or [])
    fnames = [str(Path(fn).resolve()) for fn in all_files]
    read_only_fnames = [str(Path(fn).resolve()) for fn in (args.read or [])]
    if len(all_files) > 1:
        good = True
        for fname in all_files:
            if Path(fname).is_dir():
                io.tool_error(f"{fname} is a directory, not provided alone.")
                good = False
        if not good:
            io.tool_output(
                "Provide either a single directory of a git repo, or a list of one or more files."
            )
            return 1

    git_dname = None
    if len(all_files) == 1:
        if Path(all_files[0]).is_dir():
            if args.git:
                git_dname = str(Path(all_files[0]).resolve())
                fnames = []
            else:
                io.tool_error(f"{all_files[0]} is a directory, but --no-git selected.")
                return 1

    # We can't know the git repo for sure until after parsing the args.
    # If we guessed wrong, reparse because that changes things like
    # the location of the config.yml and history files.
    if args.git and not force_git_root:
        right_repo_root = guessed_wrong_repo(io, git_root, fnames, git_dname)
        if right_repo_root:
            return main(argv, input, output, right_repo_root, return_coder=return_coder)

    if args.just_check_update:
        update_available = check_version(io, just_check=True, verbose=args.verbose)
        return 0 if not update_available else 1

    if args.install_main_branch:
        success = install_from_main_branch(io)
        return 0 if success else 1

    if args.upgrade:
        success = install_upgrade(io)
        return 0 if success else 1

    if args.check_update:
        check_version(io, verbose=args.verbose)

    if args.list_models:
        models.print_matching_models(io, args.list_models)
        return 0

    if args.git:
        git_root = setup_git(git_root, io)
        if args.gitignore:
            check_gitignore(git_root, io)

    if args.verbose:
        show = format_settings(parser, args)
        io.tool_output(show)

    cmd_line = " ".join(sys.argv)
    cmd_line = scrub_sensitive_info(args, cmd_line)
    io.tool_output(cmd_line, log_only=True)

    check_and_load_imports(io, verbose=args.verbose)

    if args.anthropic_api_key:
        os.environ["ANTHROPIC_API_KEY"] = args.anthropic_api_key

    if args.openai_api_key:
        os.environ["OPENAI_API_KEY"] = args.openai_api_key
    if args.openai_api_base:
        os.environ["OPENAI_API_BASE"] = args.openai_api_base
    if args.openai_api_version:
        os.environ["OPENAI_API_VERSION"] = args.openai_api_version
    if args.openai_api_type:
        os.environ["OPENAI_API_TYPE"] = args.openai_api_type
    if args.openai_organization_id:
        os.environ["OPENAI_ORGANIZATION"] = args.openai_organization_id

    register_models(git_root, args.model_settings_file, io, verbose=args.verbose)
    register_litellm_models(git_root, args.model_metadata_file, io, verbose=args.verbose)

    if not args.model:
        args.model = "gpt-4o-2024-08-06"
        if os.environ.get("ANTHROPIC_API_KEY"):
            args.model = "claude-3-5-sonnet-20241022"

    main_model = models.Model(
        args.model,
        weak_model=args.weak_model,
        editor_model=args.editor_model,
        editor_edit_format=args.editor_edit_format,
    )

    if args.verbose:
        io.tool_output("Model info:")
        io.tool_output(json.dumps(main_model.info, indent=4))

    lint_cmds = parse_lint_cmds(args.lint_cmd, io)
    if lint_cmds is None:
        return 1

    if args.show_model_warnings:
        problem = models.sanity_check_models(io, main_model)
        if problem:
            io.tool_output("You can skip this check with --no-show-model-warnings")
            io.tool_output()
            try:
                if not io.confirm_ask("Proceed anyway?"):
                    return 1
            except KeyboardInterrupt:
                return 1

    repo = None
    if args.git:
        try:
            repo = GitRepo(
                io,
                fnames,
                git_dname,
                args.aiderignore,
                models=main_model.commit_message_models(),
                attribute_author=args.attribute_author,
                attribute_committer=args.attribute_committer,
                attribute_commit_message_author=args.attribute_commit_message_author,
                attribute_commit_message_committer=args.attribute_commit_message_committer,
                commit_prompt=args.commit_prompt,
                subtree_only=args.subtree_only,
            )
        except FileNotFoundError:
            pass

    if not args.skip_sanity_check_repo:
        if not sanity_check_repo(repo, io):
            return 1

    commands = Commands(
        io, None, verify_ssl=args.verify_ssl, args=args, parser=parser, verbose=args.verbose
    )

    summarizer = ChatSummary(
        [main_model.weak_model, main_model],
        args.max_chat_history_tokens or main_model.max_chat_history_tokens,
    )

    if args.cache_prompts and args.map_refresh == "auto":
        args.map_refresh = "files"

    if not main_model.streaming:
        if args.stream:
            io.tool_warning(
                f"Warning: Streaming is not supported by {main_model.name}. Disabling streaming."
            )
        args.stream = False

    try:
        coder = Coder.create(
            main_model=main_model,
            edit_format=args.edit_format,
            io=io,
            repo=repo,
            fnames=fnames,
            read_only_fnames=read_only_fnames,
            show_diffs=args.show_diffs,
            auto_commits=args.auto_commits,
            dirty_commits=args.dirty_commits,
            dry_run=args.dry_run,
            map_tokens=args.map_tokens,
            verbose=args.verbose,
            stream=args.stream,
            use_git=args.git,
            restore_chat_history=args.restore_chat_history,
            auto_lint=args.auto_lint,
            auto_test=args.auto_test,
            lint_cmds=lint_cmds,
            test_cmd=args.test_cmd,
            commands=commands,
            summarizer=summarizer,
            map_refresh=args.map_refresh,
            cache_prompts=args.cache_prompts,
            map_mul_no_files=args.map_multiplier_no_files,
            num_cache_warming_pings=args.cache_keepalive_pings,
            suggest_shell_commands=args.suggest_shell_commands,
            chat_language=args.chat_language,
        )
    except ValueError as err:
        io.tool_error(str(err))
        return 1

    if return_coder:
        return coder

    coder.show_announcements()

    if args.show_prompts:
        coder.cur_messages += [
            dict(role="user", content="Hello!"),
        ]
        messages = coder.format_messages().all_messages()
        utils.show_messages(messages)
        return

    if args.lint:
        coder.commands.cmd_lint(fnames=fnames)

    if args.test:
        if not args.test_cmd:
            io.tool_error("No --test-cmd provided.")
            return 1
        test_errors = coder.commands.cmd_test(args.test_cmd)
        if test_errors:
            coder.run(test_errors)

    if args.commit:
        if args.dry_run:
            io.tool_output("Dry run enabled, skipping commit.")
        else:
            coder.commands.cmd_commit()

    if args.lint or args.test or args.commit:
        return

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

    if "VSCODE_GIT_IPC_HANDLE" in os.environ:
        args.pretty = False
        io.tool_output("VSCode terminal detected, pretty output has been disabled.")

    io.tool_output('Use /help <question> for help, run "aider --help" to see cmd line args')

    if git_root and Path.cwd().resolve() != Path(git_root).resolve():
        io.tool_warning(
            "Note: in-chat filenames are always relative to the git working dir, not the current"
            " working dir."
        )

        io.tool_output(f"Cur working dir: {Path.cwd()}")
        io.tool_output(f"Git working dir: {git_root}")

    if args.message:
        io.add_to_input_history(args.message)
        io.tool_output()
        try:
            coder.run(with_message=args.message)
        except SwitchCoder:
            pass
        return

    if args.message_file:
        try:
            message_from_file = io.read_text(args.message_file)
            io.tool_output()
            coder.run(with_message=message_from_file)
        except FileNotFoundError:
            io.tool_error(f"Message file not found: {args.message_file}")
            return 1
        except IOError as e:
            io.tool_error(f"Error reading message file: {e}")
            return 1
        return

    if args.exit:
        return

    while True:
        try:
            coder.run()
            return
        except SwitchCoder as switch:
            kwargs = dict(io=io, from_coder=coder)
            kwargs.update(switch.kwargs)
            if "show_announcements" in kwargs:
                del kwargs["show_announcements"]

            coder = Coder.create(**kwargs)

            if switch.kwargs.get("show_announcements") is not False:
                coder.show_announcements()


def check_and_load_imports(io, verbose=False):
    installs_file = Path.home() / ".aider" / "installs.json"
    key = (__version__, sys.executable)

    if verbose:
        io.tool_output(
            f"Checking imports for version {__version__} and executable {sys.executable}"
        )
        io.tool_output(f"Installs file: {installs_file}")

    try:
        if installs_file.exists():
            with open(installs_file, "r") as f:
                installs = json.load(f)
            if verbose:
                io.tool_output("Installs file exists and loaded")
        else:
            installs = {}
            if verbose:
                io.tool_output("Installs file does not exist, creating new dictionary")

        if str(key) not in installs:
            if verbose:
                io.tool_output(
                    "First run for this version and executable, loading imports synchronously"
                )
            try:
                load_slow_imports(swallow=False)
            except Exception as err:
                io.tool_error(str(err))
                io.tool_output("Error loading required imports. Did you install aider properly?")
                io.tool_output("https://aider.chat/docs/install/install.html")
                sys.exit(1)

            installs[str(key)] = True
            installs_file.parent.mkdir(parents=True, exist_ok=True)
            with open(installs_file, "w") as f:
                json.dump(installs, f, indent=4)
            if verbose:
                io.tool_output("Imports loaded and installs file updated")
        else:
            if verbose:
                io.tool_output("Not first run, loading imports in background thread")
            thread = threading.Thread(target=load_slow_imports)
            thread.daemon = True
            thread.start()
    except Exception as e:
        io.tool_warning(f"Error in checking imports: {e}")
        if verbose:
            io.tool_output(f"Full exception details: {traceback.format_exc()}")


def load_slow_imports(swallow=True):
    # These imports are deferred in various ways to
    # improve startup time.
    # This func is called either synchronously or in a thread
    # depending on whether it's been run before for this version and executable.

    try:
        import httpx  # noqa: F401
        import litellm  # noqa: F401
        import networkx  # noqa: F401
        import numpy  # noqa: F401
    except Exception as e:
        if not swallow:
            raise e


if __name__ == "__main__":
    status = main()
    sys.exit(status)
