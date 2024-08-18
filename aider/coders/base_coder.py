#!/usr/bin/env python

import base64
import hashlib
import json
import locale
import math
import mimetypes
import os
import platform
import re
import sys
import threading
import time
import traceback
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from json.decoder import JSONDecodeError
from pathlib import Path
from typing import List

import git
from rich.console import Console, Text
from rich.markdown import Markdown

from aider import __version__, models, prompts, urls, utils
from aider.commands import Commands
from aider.history import ChatSummary
from aider.io import InputOutput
from aider.linter import Linter
from aider.llm import litellm
from aider.mdstream import MarkdownStream
from aider.repo import GitRepo
from aider.repomap import RepoMap
from aider.sendchat import retry_exceptions, send_completion
from aider.utils import format_content, format_messages, is_image_file

from ..dump import dump  # noqa: F401


class MissingAPIKeyError(ValueError):
    pass


class FinishReasonLength(Exception):
    pass


def wrap_fence(name):
    return f"<{name}>", f"</{name}>"


@dataclass
class ChatChunks:
    system: List = field(default_factory=list)
    examples: List = field(default_factory=list)
    done: List = field(default_factory=list)
    repo: List = field(default_factory=list)
    readonly_files: List = field(default_factory=list)
    chat_files: List = field(default_factory=list)
    cur: List = field(default_factory=list)
    reminder: List = field(default_factory=list)

    def all_messages(self):
        return (
            self.system
            + self.examples
            + self.repo
            + self.readonly_files
            + self.done
            + self.chat_files
            + self.cur
            + self.reminder
        )

    def add_cache_control_headers(self):
        if self.examples:
            self.add_cache_control(self.examples)
        else:
            self.add_cache_control(self.system)

        if self.readonly_files:
            self.add_cache_control(self.readonly_files)
        else:
            self.add_cache_control(self.repo)

        self.add_cache_control(self.chat_files)

    def add_cache_control(self, messages):
        if not messages:
            return

        content = messages[-1]["content"]
        if type(content) is str:
            content = dict(
                type="text",
                text=content,
            )
        content["cache_control"] = {"type": "ephemeral"}

        messages[-1]["content"] = [content]


