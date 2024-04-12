#!/usr/bin/env python

import hashlib
import json
import os
import sys
import threading
import time
import traceback
from json.decoder import JSONDecodeError
from pathlib import Path

import git
import openai
from jsonschema import Draft7Validator
from rich.console import Console, Text
from rich.markdown import Markdown

from aider import models, prompts, utils
from aider.commands import Commands
from aider.history import ChatSummary
from aider.io import InputOutput
from aider.mdstream import MarkdownStream
from aider.repo import GitRepo
from aider.repomap import RepoMap
from aider.sendchat import send_with_retries
from aider.utils import is_image_file

from ..dump import dump  # noqa: F401


class MissingAPIKeyError(ValueError):
    pass


class ExhaustedContextWindow(Exception):
    pass


def wrap_fence(name):
    return f"<{name}>", f"</{name}>"


class Coder:
    client = None
    abs_fnames = None
    repo = None
    last_aider_commit_hash = None
    last_asked_for_commit_time = 0
    repo_map = None
    functions = None
    total_cost = 0.0
    num_exhausted_context_windows = 0
    num_malformed_responses = 0
    last_keyboard_interrupt = None
    max_apply_update_errors = 3
    edit_format = None

    @classmethod
    def create(
        self,
        main_model=None,
        edit_format=None,
        io=None,
        client=None,
        skip_model_availabily_check=False,
        **kwargs,
    ):
        from . import EditBlockCoder, UnifiedDiffCoder, WholeFileCoder

        if not main_model:
            main_model = models.Model.create(models.DEFAULT_MODEL_NAME)

        if not skip_model_availabily_check and not main_model.always_available:
            if not check_model_availability(io, client, main_model):
                fallback_model = models.Model.create("gpt-3.5-turbo-0125")
                io.tool_error(
                    f"API key does not support {main_model.name}, falling back to"
                    f" {fallback_model.name}"
                )
                main_model = fallback_model

        if edit_format is None:
            edit_format = main_model.edit_format

        if edit_format == "diff":
            return EditBlockCoder(client, main_model, io, **kwargs)
        elif edit_format == "whole":
            return WholeFileCoder(client, main_model, io, **kwargs)
        elif edit_format == "udiff":
            return UnifiedDiffCoder(client, main_model, io, **kwargs)
        else:
            raise ValueError(f"Unknown edit format {edit_format}")

    def __init__(
        self,
        client,
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
    ):
        self.client = client

        if not fnames:
            fnames = []

        if io is None:
            io = InputOutput()

        self.chat_completion_call_hashes = []
        self.chat_completion_response_hashes = []
        self.need_commit_before_edits = set()

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

        self.io.tool_output(f"Model: {main_model.name} using {self.edit_format} edit format")

        self.show_diffs = show_diffs

        self.commands = Commands(self.io, self, voice_language)

        if use_git:
            try:
                self.repo = GitRepo(
                    self.io, fnames, git_dname, main_model, aider_ignore_file, client=self.client
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

        if self.repo:
            rel_repo_dir = self.repo.get_rel_repo_dir()
            num_files = len(self.repo.get_tracked_files())
            self.io.tool_output(f"Git repo: {rel_repo_dir} with {num_files:,} files")
            if num_files > 1000:
                self.io.tool_error(
                    "Warning: For large repos, consider using an .aiderignore file to ignore"
                    " irrelevant files/dirs."
                )
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

        if map_tokens > 0:
            self.io.tool_output(f"Repo-map: using {map_tokens} tokens")
            max_map_tokens = 2048
            if map_tokens > max_map_tokens:
                self.io.tool_error(
                    f"Warning: map-tokens > {max_map_tokens} is not recommended as too much"
                    " irrelevant code can confuse GPT."
                )
        else:
            self.io.tool_output("Repo-map: disabled because map_tokens == 0")

        for fname in self.get_inchat_relative_files():
            self.io.tool_output(f"Added {fname} to the chat.")

        self.summarizer = ChatSummary(
            self.client,
            self.main_model.get_weak_model(),
            self.main_model.max_chat_history_tokens,
        )

        self.summarizer_thread = None
        self.summarized_done_messages = []

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

    def add_rel_fname(self, rel_fname):
        self.abs_fnames.add(self.abs_root_path(rel_fname))
        self.check_added_files()

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

    def get_repo_map(self):
        if not self.repo_map:
            return

        other_files = set(self.get_all_abs_files()) - set(self.abs_fnames)
        repo_content = self.repo_map.get_repo_map(self.abs_fnames, other_files)
        return repo_content

    def get_files_messages(self):
        all_content = ""

        repo_content = self.get_repo_map()
        if repo_content:
            if all_content:
                all_content += "\n"
            all_content += repo_content

        if self.abs_fnames:
            files_content = self.gpt_prompts.files_content_prefix
            files_content += self.get_files_content()
        else:
            files_content = self.gpt_prompts.files_no_full_files

        all_content += files_content

        files_messages = [
            dict(role="user", content=all_content),
            dict(role="assistant", content="Ok."),
        ]

        images_message = self.get_images_message()
        if images_message is not None:
            files_messages += [
                images_message,
                dict(role="assistant", content="Ok."),
            ]

        return files_messages

    def get_images_message(self):
        if not utils.is_gpt4_with_openai_base_url(self.main_model.name, self.client):
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
                    return self.partial_response_content

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

        return self.send_new_user_message(inp)

    def fmt_system_prompt(self, prompt):
        prompt = prompt.format(fence=self.fence)
        return prompt

    def format_messages(self):
        self.choose_fence()
        main_sys = self.fmt_system_prompt(self.gpt_prompts.main_system)
        main_sys += "\n" + self.fmt_system_prompt(self.gpt_prompts.system_reminder)

        messages = [
            dict(role="system", content=main_sys),
        ]

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

        # Add the reminder prompt if we still have room to include it.
        if total_tokens < self.main_model.max_context_tokens:
            messages += reminder_message

        return messages

    def send_new_user_message(self, inp):
        self.cur_messages += [
            dict(role="user", content=inp),
        ]

        messages = self.format_messages()

        if self.verbose:
            utils.show_messages(messages, functions=self.functions)

        exhausted = False
        interrupted = False
        try:
            interrupted = self.send(messages, functions=self.functions)
        except ExhaustedContextWindow:
            exhausted = True
        except openai.BadRequestError as err:
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
                saved_message = self.auto_commit(edited)
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

    def send(self, messages, model=None, functions=None):
        if not model:
            model = self.main_model.name

        self.partial_response_content = ""
        self.partial_response_function_call = dict()

        interrupted = False
        try:
            hash_object, completion = send_with_retries(
                self.client, model, messages, functions, self.stream
            )
            self.chat_completion_call_hashes.append(hash_object.hexdigest())

            if self.stream:
                self.show_send_output_stream(completion)
            else:
                self.show_send_output(completion)
        except KeyboardInterrupt:
            self.keyboard_interrupt()
            interrupted = True

        if self.partial_response_content:
            self.io.ai_output(self.partial_response_content)
        elif self.partial_response_function_call:
            # TODO: push this into subclasses
            args = self.parse_partial_args()
            if args:
                self.io.ai_output(json.dumps(args, indent=4))

        return interrupted

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
            raise Exception("No data found in openai response!")

        tokens = None
        if hasattr(completion, "usage") and completion.usage is not None:
            prompt_tokens = completion.usage.prompt_tokens
            completion_tokens = completion.usage.completion_tokens

            tokens = f"{prompt_tokens} prompt tokens, {completion_tokens} completion tokens"
            if self.main_model.prompt_price:
                cost = prompt_tokens * self.main_model.prompt_price / 1000
                if self.main_model.completion_price:
                    cost += completion_tokens * self.main_model.completion_price / 1000
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

    def show_send_output_stream(self, completion):
        if self.show_pretty():
            mdargs = dict(style=self.assistant_output_color, code_theme=self.code_theme)
            mdstream = MarkdownStream(mdargs=mdargs)
        else:
            mdstream = None

        try:
            for chunk in completion:
                if len(chunk.choices) == 0:
                    continue

                if (
                    hasattr(chunk.choices[0], "finish_reason")
                    and chunk.choices[0].finish_reason == "length"
                ):
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
                    text = None

                if self.show_pretty():
                    self.live_incremental_response(mdstream, False)
                elif text:
                    sys.stdout.write(text)
                    sys.stdout.flush()
        finally:
            if mdstream:
                self.live_incremental_response(mdstream, True)

    def live_incremental_response(self, mdstream, final):
        show_resp = self.render_incremental_response(final)
        if not show_resp:
            return

        mdstream.update(show_resp, final=final)

    def render_incremental_response(self, final):
        return self.partial_response_content

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
        self.io.tool_error(
            "https://aider.chat/docs/faq.html#how-can-i-add-all-the-files-to-the-chat"
        )
        self.warning_given = True

    apply_update_errors = 0

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
            self.apply_update_errors += 1
            if self.apply_update_errors < self.max_apply_update_errors:
                self.io.tool_error(f"Malformed response #{self.apply_update_errors}, retrying...")
                self.io.tool_error("https://aider.chat/docs/faq.html#aider-isnt-editing-my-files")
                self.io.tool_error(str(err))
                return None, err
            else:
                self.io.tool_error(f"Malformed response #{self.apply_update_errors}, aborting.")
                self.io.tool_error("https://aider.chat/docs/faq.html#aider-isnt-editing-my-files")
                self.io.tool_error(str(err))
                return False, None

        except git.exc.GitCommandError as err:
            self.io.tool_error(str(err))
            return False, None
        except Exception as err:
            print(err)
            print()
            traceback.print_exc()
            self.apply_update_errors += 1
            if self.apply_update_errors < self.max_apply_update_errors:
                self.io.tool_error(f"Update exception #{self.apply_update_errors}, retrying...")
                self.io.tool_error(str(err))
                return None, str(err)
            else:
                self.io.tool_error(f"Update exception #{self.apply_update_errors}, aborting")
                self.io.tool_error(str(err))
                return False, None

        self.apply_update_errors = 0

        for path in edited:
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

    # commits...

    def get_context_from_history(self, history):
        context = ""
        if history:
            for msg in history:
                context += "\n" + msg["role"].upper() + ": " + msg["content"] + "\n"

        return context

    def auto_commit(self, edited):
        context = self.get_context_from_history(self.cur_messages)
        res = self.repo.commit(fnames=edited, context=context, prefix="aider: ")
        if res:
            commit_hash, commit_message = res
            self.last_aider_commit_hash = commit_hash

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


def check_model_availability(io, client, main_model):
    if not hasattr(client, "models"):
        return True

    try:
        available_models = client.models.list()
    except openai.NotFoundError:
        # Azure sometimes returns 404?
        # https://discord.com/channels/1131200896827654144/1182327371232186459
        io.tool_error(f"Unable to list available models, proceeding with {main_model.name}")
        return True

    model_ids = sorted(model.id for model in available_models)
    if main_model.name in model_ids:
        return True

    available_models = ", ".join(model_ids)
    io.tool_error(f"API key supports: {available_models}")
    return False
