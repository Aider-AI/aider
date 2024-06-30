#!/usr/bin/env python

import hashlib
import json
import os
import re
import sys
import threading
import time
import traceback
from collections import defaultdict
from json.decoder import JSONDecodeError
from pathlib import Path

import git
from jsonschema import Draft7Validator
from rich.console import Console, Text
from rich.markdown import Markdown

from aider import __version__, models, prompts, urls, utils
from aider.commands import Commands
from aider.history import ChatSummary
from aider.io import InputOutput
from aider.linter import Linter
from aider.litellm import litellm
from aider.mdstream import MarkdownStream
from aider.repo import GitRepo
from aider.repomap import RepoMap
from aider.sendchat import send_with_retries
from aider.utils import format_content, format_messages, is_image_file

from ..dump import dump  # noqa: F401


class MissingAPIKeyError(ValueError):
    pass


class FinishReasonLength(Exception):
    pass


def wrap_fence(name):
    return f"<{name}>", f"</{name}>"


class Coder:
    abs_fnames = None
    repo = None
    last_aider_commit_hash = None
    aider_edited_files = None
    last_asked_for_commit_time = 0
    repo_map = None
    functions = None
    total_cost = 0.0
    num_exhausted_context_windows = 0
    num_malformed_responses = 0
    last_keyboard_interrupt = None
    num_reflections = 0
    max_reflections = 3
    edit_format = None
    yield_stream = False
    temperature = 0
    auto_lint = True
    auto_test = False
    test_cmd = None
    lint_outcome = None
    test_outcome = None
    multi_response_content = ""

    @classmethod
    def create(
        self,
        main_model=None,
        edit_format=None,
        io=None,
        from_coder=None,
        **kwargs,
    ):
        from . import (
            EditBlockCoder,
            EditBlockFencedCoder,
            UnifiedDiffCoder,
            WholeFileCoder,
        )

        if not main_model:
            if from_coder:
                main_model = from_coder.main_model
            else:
                main_model = models.Model(models.DEFAULT_MODEL_NAME)

        if edit_format is None:
            if from_coder:
                edit_format = from_coder.edit_format
            else:
                edit_format = main_model.edit_format

        if not io and from_coder:
            io = from_coder.io

        if from_coder:
            use_kwargs = dict(from_coder.original_kwargs)  # copy orig kwargs

            # If the edit format changes, we can't leave old ASSISTANT
            # messages in the chat history. The old edit format will
            # confused the new LLM. It may try and imitate it, disobeying
            # the system prompt.
            done_messages = from_coder.done_messages
            if edit_format != from_coder.edit_format and done_messages:
                done_messages = from_coder.summarizer.summarize_all(done_messages)

            # Bring along context from the old Coder
            update = dict(
                fnames=from_coder.get_inchat_relative_files(),
                done_messages=done_messages,
                cur_messages=from_coder.cur_messages,
            )

            use_kwargs.update(update)  # override to complete the switch
            use_kwargs.update(kwargs)  # override passed kwargs

            kwargs = use_kwargs

        if edit_format == "diff":
            res = EditBlockCoder(main_model, io, **kwargs)
        elif edit_format == "diff-fenced":
            res = EditBlockFencedCoder(main_model, io, **kwargs)
        elif edit_format == "whole":
            res = WholeFileCoder(main_model, io, **kwargs)
        elif edit_format == "udiff":
            res = UnifiedDiffCoder(main_model, io, **kwargs)
        else:
            raise ValueError(f"Unknown edit format {edit_format}")

        res.original_kwargs = dict(kwargs)

        return res

    def clone(self, **kwargs):
        return Coder.create(from_coder=self, **kwargs)

    def get_announcements(self):
        lines = []
        lines.append(f"Aider v{__version__}")

        # Model
        main_model = self.main_model
        weak_model = main_model.weak_model
        prefix = "Model:"
        output = f" {main_model.name} with {self.edit_format} edit format"
        if weak_model is not main_model:
            prefix = "Models:"
            output += f", weak model {weak_model.name}"
        lines.append(prefix + output)

        # Repo
        if self.repo:
            rel_repo_dir = self.repo.get_rel_repo_dir()
            num_files = len(self.repo.get_tracked_files())
            lines.append(f"Git repo: {rel_repo_dir} with {num_files:,} files")
            if num_files > 1000:
                lines.append(
                    "Warning: For large repos, consider using an .aiderignore file to ignore"
                    " irrelevant files/dirs."
                )
        else:
            lines.append("Git repo: none")

        # Repo-map
        if self.repo_map:
            map_tokens = self.repo_map.max_map_tokens
            if map_tokens > 0:
                lines.append(f"Repo-map: using {map_tokens} tokens")
                max_map_tokens = 2048
                if map_tokens > max_map_tokens:
                    lines.append(
                        f"Warning: map-tokens > {max_map_tokens} is not recommended as too much"
                        " irrelevant code can confuse GPT."
                    )
            else:
                lines.append("Repo-map: disabled because map_tokens == 0")
        else:
            lines.append("Repo-map: disabled")

        # Files
        for fname in self.get_inchat_relative_files():
            lines.append(f"Added {fname} to the chat.")

        if self.done_messages:
            lines.append("Restored previous conversation history.")

        return lines

    def __init__(
        self,
        main_model,
        io,
        fnames=None,
        git_dname=None,
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
        voice_language=None,
        aider_ignore_file=None,
        cur_messages=None,
        done_messages=None,
        max_chat_history_tokens=None,
        restore_chat_history=False,
        auto_lint=True,
        auto_test=False,
        lint_cmds=None,
        test_cmd=None,
        attribute_author=True,
        attribute_committer=True,
        attribute_commit_message=False,
    ):
        if not fnames:
            fnames = []

        if io is None:
            io = InputOutput()

        self.chat_completion_call_hashes = []
        self.chat_completion_response_hashes = []
        self.need_commit_before_edits = set()

        self.verbose = verbose
        self.abs_fnames = set()

        if cur_messages:
            self.cur_messages = cur_messages
        else:
            self.cur_messages = []

        if done_messages:
            self.done_messages = done_messages
        else:
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

        self.show_diffs = show_diffs

        self.commands = Commands(self.io, self, voice_language)

        if use_git:
            try:
                self.repo = GitRepo(
                    self.io,
                    fnames,
                    git_dname,
                    aider_ignore_file,
                    models=main_model.commit_message_models(),
                    attribute_author=attribute_author,
                    attribute_committer=attribute_committer,
                    attribute_commit_message=attribute_commit_message,
                )
                self.root = self.repo.root
            except FileNotFoundError:
                self.repo = None

        for fname in fnames:
            fname = Path(fname)
            if not fname.exists():
                self.io.tool_output(f"Creating empty file {fname}")
                fname.parent.mkdir(parents=True, exist_ok=True)
                fname.touch()

            if not fname.is_file():
                raise ValueError(f"{fname} is not a file")

            fname = str(fname.resolve())

            if self.repo and self.repo.ignored_file(fname):
                self.io.tool_error(f"Skipping {fname} that matches aiderignore spec.")
                continue

            self.abs_fnames.add(fname)
            self.check_added_files()

        if not self.repo:
            self.find_common_root()

        if main_model.use_repo_map and self.repo and self.gpt_prompts.repo_content_prefix:
            self.repo_map = RepoMap(
                map_tokens,
                self.root,
                self.main_model,
                io,
                self.gpt_prompts.repo_content_prefix,
                self.verbose,
                self.main_model.info.get("max_input_tokens"),
            )

        if max_chat_history_tokens is None:
            max_chat_history_tokens = self.main_model.max_chat_history_tokens
        self.summarizer = ChatSummary(
            self.main_model.weak_model,
            max_chat_history_tokens,
        )

        self.summarizer_thread = None
        self.summarized_done_messages = []

        if not self.done_messages and restore_chat_history:
            history_md = self.io.read_text(self.io.chat_history_file)
            if history_md:
                self.done_messages = utils.split_chat_history_markdown(history_md)
                self.summarize_start()

        # Linting and testing
        self.linter = Linter(root=self.root, encoding=io.encoding)
        self.auto_lint = auto_lint
        self.setup_lint_cmds(lint_cmds)

        self.auto_test = auto_test
        self.test_cmd = test_cmd

        # validate the functions jsonschema
        if self.functions:
            for function in self.functions:
                Draft7Validator.check_schema(function)

            if self.verbose:
                self.io.tool_output("JSON Schema:")
                self.io.tool_output(json.dumps(self.functions, indent=4))

    def setup_lint_cmds(self, lint_cmds):
        if not lint_cmds:
            return
        for lang, cmd in lint_cmds.items():
            self.linter.set_linter(lang, cmd)

    def show_announcements(self):
        for line in self.get_announcements():
            self.io.tool_output(line)

    def find_common_root(self):
        if len(self.abs_fnames) == 1:
            self.root = os.path.dirname(list(self.abs_fnames)[0])
        elif self.abs_fnames:
            self.root = os.path.commonpath(list(self.abs_fnames))
        else:
            self.root = os.getcwd()

        self.root = utils.safe_abs_path(self.root)

    def add_rel_fname(self, rel_fname):
        self.abs_fnames.add(self.abs_root_path(rel_fname))
        self.check_added_files()

    def drop_rel_fname(self, fname):
        abs_fname = self.abs_root_path(fname)
        if abs_fname in self.abs_fnames:
            self.abs_fnames.remove(abs_fname)
            return True

    def abs_root_path(self, path):
        res = Path(self.root) / path
        return utils.safe_abs_path(res)

    fences = [
        ("``" + "`", "``" + "`"),
        wrap_fence("source"),
        wrap_fence("code"),
        wrap_fence("pre"),
        wrap_fence("codeblock"),
        wrap_fence("sourcecode"),
    ]
    fence = fences[0]

    def show_pretty(self):
        if not self.pretty:
            return False

        # only show pretty output if fences are the normal triple-backtick
        if self.fence != self.fences[0]:
            return False

        return True

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
                f" {self.fence[0]}...{self.fence[1]}"
            )

        return

    def get_files_content(self, fnames=None):
        if not fnames:
            fnames = self.abs_fnames

        prompt = ""
        for fname, content in self.get_abs_fnames_content():
            if not is_image_file(fname):
                relative_fname = self.get_rel_fname(fname)
                prompt += "\n"
                prompt += relative_fname
                prompt += f"\n{self.fence[0]}\n"

                prompt += content

                # lines = content.splitlines(keepends=True)
                # lines = [f"{i+1:03}:{line}" for i, line in enumerate(lines)]
                # prompt += "".join(lines)

                prompt += f"{self.fence[1]}\n"

        return prompt

    def get_cur_message_text(self):
        text = ""
        for msg in self.cur_messages:
            text += msg["content"] + "\n"
        return text

    def get_ident_mentions(self, text):
        # Split the string on any character that is not alphanumeric
        # \W+ matches one or more non-word characters (equivalent to [^a-zA-Z0-9_]+)
        words = set(re.split(r"\W+", text))
        return words

    def get_ident_filename_matches(self, idents):
        all_fnames = defaultdict(set)
        for fname in self.get_all_relative_files():
            base = Path(fname).with_suffix("").name.lower()
            if len(base) >= 5:
                all_fnames[base].add(fname)

        matches = set()
        for ident in idents:
            if len(ident) < 5:
                continue
            matches.update(all_fnames[ident.lower()])

        return matches

    def get_repo_map(self):
        if not self.repo_map:
            return

        cur_msg_text = self.get_cur_message_text()
        mentioned_fnames = self.get_file_mentions(cur_msg_text)
        mentioned_idents = self.get_ident_mentions(cur_msg_text)

        mentioned_fnames.update(self.get_ident_filename_matches(mentioned_idents))

        other_files = set(self.get_all_abs_files()) - set(self.abs_fnames)
        repo_content = self.repo_map.get_repo_map(
            self.abs_fnames,
            other_files,
            mentioned_fnames=mentioned_fnames,
            mentioned_idents=mentioned_idents,
        )

        # fall back to global repo map if files in chat are disjoint from rest of repo
        if not repo_content:
            repo_content = self.repo_map.get_repo_map(
                set(),
                set(self.get_all_abs_files()),
                mentioned_fnames=mentioned_fnames,
                mentioned_idents=mentioned_idents,
            )

        # fall back to completely unhinted repo
        if not repo_content:
            repo_content = self.repo_map.get_repo_map(
                set(),
                set(self.get_all_abs_files()),
            )

        return repo_content

    def get_files_messages(self):
        files_messages = []

        repo_content = self.get_repo_map()
        if repo_content:
            files_messages += [
                dict(role="user", content=repo_content),
                dict(
                    role="assistant",
                    content="Ok, I won't try and edit those files without asking first.",
                ),
            ]

        if self.abs_fnames:
            files_content = self.gpt_prompts.files_content_prefix
            files_content += self.get_files_content()
            files_reply = "Ok, any changes I propose will be to those files."
        elif repo_content:
            files_content = self.gpt_prompts.files_no_full_files_with_repo_map
            files_reply = (
                "Ok, based on your requests I will suggest which files need to be edited and then"
                " stop and wait for your approval."
            )
        else:
            files_content = self.gpt_prompts.files_no_full_files
            files_reply = "Ok."

        files_messages += [
            dict(role="user", content=files_content),
            dict(role="assistant", content=files_reply),
        ]

        images_message = self.get_images_message()
        if images_message is not None:
            files_messages += [
                images_message,
                dict(role="assistant", content="Ok."),
            ]

        return files_messages

    def get_images_message(self):
        if not self.main_model.accepts_images:
            return None

        image_messages = []
        for fname, content in self.get_abs_fnames_content():
            if is_image_file(fname):
                image_url = f"data:image/{Path(fname).suffix.lstrip('.')};base64,{content}"
                image_messages.append(
                    {"type": "image_url", "image_url": {"url": image_url, "detail": "high"}}
                )

        if not image_messages:
            return None

        return {"role": "user", "content": image_messages}

    def run_stream(self, user_message):
        self.io.user_input(user_message)
        self.init_before_message()
        yield from self.send_new_user_message(user_message)

    def init_before_message(self):
        self.reflected_message = None
        self.num_reflections = 0
        self.lint_outcome = None
        self.test_outcome = None
        self.edit_outcome = None

    def run(self, with_message=None):
        while True:
            self.init_before_message()

            try:
                if with_message:
                    new_user_message = with_message
                    self.io.user_input(with_message)
                else:
                    new_user_message = self.run_loop()

                while new_user_message:
                    self.reflected_message = None
                    list(self.send_new_user_message(new_user_message))

                    new_user_message = None
                    if self.reflected_message:
                        if self.num_reflections < self.max_reflections:
                            self.num_reflections += 1
                            new_user_message = self.reflected_message
                        else:
                            self.io.tool_error(
                                f"Only {self.max_reflections} reflections allowed, stopping."
                            )

                if with_message:
                    return self.partial_response_content

            except KeyboardInterrupt:
                self.keyboard_interrupt()
            except EOFError:
                return

    def run_loop(self):
        inp = self.io.get_input(
            self.root,
            self.get_inchat_relative_files(),
            self.get_addable_relative_files(),
            self.commands,
        )

        if not inp:
            return

        if self.commands.is_command(inp):
            return self.commands.run(inp)

        self.check_for_file_mentions(inp)
        inp = self.check_for_urls(inp)

        return inp

    def check_for_urls(self, inp):
        url_pattern = re.compile(
            r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
        )
        urls = url_pattern.findall(inp)
        for url in urls:
            if self.io.confirm_ask(f"Add {url} to the chat?"):
                inp += "\n\n"
                inp += self.commands.cmd_web(url)

        return inp

    def keyboard_interrupt(self):
        now = time.time()

        thresh = 2  # seconds
        if self.last_keyboard_interrupt and now - self.last_keyboard_interrupt < thresh:
            self.io.tool_error("\n\n^C KeyboardInterrupt")
            sys.exit()

        self.io.tool_error("\n\n^C again to exit")

        self.last_keyboard_interrupt = now

    def summarize_start(self):
        if not self.summarizer.too_big(self.done_messages):
            return

        self.summarize_end()

        if self.verbose:
            self.io.tool_output("Starting to summarize chat history.")

        self.summarizer_thread = threading.Thread(target=self.summarize_worker)
        self.summarizer_thread.start()

    def summarize_worker(self):
        try:
            self.summarized_done_messages = self.summarizer.summarize(self.done_messages)
        except ValueError as err:
            self.io.tool_error(err.args[0])

        if self.verbose:
            self.io.tool_output("Finished summarizing chat history.")

    def summarize_end(self):
        if self.summarizer_thread is None:
            return

        self.summarizer_thread.join()
        self.summarizer_thread = None

        self.done_messages = self.summarized_done_messages
        self.summarized_done_messages = []

    def move_back_cur_messages(self, message):
        self.done_messages += self.cur_messages
        self.summarize_start()

        # TODO check for impact on image messages
        if message:
            self.done_messages += [
                dict(role="user", content=message),
                dict(role="assistant", content="Ok."),
            ]
        self.cur_messages = []

    def fmt_system_prompt(self, prompt):
        lazy_prompt = self.gpt_prompts.lazy_prompt if self.main_model.lazy else ""

        prompt = prompt.format(fence=self.fence, lazy_prompt=lazy_prompt)
        return prompt

    def format_messages(self):
        self.choose_fence()
        main_sys = self.fmt_system_prompt(self.gpt_prompts.main_system)

        example_messages = []
        if self.main_model.examples_as_sys_msg:
            main_sys += "\n# Example conversations:\n\n"
            for msg in self.gpt_prompts.example_messages:
                role = msg["role"]
                content = self.fmt_system_prompt(msg["content"])
                main_sys += f"## {role.upper()}: {content}\n\n"
            main_sys = main_sys.strip()
        else:
            for msg in self.gpt_prompts.example_messages:
                example_messages.append(
                    dict(
                        role=msg["role"],
                        content=self.fmt_system_prompt(msg["content"]),
                    )
                )
            if self.gpt_prompts.example_messages:
                example_messages += [
                    dict(
                        role="user",
                        content=(
                            "I switched to a new code base. Please don't consider the above files"
                            " or try to edit them any longer."
                        ),
                    ),
                    dict(role="assistant", content="Ok."),
                ]

        main_sys += "\n" + self.fmt_system_prompt(self.gpt_prompts.system_reminder)
        messages = [
            dict(role="system", content=main_sys),
        ]
        messages += example_messages

        self.summarize_end()
        messages += self.done_messages
        messages += self.get_files_messages()

        reminder_message = [
            dict(role="system", content=self.fmt_system_prompt(self.gpt_prompts.system_reminder)),
        ]

        # TODO review impact of token count on image messages
        messages_tokens = self.main_model.token_count(messages)
        reminder_tokens = self.main_model.token_count(reminder_message)
        cur_tokens = self.main_model.token_count(self.cur_messages)

        if None not in (messages_tokens, reminder_tokens, cur_tokens):
            total_tokens = messages_tokens + reminder_tokens + cur_tokens
        else:
            # add the reminder anyway
            total_tokens = 0

        messages += self.cur_messages

        final = messages[-1]

        max_input_tokens = self.main_model.info.get("max_input_tokens")
        # Add the reminder prompt if we still have room to include it.
        if max_input_tokens is None or total_tokens < max_input_tokens:
            if self.main_model.reminder_as_sys_msg:
                messages += reminder_message
            elif final["role"] == "user":
                # stuff it into the user message
                new_content = (
                    final["content"]
                    + "\n\n"
                    + self.fmt_system_prompt(self.gpt_prompts.system_reminder)
                )
                messages[-1] = dict(role=final["role"], content=new_content)

        return messages

    def send_new_user_message(self, inp):
        self.aider_edited_files = None

        self.cur_messages += [
            dict(role="user", content=inp),
        ]

        messages = self.format_messages()

        if self.verbose:
            utils.show_messages(messages, functions=self.functions)

        self.multi_response_content = ""
        if self.show_pretty() and self.stream:
            mdargs = dict(style=self.assistant_output_color, code_theme=self.code_theme)
            self.mdstream = MarkdownStream(mdargs=mdargs)
        else:
            self.mdstream = None

        exhausted = False
        interrupted = False
        try:
            while True:
                try:
                    yield from self.send(messages, functions=self.functions)
                    break
                except KeyboardInterrupt:
                    interrupted = True
                    break
                except litellm.ContextWindowExceededError:
                    # The input is overflowing the context window!
                    exhausted = True
                    break
                except litellm.exceptions.BadRequestError as br_err:
                    self.io.tool_error(f"BadRequestError: {br_err}")
                    return
                except FinishReasonLength:
                    # We hit the 4k output limit!
                    if not self.main_model.can_prefill:
                        exhausted = True
                        break

                    self.multi_response_content = self.get_multi_response_content()

                    if messages[-1]["role"] == "assistant":
                        messages[-1]["content"] = self.multi_response_content
                    else:
                        messages.append(dict(role="assistant", content=self.multi_response_content))
                except Exception as err:
                    self.io.tool_error(f"Unexpected error: {err}")
                    traceback.print_exc()
                    return
        finally:
            if self.mdstream:
                self.live_incremental_response(True)
                self.mdstream = None

            self.partial_response_content = self.get_multi_response_content(True)
            self.multi_response_content = ""

        if exhausted:
            self.show_exhausted_error()
            self.num_exhausted_context_windows += 1
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

        self.io.tool_output()

        if interrupted:
            content += "\n^C KeyboardInterrupt"
            self.cur_messages += [dict(role="assistant", content=content)]
            return

        edited = self.apply_updates()
        if self.reflected_message:
            self.edit_outcome = False
            self.update_cur_messages(set())
            return
        if edited:
            self.edit_outcome = True

        if edited and self.auto_lint:
            lint_errors = self.lint_edited(edited)
            self.lint_outcome = not lint_errors
            if lint_errors:
                ok = self.io.confirm_ask("Attempt to fix lint errors?")
                if ok:
                    self.reflected_message = lint_errors
                    self.update_cur_messages(set())
                    return

        if edited and self.auto_test:
            test_errors = self.commands.cmd_test(self.test_cmd)
            self.test_outcome = not test_errors
            if test_errors:
                ok = self.io.confirm_ask("Attempt to fix test errors?")
                if ok:
                    self.reflected_message = test_errors
                    self.update_cur_messages(set())
                    return

        self.update_cur_messages(edited)

        if edited:
            self.aider_edited_files = edited
            if self.repo and self.auto_commits and not self.dry_run:
                saved_message = self.auto_commit(edited)
            elif hasattr(self.gpt_prompts, "files_content_gpt_edits_no_repo"):
                saved_message = self.gpt_prompts.files_content_gpt_edits_no_repo
            else:
                saved_message = None

            self.move_back_cur_messages(saved_message)

        add_rel_files_message = self.check_for_file_mentions(content)
        if add_rel_files_message:
            if self.reflected_message:
                self.reflected_message += "\n\n" + add_rel_files_message
            else:
                self.reflected_message = add_rel_files_message

    def show_exhausted_error(self):
        output_tokens = 0
        if self.partial_response_content:
            output_tokens = self.main_model.token_count(self.partial_response_content)
        max_output_tokens = self.main_model.info.get("max_output_tokens", 0)

        input_tokens = self.main_model.token_count(self.format_messages())
        max_input_tokens = self.main_model.info.get("max_input_tokens", 0)

        total_tokens = input_tokens + output_tokens

        fudge = 0.7

        out_err = ""
        if output_tokens >= max_output_tokens * fudge:
            out_err = " -- possibly exceeded output limit!"

        inp_err = ""
        if input_tokens >= max_input_tokens * fudge:
            inp_err = " -- possibly exhausted context window!"

        tot_err = ""
        if total_tokens >= max_input_tokens * fudge:
            tot_err = " -- possibly exhausted context window!"

        res = ["", ""]
        res.append(f"Model {self.main_model.name} has hit a token limit!")
        res.append("Token counts below are approximate.")
        res.append("")
        res.append(f"Input tokens: ~{input_tokens:,} of {max_input_tokens:,}{inp_err}")
        res.append(f"Output tokens: ~{output_tokens:,} of {max_output_tokens:,}{out_err}")
        res.append(f"Total tokens: ~{total_tokens:,} of {max_input_tokens:,}{tot_err}")

        if output_tokens >= max_output_tokens:
            res.append("")
            res.append("To reduce output tokens:")
            res.append("- Ask for smaller changes in each request.")
            res.append("- Break your code into smaller source files.")
            if "diff" not in self.main_model.edit_format:
                res.append(
                    "- Use a stronger model like gpt-4o, sonnet or opus that can return diffs."
                )

        if input_tokens >= max_input_tokens or total_tokens >= max_input_tokens:
            res.append("")
            res.append("To reduce input tokens:")
            res.append("- Use /tokens to see token usage.")
            res.append("- Use /drop to remove unneeded files from the chat session.")
            res.append("- Use /clear to clear the chat history.")
            res.append("- Break your code into smaller source files.")

        res.append("")
        res.append(f"For more info: {urls.token_limits}")

        res = "".join([line + "\n" for line in res])
        self.io.tool_error(res)

    def lint_edited(self, fnames):
        res = ""
        for fname in fnames:
            errors = self.linter.lint(self.abs_root_path(fname))
            if errors:
                res += "\n"
                res += errors
                res += "\n"

        if res:
            self.io.tool_error(res)

        return res

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

    def get_file_mentions(self, content):
        words = set(word for word in content.split())

        # drop sentence punctuation from the end
        words = set(word.rstrip(",.!;:") for word in words)

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

            # Don't add basenames that could be plain words like "run" or "make"
            if "/" in fname or "." in fname or "_" in fname or "-" in fname:
                if fname not in fname_to_rel_fnames:
                    fname_to_rel_fnames[fname] = []
                fname_to_rel_fnames[fname].append(rel_fname)

        for fname, rel_fnames in fname_to_rel_fnames.items():
            if len(rel_fnames) == 1 and fname in words:
                mentioned_rel_fnames.add(rel_fnames[0])

        return mentioned_rel_fnames

    def check_for_file_mentions(self, content):
        mentioned_rel_fnames = self.get_file_mentions(content)

        if not mentioned_rel_fnames:
            return

        for rel_fname in mentioned_rel_fnames:
            self.io.tool_output(rel_fname)

        if not self.io.confirm_ask("Add these files to the chat?"):
            return

        for rel_fname in mentioned_rel_fnames:
            self.add_rel_fname(rel_fname)

        return prompts.added_files.format(fnames=", ".join(mentioned_rel_fnames))

    def send(self, messages, model=None, functions=None):
        if not model:
            model = self.main_model.name

        self.partial_response_content = ""
        self.partial_response_function_call = dict()

        self.io.log_llm_history("TO LLM", format_messages(messages))

        interrupted = False
        try:
            hash_object, completion = send_with_retries(
                model, messages, functions, self.stream, self.temperature
            )
            self.chat_completion_call_hashes.append(hash_object.hexdigest())

            if self.stream:
                yield from self.show_send_output_stream(completion)
            else:
                self.show_send_output(completion)
        except KeyboardInterrupt:
            self.keyboard_interrupt()
            interrupted = True
        finally:
            self.io.log_llm_history(
                "LLM RESPONSE",
                format_content("ASSISTANT", self.partial_response_content),
            )

            if self.partial_response_content:
                self.io.ai_output(self.partial_response_content)
            elif self.partial_response_function_call:
                # TODO: push this into subclasses
                args = self.parse_partial_args()
                if args:
                    self.io.ai_output(json.dumps(args, indent=4))

        if interrupted:
            raise KeyboardInterrupt

    def show_send_output(self, completion):
        if self.verbose:
            print(completion)

        if not completion.choices:
            self.io.tool_error(str(completion))
            return

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
            raise Exception("No data found in LLM response!")

        tokens = None
        if hasattr(completion, "usage") and completion.usage is not None:
            prompt_tokens = completion.usage.prompt_tokens
            completion_tokens = completion.usage.completion_tokens

            tokens = f"{prompt_tokens} prompt tokens, {completion_tokens} completion tokens"
            if self.main_model.info.get("input_cost_per_token"):
                cost = prompt_tokens * self.main_model.info.get("input_cost_per_token")
                if self.main_model.info.get("output_cost_per_token"):
                    cost += completion_tokens * self.main_model.info.get("output_cost_per_token")
                tokens += f", ${cost:.6f} cost"
                self.total_cost += cost

        show_resp = self.render_incremental_response(True)
        if self.show_pretty():
            show_resp = Markdown(
                show_resp, style=self.assistant_output_color, code_theme=self.code_theme
            )
        else:
            show_resp = Text(show_resp or "<no response>")

        self.io.console.print(show_resp)

        if tokens is not None:
            self.io.tool_output(tokens)

        if (
            hasattr(completion.choices[0], "finish_reason")
            and completion.choices[0].finish_reason == "length"
        ):
            raise FinishReasonLength()

    def show_send_output_stream(self, completion):
        for chunk in completion:
            if len(chunk.choices) == 0:
                continue

            if (
                hasattr(chunk.choices[0], "finish_reason")
                and chunk.choices[0].finish_reason == "length"
            ):
                raise FinishReasonLength()

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
                text = None

            if self.show_pretty():
                self.live_incremental_response(False)
            elif text:
                sys.stdout.write(text)
                sys.stdout.flush()
                yield text

    def live_incremental_response(self, final):
        show_resp = self.render_incremental_response(final)
        self.mdstream.update(show_resp, final=final)

    def render_incremental_response(self, final):
        return self.get_multi_response_content()

    def get_multi_response_content(self, final=False):
        cur = self.multi_response_content
        new = self.partial_response_content

        if new.rstrip() != new and not final:
            new = new.rstrip()
        return cur + new

    def get_rel_fname(self, fname):
        return os.path.relpath(fname, self.root)

    def get_inchat_relative_files(self):
        files = [self.get_rel_fname(fname) for fname in self.abs_fnames]
        return sorted(set(files))

    def get_all_relative_files(self):
        if self.repo:
            files = self.repo.get_tracked_files()
        else:
            files = self.get_inchat_relative_files()

        files = [fname for fname in files if Path(self.abs_root_path(fname)).is_file()]
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

    def check_for_dirty_commit(self, path):
        if not self.repo:
            return
        if not self.dirty_commits:
            return
        if not self.repo.is_dirty(path):
            return

        fullp = Path(self.abs_root_path(path))
        if not fullp.stat().st_size:
            return

        self.io.tool_output(f"Committing {path} before applying edits.")
        self.need_commit_before_edits.add(path)

    def allowed_to_edit(self, path):
        full_path = self.abs_root_path(path)
        if self.repo:
            need_to_add = not self.repo.path_in_repo(path)
        else:
            need_to_add = False

        if full_path in self.abs_fnames:
            self.check_for_dirty_commit(path)
            return True

        if not Path(full_path).exists():
            if not self.io.confirm_ask(f"Allow creation of new file {path}?"):
                self.io.tool_error(f"Skipping edits to {path}")
                return

            if not self.dry_run:
                Path(full_path).parent.mkdir(parents=True, exist_ok=True)
                Path(full_path).touch()

                # Seems unlikely that we needed to create the file, but it was
                # actually already part of the repo.
                # But let's only add if we need to, just to be safe.
                if need_to_add:
                    self.repo.repo.git.add(full_path)

            self.abs_fnames.add(full_path)
            self.check_added_files()
            return True

        if not self.io.confirm_ask(
            f"Allow edits to {path} which was not previously added to chat?"
        ):
            self.io.tool_error(f"Skipping edits to {path}")
            return

        if need_to_add:
            self.repo.repo.git.add(full_path)

        self.abs_fnames.add(full_path)
        self.check_added_files()
        self.check_for_dirty_commit(path)

        return True

    warning_given = False

    def check_added_files(self):
        if self.warning_given:
            return

        warn_number_of_files = 4
        warn_number_of_tokens = 20 * 1024

        num_files = len(self.abs_fnames)
        if num_files < warn_number_of_files:
            return

        tokens = 0
        for fname in self.abs_fnames:
            relative_fname = self.get_rel_fname(fname)
            if is_image_file(relative_fname):
                continue
            content = self.io.read_text(fname)
            tokens += self.main_model.token_count(content)

        if tokens < warn_number_of_tokens:
            return

        self.io.tool_error("Warning: it's best to only add files that need changes to the chat.")
        self.io.tool_error(urls.edit_errors)
        self.warning_given = True

    def prepare_to_edit(self, edits):
        res = []
        seen = dict()

        self.need_commit_before_edits = set()

        for edit in edits:
            path = edit[0]
            if path in seen:
                allowed = seen[path]
            else:
                allowed = self.allowed_to_edit(path)
                seen[path] = allowed

            if allowed:
                res.append(edit)

        self.dirty_commit()
        self.need_commit_before_edits = set()

        return res

    def update_files(self):
        edits = self.get_edits()
        edits = self.prepare_to_edit(edits)
        self.apply_edits(edits)
        return set(edit[0] for edit in edits)

    def apply_updates(self):
        try:
            edited = self.update_files()
        except ValueError as err:
            self.num_malformed_responses += 1

            err = err.args[0]

            self.io.tool_error("The LLM did not conform to the edit format.")
            self.io.tool_error(urls.edit_errors)
            self.io.tool_error()
            self.io.tool_error(str(err), strip=False)

            self.reflected_message = str(err)
            return

        except git.exc.GitCommandError as err:
            self.io.tool_error(str(err))
            return
        except Exception as err:
            self.io.tool_error("Exception while updating files:")
            self.io.tool_error(str(err), strip=False)

            traceback.print_exc()

            self.reflected_message = str(err)
            return

        for path in edited:
            if self.dry_run:
                self.io.tool_output(f"Did not apply edit to {path} (--dry-run)")
            else:
                self.io.tool_output(f"Applied edit to {path}")

        return edited

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

    # commits...

    def get_context_from_history(self, history):
        context = ""
        if history:
            for msg in history:
                context += "\n" + msg["role"].upper() + ": " + msg["content"] + "\n"

        return context

    def auto_commit(self, edited):
        context = self.get_context_from_history(self.cur_messages)
        res = self.repo.commit(fnames=edited, context=context, aider_edits=True)
        if res:
            commit_hash, commit_message = res
            self.last_aider_commit_hash = commit_hash
            self.last_aider_commit_message = commit_message
            if self.show_diffs:
                self.commands.cmd_diff()

            return self.gpt_prompts.files_content_gpt_edits.format(
                hash=commit_hash,
                message=commit_message,
            )

        self.io.tool_output("No changes made to git tracked files.")
        return self.gpt_prompts.files_content_gpt_no_edits

    def dirty_commit(self):
        if not self.need_commit_before_edits:
            return
        if not self.dirty_commits:
            return
        if not self.repo:
            return

        self.repo.commit(fnames=self.need_commit_before_edits)

        # files changed, move cur messages back behind the files messages
        # self.move_back_cur_messages(self.gpt_prompts.files_content_local_edits)
        return True