class Coder:
    abs_fnames = None
    abs_read_only_fnames = None
    repo = None
    last_aider_commit_hash = None
    aider_edited_files = None
    last_asked_for_commit_time = 0
    repo_map = None
    functions = None
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
    partial_response_content = ""
    commit_before_message = []
    message_cost = 0.0
    message_tokens_sent = 0
    message_tokens_received = 0

    @classmethod
    def create(
        self,
        main_model=None,
        edit_format=None,
        io=None,
        from_coder=None,
        summarize_from_coder=True,
        **kwargs,
    ):
        import aider.coders as coders

        if not main_model:
            if from_coder:
                main_model = from_coder.main_model
            else:
                main_model = models.Model(models.DEFAULT_MODEL_NAME)

        if edit_format == "code":
            edit_format = None
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
            if edit_format != from_coder.edit_format and done_messages and summarize_from_coder:
                done_messages = from_coder.summarizer.summarize_all(done_messages)

            # Bring along context from the old Coder
            update = dict(
                fnames=list(from_coder.abs_fnames),
                read_only_fnames=list(from_coder.abs_read_only_fnames),  # Copy read-only files
                done_messages=done_messages,
                cur_messages=from_coder.cur_messages,
                aider_commit_hashes=from_coder.aider_commit_hashes,
                commands=from_coder.commands.clone(),
                total_cost=from_coder.total_cost,
            )

            use_kwargs.update(update)  # override to complete the switch
            use_kwargs.update(kwargs)  # override passed kwargs

            kwargs = use_kwargs

        for coder in coders.__all__:
            if hasattr(coder, "edit_format") and coder.edit_format == edit_format:
                res = coder(main_model, io, **kwargs)
                res.original_kwargs = dict(kwargs)
                return res

        raise ValueError(f"Unknown edit format {edit_format}")

    def clone(self, **kwargs):
        return Coder.create(from_coder=self, **kwargs)

    def get_announcements(self):
        lines = []
        lines.append(f"Aider v{__version__}")

        # Model
        main_model = self.main_model
        weak_model = main_model.weak_model
        prefix = "Model:"
        output = f" {main_model.name}"
        if main_model.cache_control and self.cache_prompts:
            output += "⚡"
        output += " with"
        if main_model.info.get("supports_assistant_prefill"):
            output += " ♾️"
        output += f" {self.edit_format} edit format"
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
                    "Warning: For large repos, consider using --subtree-only and .aiderignore"
                )
                lines.append(f"See: {urls.large_repos}")
        else:
            lines.append("Git repo: none")

        # Repo-map
        if self.repo_map:
            map_tokens = self.repo_map.max_map_tokens
            if map_tokens > 0:
                refresh = self.repo_map.refresh
                lines.append(f"Repo-map: using {map_tokens} tokens, {refresh} refresh")
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
        repo=None,
        fnames=None,
        read_only_fnames=None,
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
        cur_messages=None,
        done_messages=None,
        restore_chat_history=False,
        auto_lint=True,
        auto_test=False,
        lint_cmds=None,
        test_cmd=None,
        aider_commit_hashes=None,
        map_mul_no_files=8,
        commands=None,
        summarizer=None,
        total_cost=0.0,
        map_refresh="auto",
        cache_prompts=False,
    ):
        self.commit_before_message = []
        self.aider_commit_hashes = set()
        self.rejected_urls = set()
        self.abs_root_path_cache = {}
        self.cache_prompts = cache_prompts

        if not fnames:
            fnames = []

        if io is None:
            io = InputOutput()

        if aider_commit_hashes:
            self.aider_commit_hashes = aider_commit_hashes
        else:
            self.aider_commit_hashes = set()

        self.chat_completion_call_hashes = []
        self.chat_completion_response_hashes = []
        self.need_commit_before_edits = set()

        self.total_cost = total_cost

        self.verbose = verbose
        self.abs_fnames = set()
        self.abs_read_only_fnames = set()

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
        self.pretty = self.io.pretty

        if self.pretty:
            self.console = Console()
        else:
            self.console = Console(force_terminal=False, no_color=True)

        self.main_model = main_model

        self.show_diffs = show_diffs

        self.commands = commands or Commands(self.io, self)
        self.commands.coder = self

        self.repo = repo
        if use_git and self.repo is None:
            try:
                self.repo = GitRepo(
                    self.io,
                    fnames,
                    None,
                    models=main_model.commit_message_models(),
                )
            except FileNotFoundError:
                pass

        if self.repo:
            self.root = self.repo.root

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

        if read_only_fnames:
            self.abs_read_only_fnames = set()
            for fname in read_only_fnames:
                abs_fname = self.abs_root_path(fname)
                if os.path.exists(abs_fname):
                    self.abs_read_only_fnames.add(abs_fname)
                else:
                    self.io.tool_error(f"Error: Read-only file {fname} does not exist. Skipping.")

        if map_tokens is None:
            use_repo_map = main_model.use_repo_map
            map_tokens = 1024
        else:
            use_repo_map = map_tokens > 0

        max_inp_tokens = self.main_model.info.get("max_input_tokens") or 0

        has_map_prompt = hasattr(self, "gpt_prompts") and self.gpt_prompts.repo_content_prefix

        if use_repo_map and self.repo and has_map_prompt:
            self.repo_map = RepoMap(
                map_tokens,
                self.root,
                self.main_model,
                io,
                self.gpt_prompts.repo_content_prefix,
                self.verbose,
                max_inp_tokens,
                map_mul_no_files=map_mul_no_files,
                refresh=map_refresh,
            )

        self.summarizer = summarizer or ChatSummary(
            [self.main_model.weak_model, self.main_model],
            self.main_model.max_chat_history_tokens,
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
            from jsonschema import Draft7Validator

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
        bold = True
        for line in self.get_announcements():
            self.io.tool_output(line, bold=bold)
            bold = False

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
        key = path
        if key in self.abs_root_path_cache:
            return self.abs_root_path_cache[key]

        res = Path(self.root) / path
        res = utils.safe_abs_path(res)
        self.abs_root_path_cache[key] = res
        return res

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
        for _fname in self.abs_read_only_fnames:
            content = self.io.read_text(_fname)
            if content is not None:
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

    def get_read_only_files_content(self):
        prompt = ""
        for fname in self.abs_read_only_fnames:
            content = self.io.read_text(fname)
            if content is not None and not is_image_file(fname):
                relative_fname = self.get_rel_fname(fname)
                prompt += "\n"
                prompt += relative_fname
                prompt += f"\n{self.fence[0]}\n"
                prompt += content
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

    def get_repo_map(self, force_refresh=False):
        if not self.repo_map:
            return

        cur_msg_text = self.get_cur_message_text()
        mentioned_fnames = self.get_file_mentions(cur_msg_text)
        mentioned_idents = self.get_ident_mentions(cur_msg_text)

        mentioned_fnames.update(self.get_ident_filename_matches(mentioned_idents))

        all_abs_files = set(self.get_all_abs_files())
        repo_abs_read_only_fnames = set(self.abs_read_only_fnames) & all_abs_files
        chat_files = set(self.abs_fnames) | repo_abs_read_only_fnames
        other_files = all_abs_files - chat_files

        repo_content = self.repo_map.get_repo_map(
            chat_files,
            other_files,
            mentioned_fnames=mentioned_fnames,
            mentioned_idents=mentioned_idents,
            force_refresh=force_refresh,
        )

        # fall back to global repo map if files in chat are disjoint from rest of repo
        if not repo_content:
            repo_content = self.repo_map.get_repo_map(
                set(),
                all_abs_files,
                mentioned_fnames=mentioned_fnames,
                mentioned_idents=mentioned_idents,
            )

        # fall back to completely unhinted repo
        if not repo_content:
            repo_content = self.repo_map.get_repo_map(
                set(),
                all_abs_files,
            )

        return repo_content

    def get_repo_messages(self):
        repo_messages = []
        repo_content = self.get_repo_map()
        if repo_content:
            repo_messages += [
                dict(role="user", content=repo_content),
                dict(
                    role="assistant",
                    content="Ok, I won't try and edit those files without asking first.",
                ),
            ]
        return repo_messages

    def get_readonly_files_messages(self):
        readonly_messages = []
        read_only_content = self.get_read_only_files_content()
        if read_only_content:
            readonly_messages += [
                dict(
                    role="user", content=self.gpt_prompts.read_only_files_prefix + read_only_content
                ),
                dict(
                    role="assistant",
                    content="Ok, I will use these files as references.",
                ),
            ]
        return readonly_messages

    def get_chat_files_messages(self):
        chat_files_messages = []
        if self.abs_fnames:
            files_content = self.gpt_prompts.files_content_prefix
            files_content += self.get_files_content()
            files_reply = "Ok, any changes I propose will be to those files."
        elif self.get_repo_map() and self.gpt_prompts.files_no_full_files_with_repo_map:
            files_content = self.gpt_prompts.files_no_full_files_with_repo_map
            files_reply = self.gpt_prompts.files_no_full_files_with_repo_map_reply
        else:
            files_content = self.gpt_prompts.files_no_full_files
            files_reply = "Ok."

        if files_content:
            chat_files_messages += [
                dict(role="user", content=files_content),
                dict(role="assistant", content=files_reply),
            ]

        images_message = self.get_images_message()
        if images_message is not None:
            chat_files_messages += [
                images_message,
                dict(role="assistant", content="Ok."),
            ]

        return chat_files_messages

    def get_images_message(self):
        if not self.main_model.accepts_images:
            return None

        image_messages = []
        for fname, content in self.get_abs_fnames_content():
            if is_image_file(fname):
                with open(fname, "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
                mime_type, _ = mimetypes.guess_type(fname)
                if mime_type and mime_type.startswith("image/"):
                    image_url = f"data:{mime_type};base64,{encoded_string}"
                    rel_fname = self.get_rel_fname(fname)
                    image_messages += [
                        {"type": "text", "text": f"Image file: {rel_fname}"},
                        {"type": "image_url", "image_url": {"url": image_url, "detail": "high"}},
                    ]

        if not image_messages:
            return None

        return {"role": "user", "content": image_messages}

    def run_stream(self, user_message):
        self.io.user_input(user_message)
        self.init_before_message()
        yield from self.send_message(user_message)

    def init_before_message(self):
        self.reflected_message = None
        self.num_reflections = 0
        self.lint_outcome = None
        self.test_outcome = None
        self.edit_outcome = None
        if self.repo:
            self.commit_before_message.append(self.repo.get_head())

    def run(self, with_message=None, preproc=True):
        try:
            if with_message:
                self.io.user_input(with_message)
                self.run_one(with_message, preproc)
                return self.partial_response_content

            while True:
                try:
                    user_message = self.get_input()
                    self.run_one(user_message, preproc)
                    self.show_undo_hint()
                except KeyboardInterrupt:
                    self.keyboard_interrupt()
        except EOFError:
            return

    def get_input(self):
        inchat_files = self.get_inchat_relative_files()
        read_only_files = [self.get_rel_fname(fname) for fname in self.abs_read_only_fnames]
        all_files = sorted(set(inchat_files + read_only_files))
        return self.io.get_input(
            self.root,
            all_files,
            self.get_addable_relative_files(),
            self.commands,
            self.abs_read_only_fnames,
        )

    def preproc_user_input(self, inp):
        if not inp:
            return

        if self.commands.is_command(inp):
            return self.commands.run(inp)

        self.check_for_file_mentions(inp)
        self.check_for_urls(inp)

        return inp

    def run_one(self, user_message, preproc):
        self.init_before_message()

        if preproc:
            message = self.preproc_user_input(user_message)
        else:
            message = user_message

        while message:
            self.reflected_message = None
            list(self.send_message(message))

            if not self.reflected_message:
                break

            if self.num_reflections >= self.max_reflections:
                self.io.tool_error(f"Only {self.max_reflections} reflections allowed, stopping.")
                return

            self.num_reflections += 1
            message = self.reflected_message

    def check_for_urls(self, inp):
        url_pattern = re.compile(r"(https?://[^\s/$.?#].[^\s]*[^\s,.])")
        urls = list(set(url_pattern.findall(inp)))  # Use set to remove duplicates
        added_urls = []
        for url in urls:
            if url not in self.rejected_urls:
                if self.io.confirm_ask(f"Add {url} to the chat?"):
                    inp += "\n\n"
                    inp += self.commands.cmd_web(url, paginate=False)
                    added_urls.append(url)
                else:
                    self.rejected_urls.add(url)

        return added_urls

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

    def get_user_language(self):
        try:
            lang = locale.getlocale()[0]
            if lang:
                return lang  # Return the full language code, including country
        except Exception:
            pass

        for env_var in ["LANG", "LANGUAGE", "LC_ALL", "LC_MESSAGES"]:
            lang = os.environ.get(env_var)
            if lang:
                return lang.split(".")[
                    0
                ]  # Return language and country, but remove encoding if present

        return None

    def fmt_system_prompt(self, prompt):
        lazy_prompt = self.gpt_prompts.lazy_prompt if self.main_model.lazy else ""

        platform_text = f"- Platform: {platform.platform()}\n"
        if os.name == "nt":
            var = "COMSPEC"
        else:
            var = "SHELL"

        val = os.getenv(var)
        platform_text += f"- Shell: {var}={val}\n"

        user_lang = self.get_user_language()
        if user_lang:
            platform_text += f"- Language: {user_lang}\n"

        if self.cache_prompts:
            dt = datetime.now().astimezone().strftime("%Y-%m-%d")
            platform_text += f"- Current date: {dt}"
        else:
            dt = datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")
            platform_text += f"- Current date/time: {dt}"

        prompt = prompt.format(
            fence=self.fence,
            lazy_prompt=lazy_prompt,
            platform=platform_text,
        )
        return prompt

    def format_chat_chunks(self):
        self.choose_fence()
        main_sys = self.fmt_system_prompt(self.gpt_prompts.main_system)

        example_messages = []
        if self.main_model.examples_as_sys_msg:
            if self.gpt_prompts.example_messages:
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

        if self.gpt_prompts.system_reminder:
            main_sys += "\n" + self.fmt_system_prompt(self.gpt_prompts.system_reminder)

        chunks = ChatChunks()

        chunks.system = [
            dict(role="system", content=main_sys),
        ]
        chunks.examples = example_messages

        self.summarize_end()
        chunks.done = self.done_messages

        chunks.repo = self.get_repo_messages()
        chunks.readonly_files = self.get_readonly_files_messages()
        chunks.chat_files = self.get_chat_files_messages()

        if self.gpt_prompts.system_reminder:
            reminder_message = [
                dict(
                    role="system", content=self.fmt_system_prompt(self.gpt_prompts.system_reminder)
                ),
            ]
        else:
            reminder_message = []

        chunks.cur = list(self.cur_messages)
        chunks.reminder = []

        # TODO review impact of token count on image messages
        messages_tokens = self.main_model.token_count(chunks.all_messages())
        reminder_tokens = self.main_model.token_count(reminder_message)
        cur_tokens = self.main_model.token_count(chunks.cur)

        if None not in (messages_tokens, reminder_tokens, cur_tokens):
            total_tokens = messages_tokens + reminder_tokens + cur_tokens
        else:
            # add the reminder anyway
            total_tokens = 0

        final = chunks.cur[-1]

        max_input_tokens = self.main_model.info.get("max_input_tokens") or 0
        # Add the reminder prompt if we still have room to include it.
        if (
            max_input_tokens is None
            or total_tokens < max_input_tokens
            and self.gpt_prompts.system_reminder
        ):
            if self.main_model.reminder_as_sys_msg:
                chunks.reminder = reminder_message
            elif final["role"] == "user":
                # stuff it into the user message
                new_content = (
                    final["content"]
                    + "\n\n"
                    + self.fmt_system_prompt(self.gpt_prompts.system_reminder)
                )
                chunks.cur[-1] = dict(role=final["role"], content=new_content)

        return chunks

    def format_messages(self):
        chunks = self.format_chat_chunks()
        if self.cache_prompts and self.main_model.cache_control:
            chunks.add_cache_control_headers()

        msgs = chunks.all_messages()
        return msgs

    def send_message(self, inp):
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

        retry_delay = 0.125

        self.usage_report = None
        exhausted = False
        interrupted = False
        try:
            while True:
                try:
                    yield from self.send(messages, functions=self.functions)
                    break
                except retry_exceptions() as err:
                    self.io.tool_error(str(err))
                    retry_delay *= 2
                    if retry_delay > 60:
                        break
                    self.io.tool_output(f"Retrying in {retry_delay:.1f} seconds...")
                    time.sleep(retry_delay)
                    continue
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
                    # We hit the output limit!
                    if not self.main_model.info.get("supports_assistant_prefill"):
                        exhausted = True
                        break

                    self.multi_response_content = self.get_multi_response_content()

                    if messages[-1]["role"] == "assistant":
                        messages[-1]["content"] = self.multi_response_content
                    else:
                        messages.append(
                            dict(role="assistant", content=self.multi_response_content, prefix=True)
                        )
                except Exception as err:
                    self.io.tool_error(f"Unexpected error: {err}")
                    lines = traceback.format_exception(type(err), err, err.__traceback__)
                    self.io.tool_error("".join(lines))
                    return
        finally:
            if self.mdstream:
                self.live_incremental_response(True)
                self.mdstream = None

            self.partial_response_content = self.get_multi_response_content(True)
            self.multi_response_content = ""

        self.io.tool_output()

        self.show_usage_report()

        if exhausted:
            self.show_exhausted_error()
            self.num_exhausted_context_windows += 1
            return

        if self.partial_response_function_call:
            args = self.parse_partial_args()
            if args:
                content = args.get("explanation") or ""
            else:
                content = ""
        elif self.partial_response_content:
            content = self.partial_response_content
        else:
            content = ""

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
        max_output_tokens = self.main_model.info.get("max_output_tokens") or 0

        input_tokens = self.main_model.token_count(self.format_messages())
        max_input_tokens = self.main_model.info.get("max_input_tokens") or 0

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

        # Commit any formatting changes that happened
        if self.repo and self.auto_commits and not self.dry_run:
            commit_res = self.repo.commit(
                fnames=fnames, context="The linter made edits to these files", aider_edits=True
            )
            if commit_res:
                self.show_auto_commit_outcome(commit_res)

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
            normalized_rel_fname = rel_fname.replace("\\", "/")
            normalized_words = set(word.replace("\\", "/") for word in words)
            if normalized_rel_fname in normalized_words:
                mentioned_rel_fnames.add(rel_fname)

            fname = os.path.basename(rel_fname)

            # Don't add basenames that could be plain words like "run" or "make"
            if "/" in fname or "\\" in fname or "." in fname or "_" in fname or "-" in fname:
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
            model = self.main_model

        self.partial_response_content = ""
        self.partial_response_function_call = dict()

        self.io.log_llm_history("TO LLM", format_messages(messages))

        completion = None
        try:
            hash_object, completion = send_completion(
                model.name,
                messages,
                functions,
                self.stream,
                self.temperature,
                extra_headers=model.extra_headers,
                max_tokens=model.max_tokens,
            )
            self.chat_completion_call_hashes.append(hash_object.hexdigest())

            if self.stream:
                yield from self.show_send_output_stream(completion)
            else:
                self.show_send_output(completion)
        except KeyboardInterrupt as kbi:
            self.keyboard_interrupt()
            raise kbi
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

            self.calculate_and_show_tokens_and_cost(messages, completion)

    def show_send_output(self, completion):
        if self.verbose:
            print(completion)

        if not completion.choices:
            self.io.tool_error(str(completion))
            return

        show_func_err = None
        show_content_err = None
        try:
            if completion.choices[0].message.tool_calls:
                self.partial_response_function_call = (
                    completion.choices[0].message.tool_calls[0].function
                )
        except AttributeError as func_err:
            show_func_err = func_err

        try:
            self.partial_response_content = completion.choices[0].message.content or ""
        except AttributeError as content_err:
            show_content_err = content_err

        resp_hash = dict(
            function_call=str(self.partial_response_function_call),
            content=self.partial_response_content,
        )
        resp_hash = hashlib.sha1(json.dumps(resp_hash, sort_keys=True).encode())
        self.chat_completion_response_hashes.append(resp_hash.hexdigest())

        if show_func_err and show_content_err:
            self.io.tool_error(show_func_err)
            self.io.tool_error(show_content_err)
            raise Exception("No data found in LLM response!")

        show_resp = self.render_incremental_response(True)
        if self.show_pretty():
            show_resp = Markdown(
                show_resp, style=self.assistant_output_color, code_theme=self.code_theme
            )
        else:
            show_resp = Text(show_resp or "<no response>")

        self.io.console.print(show_resp)

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
                try:
                    sys.stdout.write(text)
                except UnicodeEncodeError:
                    # Safely encode and decode the text
                    safe_text = text.encode(sys.stdout.encoding, errors="backslashreplace").decode(
                        sys.stdout.encoding
                    )
                    sys.stdout.write(safe_text)
                sys.stdout.flush()
                yield text

    def live_incremental_response(self, final):
        show_resp = self.render_incremental_response(final)
        self.mdstream.update(show_resp, final=final)

    def render_incremental_response(self, final):
        return self.get_multi_response_content()

    def calculate_and_show_tokens_and_cost(self, messages, completion=None):
        prompt_tokens = 0
        completion_tokens = 0
        cached_tokens = 0
        cost = 0

        if completion and hasattr(completion, "usage") and completion.usage is not None:
            prompt_tokens = completion.usage.prompt_tokens
            completion_tokens = completion.usage.completion_tokens
            cached_tokens = getattr(completion.usage, "prompt_cache_hit_tokens", 0) or getattr(
                completion.usage, "cache_read_input_tokens", 0
            )
        else:
            prompt_tokens = self.main_model.token_count(messages)
            completion_tokens = self.main_model.token_count(self.partial_response_content)

        self.message_tokens_sent += prompt_tokens
        self.message_tokens_received += completion_tokens

        if cached_tokens:
            tokens_report = (
                f"Tokens: {self.message_tokens_sent:,} sent, {cached_tokens:,} cached, "
                f"{self.message_tokens_received:,} received."
            )
        else:
            tokens_report = (
                f"Tokens: {self.message_tokens_sent:,} sent,"
                f" {self.message_tokens_received:,} received."
            )

        if self.main_model.info.get("input_cost_per_token"):
            cost += prompt_tokens * self.main_model.info.get("input_cost_per_token")
            if self.main_model.info.get("output_cost_per_token"):
                cost += completion_tokens * self.main_model.info.get("output_cost_per_token")
            self.total_cost += cost
            self.message_cost += cost

            def format_cost(value):
                if value == 0:
                    return "0.00"
                magnitude = abs(value)
                if magnitude >= 0.01:
                    return f"{value:.2f}"
                else:
                    return f"{value:.{max(2, 2 - int(math.log10(magnitude)))}f}"

            cost_report = (
                f" Cost: ${format_cost(self.message_cost)} message,"
                f" ${format_cost(self.total_cost)} session."
            )
            self.usage_report = tokens_report + cost_report
        else:
            self.usage_report = tokens_report

    def show_usage_report(self):
        if self.usage_report:
            self.io.tool_output(self.usage_report)
            self.message_cost = 0.0
            self.message_tokens_sent = 0
            self.message_tokens_received = 0

    def get_multi_response_content(self, final=False):
        cur = self.multi_response_content or ""
        new = self.partial_response_content or ""

        if new.rstrip() != new and not final:
            new = new.rstrip()
        return cur + new

    def get_rel_fname(self, fname):
        return os.path.relpath(fname, self.root)

    def get_inchat_relative_files(self):
        files = [self.get_rel_fname(fname) for fname in self.abs_fnames]
        return sorted(set(files))

    def is_file_safe(self, fname):
        try:
            return Path(self.abs_root_path(fname)).is_file()
        except OSError:
            return

    def get_all_relative_files(self):
        if self.repo:
            files = self.repo.get_tracked_files()
        else:
            files = self.get_inchat_relative_files()

        # This is quite slow in large repos
        # files = [fname for fname in files if self.is_file_safe(fname)]

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
        all_files = set(self.get_all_relative_files())
        inchat_files = set(self.get_inchat_relative_files())
        read_only_files = set(self.get_rel_fname(fname) for fname in self.abs_read_only_fnames)
        return all_files - inchat_files - read_only_files

    def check_for_dirty_commit(self, path):
        if not self.repo:
            return
        if not self.dirty_commits:
            return
        if not self.repo.is_dirty(path):
            return

        # We need a committed copy of the file in order to /undo, so skip this
        # fullp = Path(self.abs_root_path(path))
        # if not fullp.stat().st_size:
        #     return

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
            if is_image_file(fname):
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
            self.show_auto_commit_outcome(res)
            commit_hash, commit_message = res
            return self.gpt_prompts.files_content_gpt_edits.format(
                hash=commit_hash,
                message=commit_message,
            )

        self.io.tool_output("No changes made to git tracked files.")
        return self.gpt_prompts.files_content_gpt_no_edits

    def show_auto_commit_outcome(self, res):
        commit_hash, commit_message = res
        self.last_aider_commit_hash = commit_hash
        self.aider_commit_hashes.add(commit_hash)
        self.last_aider_commit_message = commit_message
        if self.show_diffs:
            self.commands.cmd_diff()

    def show_undo_hint(self):
        if not self.commit_before_message:
            return
        if self.commit_before_message[-1] != self.repo.get_head():
            self.io.tool_output("You can use /undo to undo and discard each aider commit.")

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

    def get_edits(self, mode="update"):
        return []

    def apply_edits(self, edits):
        return
