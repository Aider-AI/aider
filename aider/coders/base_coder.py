#!/usr/bin/env python

import hashlib
import json
import os
import sys
import time
import traceback
from json.decoder import JSONDecodeError
from pathlib import Path, PurePosixPath

import backoff
import git
import openai
import requests
from jsonschema import Draft7Validator
from openai.error import APIError, RateLimitError, ServiceUnavailableError, Timeout
from rich.console import Console, Text
from rich.live import Live
from rich.markdown import Markdown

from aider import models, prompts, utils
from aider.commands import Commands
from aider.repomap import RepoMap

from ..dump import dump  # noqa: F401


class MissingAPIKeyError(ValueError):
    pass


class ExhaustedContextWindow(Exception):
    pass


def wrap_fence(name):
    return f"<{name}>", f"</{name}>"


class Coder:
    abs_fnames = None
    repo = None
    last_aider_commit_hash = None
    last_asked_for_commit_time = 0
    repo_map = None
    functions = None
    total_cost = 0.0
    num_exhausted_context_windows = 0
    last_keyboard_interrupt = None

    @classmethod
    def create(
        self,
        main_model,
        edit_format,
        io,
        **kwargs,
    ):
        from . import (
            EditBlockCoder,
            EditBlockFunctionCoder,
            SingleWholeFileFunctionCoder,
            WholeFileCoder,
            WholeFileFunctionCoder,
        )

        if not main_model:
            main_model = models.GPT35_16k

        if not main_model.always_available:
            if not check_model_availability(main_model):
                if main_model != models.GPT4:
                    io.tool_error(
                        f"API key does not support {main_model.name}, falling back to"
                        f" {models.GPT35_16k.name}"
                    )
                main_model = models.GPT35_16k

        if edit_format is None:
            edit_format = main_model.edit_format

        if edit_format == "diff":
            return EditBlockCoder(main_model, io, **kwargs)
        elif edit_format == "whole":
            return WholeFileCoder(main_model, io, **kwargs)
        elif edit_format == "whole-func":
            return WholeFileFunctionCoder(main_model, io, **kwargs)
        elif edit_format == "single-whole-func":
            return SingleWholeFileFunctionCoder(main_model, io, **kwargs)
        elif edit_format == "diff-func-list":
            return EditBlockFunctionCoder("list", main_model, io, **kwargs)
        elif edit_format in ("diff-func", "diff-func-string"):
            return EditBlockFunctionCoder("string", main_model, io, **kwargs)
        else:
            raise ValueError(f"Unknown edit format {edit_format}")

    def __init__(
        self,
        main_model,
        io,
        fnames=None,
        pretty=True,
        show_diffs=False,
        auto_commits=True,
        dirty_commits=True,
        dry_run=False,
        map_tokens=1024,
        verbose=False,
        assistant_output_color="blue",
        code_theme="default",
        stream=True,
        use_git=True,
    ):
        if not fnames:
            fnames = []

        self.chat_completion_call_hashes = []
        self.chat_completion_response_hashes = []

        self.verbose = verbose
        self.abs_fnames = set()
        self.cur_messages = []
        self.done_messages = []

        self.io = io
        self.stream = stream

        if not auto_commits:
            dirty_commits = False

        self.auto_commits = auto_commits
        self.dirty_commits = dirty_commits
        self.assistant_output_color = assistant_output_color
        self.code_theme = code_theme

        self.dry_run = dry_run
        self.pretty = pretty

        if pretty:
            self.console = Console()
        else:
            self.console = Console(force_terminal=False, no_color=True)

        self.main_model = main_model

        self.io.tool_output(f"Model: {main_model.name}")

        self.show_diffs = show_diffs

        self.commands = Commands(self.io, self)

        if use_git:
            self.set_repo(fnames)
        else:
            self.abs_fnames = set([str(Path(fname).resolve()) for fname in fnames])

        if self.repo:
            rel_repo_dir = self.get_rel_repo_dir()
            self.io.tool_output(f"Git repo: {rel_repo_dir}")
        else:
            self.io.tool_output("Git repo: none")
            self.find_common_root()

        if main_model.use_repo_map and self.repo and self.gpt_prompts.repo_content_prefix:
            self.repo_map = RepoMap(
                map_tokens,
                self.root,
                self.main_model,
                io,
                self.gpt_prompts.repo_content_prefix,
                self.verbose,
            )

            if self.repo_map.use_ctags:
                self.io.tool_output(f"Repo-map: universal-ctags using {map_tokens} tokens")
            elif not self.repo_map.has_ctags and map_tokens > 0:
                self.io.tool_output(
                    f"Repo-map: basic using {map_tokens} tokens"
                    f" ({self.repo_map.ctags_disabled_reason})"
                )
            else:
                self.io.tool_output("Repo-map: disabled because map_tokens == 0")
        else:
            self.io.tool_output("Repo-map: disabled")

        for fname in self.get_inchat_relative_files():
            self.io.tool_output(f"Added {fname} to the chat.")

        # validate the functions jsonschema
        if self.functions:
            for function in self.functions:
                Draft7Validator.check_schema(function)

            if self.verbose:
                self.io.tool_output("JSON Schema:")
                self.io.tool_output(json.dumps(self.functions, indent=4))

    def find_common_root(self):
        if len(self.abs_fnames) == 1:
            self.root = os.path.dirname(list(self.abs_fnames)[0])
        elif self.abs_fnames:
            self.root = os.path.commonpath(list(self.abs_fnames))
        else:
            self.root = os.getcwd()

        self.root = utils.safe_abs_path(self.root)

    def get_rel_repo_dir(self):
        try:
            return os.path.relpath(self.repo.git_dir, os.getcwd())
        except ValueError:
            return self.repo.git_dir

    def add_rel_fname(self, rel_fname):
        self.abs_fnames.add(self.abs_root_path(rel_fname))

    def abs_root_path(self, path):
        res = Path(self.root) / path
        return utils.safe_abs_path(res)

    def set_repo(self, cmd_line_fnames):
        if not cmd_line_fnames:
            cmd_line_fnames = ["."]

        repo_paths = []
        for fname in cmd_line_fnames:
            fname = Path(fname)
            if not fname.exists():
                self.io.tool_output(f"Creating empty file {fname}")
                fname.parent.mkdir(parents=True, exist_ok=True)
                fname.touch()

            fname = fname.resolve()

            try:
                repo_path = git.Repo(fname, search_parent_directories=True).working_dir
                repo_path = utils.safe_abs_path(repo_path)
                repo_paths.append(repo_path)
            except git.exc.InvalidGitRepositoryError:
                pass

            if fname.is_dir():
                continue

            self.abs_fnames.add(str(fname))

        num_repos = len(set(repo_paths))

        if num_repos == 0:
            return
        if num_repos > 1:
            self.io.tool_error("Files are in different git repos.")
            return

        # https://github.com/gitpython-developers/GitPython/issues/427
        self.repo = git.Repo(repo_paths.pop(), odbt=git.GitDB)

        self.root = utils.safe_abs_path(self.repo.working_tree_dir)

        new_files = []
        for fname in self.abs_fnames:
            relative_fname = self.get_rel_fname(fname)

            tracked_files = set(self.get_tracked_files())
            if relative_fname not in tracked_files:
                new_files.append(relative_fname)

        if new_files:
            rel_repo_dir = self.get_rel_repo_dir()

            self.io.tool_output(f"Files not tracked in {rel_repo_dir}:")
            for fn in new_files:
                self.io.tool_output(f" - {fn}")
            if self.io.confirm_ask("Add them?"):
                for relative_fname in new_files:
                    self.repo.git.add(relative_fname)
                    self.io.tool_output(f"Added {relative_fname} to the git repo")
                show_files = ", ".join(new_files)
                commit_message = f"Added new files to the git repo: {show_files}"
                self.repo.git.commit("-m", commit_message, "--no-verify")
                commit_hash = self.repo.head.commit.hexsha[:7]
                self.io.tool_output(f"Commit {commit_hash} {commit_message}")
            else:
                self.io.tool_error("Skipped adding new files to the git repo.")
                return

    # fences are obfuscated so aider can modify this file!
    fences = [
        ("``" + "`", "``" + "`"),
        wrap_fence("source"),
        wrap_fence("code"),
        wrap_fence("pre"),
        wrap_fence("codeblock"),
        wrap_fence("sourcecode"),
    ]
    fence = fences[0]

    def get_abs_fnames_content(self):
        for fname in list(self.abs_fnames):
            content = self.io.read_text(fname)

            if content is None:
                relative_fname = self.get_rel_fname(fname)
                self.io.tool_error(f"Dropping {relative_fname} from the chat.")
                self.abs_fnames.remove(fname)
            else:
                yield fname, content

    def choose_fence(self):
        all_content = ""
        for _fname, content in self.get_abs_fnames_content():
            all_content += content + "\n"

        good = False
        for fence_open, fence_close in self.fences:
            if fence_open in all_content or fence_close in all_content:
                continue
            good = True
            break

        if good:
            self.fence = (fence_open, fence_close)
        else:
            self.fence = self.fences[0]
            self.io.tool_error(
                "Unable to find a fencing strategy! Falling back to:"
                " {self.fence[0]}...{self.fence[1]}"
            )

        return

    def get_files_content(self, fnames=None):
        if not fnames:
            fnames = self.abs_fnames

        prompt = ""
        for fname, content in self.get_abs_fnames_content():
            relative_fname = self.get_rel_fname(fname)
            prompt += "\n"
            prompt += relative_fname
            prompt += f"\n{self.fence[0]}\n"
            prompt += content
            prompt += f"{self.fence[1]}\n"

        return prompt

    def get_repo_map(self):
        if not self.repo_map:
            return

        other_files = set(self.get_all_abs_files()) - set(self.abs_fnames)
        repo_content = self.repo_map.get_repo_map(self.abs_fnames, other_files)
        return repo_content

    def get_files_messages(self):
        all_content = ""
        if self.abs_fnames:
            files_content = self.gpt_prompts.files_content_prefix
            files_content += self.get_files_content()
        else:
            files_content = self.gpt_prompts.files_no_full_files

        all_content += files_content

        repo_content = self.get_repo_map()
        if repo_content:
            if all_content:
                all_content += "\n"
            all_content += repo_content

        files_messages = [
            dict(role="user", content=all_content),
            dict(role="assistant", content="Ok."),
        ]
        if self.abs_fnames:
            files_messages += [
                dict(role="system", content=self.fmt_system_reminder()),
            ]

        return files_messages

    def run(self, with_message=None):
        while True:
            try:
                if with_message:
                    new_user_message = with_message
                    self.io.user_input(with_message)
                else:
                    new_user_message = self.run_loop()

                while new_user_message:
                    new_user_message = self.send_new_user_message(new_user_message)

                if with_message:
                    return

            except KeyboardInterrupt:
                self.keyboard_interrupt()
            except EOFError:
                return

    def keyboard_interrupt(self):
        now = time.time()

        thresh = 2  # seconds
        if self.last_keyboard_interrupt and now - self.last_keyboard_interrupt < thresh:
            self.io.tool_error("\n\n^C KeyboardInterrupt")
            sys.exit()

        self.io.tool_error("\n\n^C again to exit")

        self.last_keyboard_interrupt = now

    def should_dirty_commit(self, inp):
        cmds = self.commands.matching_commands(inp)
        if cmds:
            matching_commands, _, _ = cmds
            if len(matching_commands) == 1:
                cmd = matching_commands[0][1:]
                if cmd in "add clear commit diff drop exit help ls tokens".split():
                    return

        if not self.dirty_commits:
            return
        if not self.repo:
            return
        if not self.repo.is_dirty():
            return
        if self.last_asked_for_commit_time >= self.get_last_modified():
            return
        return True

    def move_back_cur_messages(self, message):
        self.done_messages += self.cur_messages
        if message:
            self.done_messages += [
                dict(role="user", content=message),
                dict(role="assistant", content="Ok."),
            ]
        self.cur_messages = []

    def run_loop(self):
        inp = self.io.get_input(
            self.root,
            self.get_inchat_relative_files(),
            self.get_addable_relative_files(),
            self.commands,
        )

        if self.should_dirty_commit(inp):
            self.io.tool_output("Git repo has uncommitted changes, preparing commit...")
            self.commit(ask=True, which="repo_files")

            # files changed, move cur messages back behind the files messages
            self.move_back_cur_messages(self.gpt_prompts.files_content_local_edits)

            if inp.strip():
                self.io.tool_output("Use up-arrow to retry previous command:", inp)
            return

        if not inp:
            return

        if self.commands.is_command(inp):
            return self.commands.run(inp)

        self.check_for_file_mentions(inp)

        return self.send_new_user_message(inp)

    def fmt_system_reminder(self):
        prompt = self.gpt_prompts.system_reminder
        prompt = prompt.format(fence=self.fence)
        return prompt

    def send_new_user_message(self, inp):
        self.choose_fence()

        self.cur_messages += [
            dict(role="user", content=inp),
        ]

        main_sys = self.gpt_prompts.main_system
        # if self.main_model.max_context_tokens > 4 * 1024:
        main_sys += "\n" + self.fmt_system_reminder()

        messages = [
            dict(role="system", content=main_sys),
        ]

        messages += self.done_messages
        messages += self.get_files_messages()
        messages += self.cur_messages

        if self.verbose:
            utils.show_messages(messages, functions=self.functions)

        exhausted = False
        interrupted = False
        try:
            interrupted = self.send(messages, functions=self.functions)
        except ExhaustedContextWindow:
            exhausted = True
        except openai.error.InvalidRequestError as err:
            if "maximum context length" in str(err):
                exhausted = True
            else:
                raise err

        if exhausted:
            self.num_exhausted_context_windows += 1
            self.io.tool_error("The chat session is larger than the context window!\n")
            self.commands.cmd_tokens("")
            self.io.tool_error("\nTo reduce token usage:")
            self.io.tool_error(" - Use /drop to remove unneeded files from the chat session.")
            self.io.tool_error(" - Use /clear to clear chat history.")
            return

        if self.partial_response_function_call:
            args = self.parse_partial_args()
            if args:
                content = args["explanation"]
            else:
                content = ""
        elif self.partial_response_content:
            content = self.partial_response_content
        else:
            content = ""

        if interrupted:
            content += "\n^C KeyboardInterrupt"

        self.io.tool_output()
        if interrupted:
            self.cur_messages += [dict(role="assistant", content=content)]
            return

        edited, edit_error = self.apply_updates()
        if edit_error:
            self.update_cur_messages(set())
            return edit_error

        self.update_cur_messages(edited)

        if edited:
            if self.repo and self.auto_commits and not self.dry_run:
                saved_message = self.auto_commit()
            elif hasattr(self.gpt_prompts, "files_content_gpt_edits_no_repo"):
                saved_message = self.gpt_prompts.files_content_gpt_edits_no_repo
            else:
                saved_message = None

            self.move_back_cur_messages(saved_message)

        add_rel_files_message = self.check_for_file_mentions(content)
        if add_rel_files_message:
            return add_rel_files_message

    def update_cur_messages(self, edited):
        if self.partial_response_content:
            self.cur_messages += [dict(role="assistant", content=self.partial_response_content)]
        if self.partial_response_function_call:
            self.cur_messages += [
                dict(
                    role="assistant",
                    content=None,
                    function_call=self.partial_response_function_call,
                )
            ]

    def auto_commit(self):
        res = self.commit(history=self.cur_messages, prefix="aider: ")
        if res:
            commit_hash, commit_message = res
            self.last_aider_commit_hash = commit_hash

            saved_message = self.gpt_prompts.files_content_gpt_edits.format(
                hash=commit_hash,
                message=commit_message,
            )
        else:
            if self.repo:
                self.io.tool_output("No changes made to git tracked files.")
            saved_message = self.gpt_prompts.files_content_gpt_no_edits

        return saved_message

    def check_for_file_mentions(self, content):
        words = set(word for word in content.split())

        # drop sentence punctuation from the end
        words = set(word.rstrip(",.!;") for word in words)

        # strip away all kinds of quotes
        quotes = "".join(['"', "'", "`"])
        words = set(word.strip(quotes) for word in words)

        addable_rel_fnames = self.get_addable_relative_files()

        mentioned_rel_fnames = set()
        fname_to_rel_fnames = {}
        for rel_fname in addable_rel_fnames:
            if rel_fname in words:
                mentioned_rel_fnames.add(str(rel_fname))

            fname = os.path.basename(rel_fname)
            if fname not in fname_to_rel_fnames:
                fname_to_rel_fnames[fname] = []
            fname_to_rel_fnames[fname].append(rel_fname)

        for fname, rel_fnames in fname_to_rel_fnames.items():
            if len(rel_fnames) == 1 and fname in words:
                mentioned_rel_fnames.add(rel_fnames[0])

        if not mentioned_rel_fnames:
            return

        for rel_fname in mentioned_rel_fnames:
            self.io.tool_output(rel_fname)

        if not self.io.confirm_ask("Add these files to the chat?"):
            return

        for rel_fname in mentioned_rel_fnames:
            self.add_rel_fname(rel_fname)

        return prompts.added_files.format(fnames=", ".join(mentioned_rel_fnames))

    @backoff.on_exception(
        backoff.expo,
        (
            Timeout,
            APIError,
            ServiceUnavailableError,
            RateLimitError,
            requests.exceptions.ConnectionError,
        ),
        max_tries=10,
        on_backoff=lambda details: print(
            f"{details.get('exception','Exception')}\nRetry in {details['wait']:.1f} seconds."
        ),
    )
    def send_with_retries(self, model, messages, functions):
        kwargs = dict(
            model=model,
            messages=messages,
            temperature=0,
            stream=self.stream,
        )
        if functions is not None:
            kwargs["functions"] = self.functions

        # we are abusing the openai object to stash these values
        if hasattr(openai, "api_deployment_id"):
            kwargs["deployment_id"] = openai.api_deployment_id
        if hasattr(openai, "api_engine"):
            kwargs["engine"] = openai.api_engine

        # Generate SHA1 hash of kwargs and append it to chat_completion_call_hashes
        hash_object = hashlib.sha1(json.dumps(kwargs, sort_keys=True).encode())
        self.chat_completion_call_hashes.append(hash_object.hexdigest())

        res = openai.ChatCompletion.create(**kwargs)
        return res

    def send(self, messages, model=None, silent=False, functions=None):
        if not model:
            model = self.main_model.name

        self.partial_response_content = ""
        self.partial_response_function_call = dict()

        interrupted = False
        try:
            completion = self.send_with_retries(model, messages, functions)
            if self.stream:
                self.show_send_output_stream(completion, silent)
            else:
                self.show_send_output(completion, silent)
        except KeyboardInterrupt:
            self.keyboard_interrupt()
            interrupted = True

        if not silent:
            if self.partial_response_content:
                self.io.ai_output(self.partial_response_content)
            elif self.partial_response_function_call:
                # TODO: push this into subclasses
                args = self.parse_partial_args()
                if args:
                    self.io.ai_output(json.dumps(args, indent=4))

        return interrupted

    def show_send_output(self, completion, silent):
        if self.verbose:
            print(completion)

        show_func_err = None
        show_content_err = None
        try:
            self.partial_response_function_call = completion.choices[0].message.function_call
        except AttributeError as func_err:
            show_func_err = func_err

        try:
            self.partial_response_content = completion.choices[0].message.content
        except AttributeError as content_err:
            show_content_err = content_err

        resp_hash = dict(
            function_call=self.partial_response_function_call,
            content=self.partial_response_content,
        )
        resp_hash = hashlib.sha1(json.dumps(resp_hash, sort_keys=True).encode())
        self.chat_completion_response_hashes.append(resp_hash.hexdigest())

        if show_func_err and show_content_err:
            self.io.tool_error(show_func_err)
            self.io.tool_error(show_content_err)
            raise Exception("No data found in openai response!")

        prompt_tokens = completion.usage.prompt_tokens
        completion_tokens = completion.usage.completion_tokens

        tokens = f"{prompt_tokens} prompt tokens, {completion_tokens} completion tokens"
        if self.main_model.prompt_price:
            cost = prompt_tokens * self.main_model.prompt_price / 1000
            cost += completion_tokens * self.main_model.completion_price / 1000
            tokens += f", ${cost:.6f} cost"
            self.total_cost += cost

        show_resp = self.render_incremental_response(True)
        if self.pretty:
            show_resp = Markdown(
                show_resp, style=self.assistant_output_color, code_theme=self.code_theme
            )
        else:
            show_resp = Text(show_resp or "<no response>")

        self.io.console.print(show_resp)
        self.io.console.print(tokens)

    def show_send_output_stream(self, completion, silent):
        live = None
        if self.pretty and not silent:
            live = Live(vertical_overflow="scroll")

        try:
            if live:
                live.start()

            for chunk in completion:
                if chunk.choices[0].finish_reason == "length":
                    raise ExhaustedContextWindow()

                try:
                    func = chunk.choices[0].delta.function_call
                    # dump(func)
                    for k, v in func.items():
                        if k in self.partial_response_function_call:
                            self.partial_response_function_call[k] += v
                        else:
                            self.partial_response_function_call[k] = v
                except AttributeError:
                    pass

                try:
                    text = chunk.choices[0].delta.content
                    if text:
                        self.partial_response_content += text
                except AttributeError:
                    pass

                if silent:
                    continue

                if self.pretty:
                    self.live_incremental_response(live, False)
                else:
                    sys.stdout.write(text)
                    sys.stdout.flush()
        finally:
            if live:
                self.live_incremental_response(live, True)
                live.stop()

    def live_incremental_response(self, live, final):
        show_resp = self.render_incremental_response(final)
        if not show_resp:
            return

        md = Markdown(show_resp, style=self.assistant_output_color, code_theme=self.code_theme)
        live.update(md)

    def render_incremental_response(self, final):
        return self.partial_response_content

    def get_context_from_history(self, history):
        context = ""
        if history:
            for msg in history:
                context += "\n" + msg["role"].upper() + ": " + msg["content"] + "\n"
        return context

    def get_commit_message(self, diffs, context):
        if len(diffs) >= 4 * 1024 * 4:
            self.io.tool_error(
                f"Diff is too large for {models.GPT35.name} to generate a commit message."
            )
            return

        diffs = "# Diffs:\n" + diffs

        messages = [
            dict(role="system", content=prompts.commit_system),
            dict(role="user", content=context + diffs),
        ]

        try:
            interrupted = self.send(
                messages,
                model=models.GPT35.name,
                silent=True,
            )
        except openai.error.InvalidRequestError:
            self.io.tool_error(
                f"Failed to generate commit message using {models.GPT35.name} due to an invalid"
                " request."
            )
            return

        commit_message = self.partial_response_content
        commit_message = commit_message.strip()
        if commit_message and commit_message[0] == '"' and commit_message[-1] == '"':
            commit_message = commit_message[1:-1].strip()

        if interrupted:
            self.io.tool_error(
                f"Unable to get commit message from {models.GPT35.name}. Use /commit to try again."
            )
            return

        return commit_message

    def get_diffs(self, *args):
        if self.pretty:
            args = ["--color"] + list(args)

        diffs = self.repo.git.diff(*args)
        return diffs

    def commit(self, history=None, prefix=None, ask=False, message=None, which="chat_files"):
        repo = self.repo
        if not repo:
            return

        if not repo.is_dirty():
            return

        def get_dirty_files_and_diffs(file_list):
            diffs = ""
            relative_dirty_files = []
            for fname in file_list:
                relative_fname = self.get_rel_fname(fname)
                relative_dirty_files.append(relative_fname)

                try:
                    current_branch_commit_count = len(
                        list(self.repo.iter_commits(self.repo.active_branch))
                    )
                except git.exc.GitCommandError:
                    current_branch_commit_count = None

                if not current_branch_commit_count:
                    continue

                these_diffs = self.get_diffs("HEAD", "--", relative_fname)

                if these_diffs:
                    diffs += these_diffs + "\n"

            return relative_dirty_files, diffs

        if which == "repo_files":
            all_files = [os.path.join(self.root, f) for f in self.get_all_relative_files()]
            relative_dirty_fnames, diffs = get_dirty_files_and_diffs(all_files)
        elif which == "chat_files":
            relative_dirty_fnames, diffs = get_dirty_files_and_diffs(self.abs_fnames)
        else:
            raise ValueError(f"Invalid value for 'which': {which}")

        if self.show_diffs or ask:
            # don't use io.tool_output() because we don't want to log or further colorize
            print(diffs)

        context = self.get_context_from_history(history)
        if message:
            commit_message = message
        else:
            commit_message = self.get_commit_message(diffs, context)

        if not commit_message:
            commit_message = "work in progress"

        if prefix:
            commit_message = prefix + commit_message

        if ask:
            if which == "repo_files":
                self.io.tool_output("Git repo has uncommitted changes.")
            else:
                self.io.tool_output("Files have uncommitted changes.")

            res = self.io.prompt_ask(
                "Commit before the chat proceeds [y/n/commit message]?",
                default=commit_message,
            ).strip()
            self.last_asked_for_commit_time = self.get_last_modified()

            self.io.tool_output()

            if res.lower() in ["n", "no"]:
                self.io.tool_error("Skipped commmit.")
                return
            if res.lower() not in ["y", "yes"] and res:
                commit_message = res

        repo.git.add(*relative_dirty_fnames)

        full_commit_message = commit_message + "\n\n# Aider chat conversation:\n\n" + context
        repo.git.commit("-m", full_commit_message, "--no-verify")
        commit_hash = repo.head.commit.hexsha[:7]
        self.io.tool_output(f"Commit {commit_hash} {commit_message}")

        return commit_hash, commit_message

    def get_rel_fname(self, fname):
        return os.path.relpath(fname, self.root)

    def get_inchat_relative_files(self):
        files = [self.get_rel_fname(fname) for fname in self.abs_fnames]
        return sorted(set(files))

    def get_all_relative_files(self):
        if self.repo:
            files = self.get_tracked_files()
        else:
            files = self.get_inchat_relative_files()

        return sorted(set(files))

    def get_all_abs_files(self):
        files = self.get_all_relative_files()
        files = [self.abs_root_path(path) for path in files]
        return files

    def get_last_modified(self):
        files = [Path(fn) for fn in self.get_all_abs_files() if Path(fn).exists()]
        if not files:
            return 0
        return max(path.stat().st_mtime for path in files)

    def get_addable_relative_files(self):
        return set(self.get_all_relative_files()) - set(self.get_inchat_relative_files())

    def allowed_to_edit(self, path, write_content=None):
        full_path = self.abs_root_path(path)

        if full_path in self.abs_fnames:
            if write_content:
                self.io.write_text(full_path, write_content)
            return full_path

        if not Path(full_path).exists():
            question = f"Allow creation of new file {path}?"  # noqa: E501
        else:
            question = f"Allow edits to {path} which was not previously provided?"  # noqa: E501
        if not self.io.confirm_ask(question):
            self.io.tool_error(f"Skipping edit to {path}")
            return

        if not Path(full_path).exists() and not self.dry_run:
            Path(full_path).parent.mkdir(parents=True, exist_ok=True)
            Path(full_path).touch()

        self.abs_fnames.add(full_path)

        # Check if the file is already in the repo
        if self.repo:
            tracked_files = set(self.get_tracked_files())
            relative_fname = self.get_rel_fname(full_path)
            if relative_fname not in tracked_files and self.io.confirm_ask(f"Add {path} to git?"):
                if not self.dry_run:
                    self.repo.git.add(full_path)

        if write_content:
            self.io.write_text(full_path, write_content)

        return full_path

    def get_tracked_files(self):
        if not self.repo:
            return []

        try:
            commit = self.repo.head.commit
        except ValueError:
            return set()

        files = []
        for blob in commit.tree.traverse():
            if blob.type == "blob":  # blob is a file
                files.append(blob.path)

        # convert to appropriate os.sep, since git always normalizes to /
        res = set(str(Path(PurePosixPath(path))) for path in files)

        return res

    apply_update_errors = 0

    def apply_updates(self):
        max_apply_update_errors = 3

        try:
            edited = self.update_files()
        except ValueError as err:
            err = err.args[0]
            self.apply_update_errors += 1
            if self.apply_update_errors < max_apply_update_errors:
                self.io.tool_error(f"Malformed response #{self.apply_update_errors}, retrying...")
                self.io.tool_error(str(err))
                return None, err
            else:
                self.io.tool_error(f"Malformed response #{self.apply_update_errors}, aborting.")
                return False, None

        except Exception as err:
            print(err)
            print()
            traceback.print_exc()
            self.apply_update_errors += 1
            if self.apply_update_errors < max_apply_update_errors:
                self.io.tool_error(f"Update exception #{self.apply_update_errors}, retrying...")
                return None, str(err)
            else:
                self.io.tool_error(f"Update exception #{self.apply_update_errors}, aborting")
                return False, None

        self.apply_update_errors = 0

        if edited:
            for path in sorted(edited):
                if self.dry_run:
                    self.io.tool_output(f"Did not apply edit to {path} (--dry-run)")
                else:
                    self.io.tool_output(f"Applied edit to {path}")

        return edited, None

    def parse_partial_args(self):
        # dump(self.partial_response_function_call)

        data = self.partial_response_function_call.get("arguments")
        if not data:
            return

        try:
            return json.loads(data)
        except JSONDecodeError:
            pass

        try:
            return json.loads(data + "]}")
        except JSONDecodeError:
            pass

        try:
            return json.loads(data + "}]}")
        except JSONDecodeError:
            pass

        try:
            return json.loads(data + '"}]}')
        except JSONDecodeError:
            pass


def check_model_availability(main_model):
    available_models = openai.Model.list()
    model_ids = [model.id for model in available_models["data"]]
    return main_model.name in model_ids
