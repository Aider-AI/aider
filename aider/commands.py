import json
import re
import subprocess
import sys
from pathlib import Path

import git
from prompt_toolkit.completion import Completion

from aider import prompts, voice

from .dump import dump  # noqa: F401


class Commands:
    voice = None

    def __init__(self, io, coder, voice_language=None):
        self.io = io
        self.coder = coder

        if voice_language == "auto":
            voice_language = None

        self.voice_language = voice_language
        self.tokenizer = coder.main_model.tokenizer

    def is_command(self, inp):
        if inp[0] == "/":
            return True

    def get_commands(self):
        commands = []
        for attr in dir(self):
            if attr.startswith("cmd_"):
                commands.append("/" + attr[4:])

        return commands

    def get_command_completions(self, cmd_name, partial):
        cmd_completions_method_name = f"completions_{cmd_name}"
        cmd_completions_method = getattr(self, cmd_completions_method_name, None)
        if cmd_completions_method:
            for completion in cmd_completions_method(partial):
                yield completion

    def do_run(self, cmd_name, args):
        cmd_method_name = f"cmd_{cmd_name}"
        cmd_method = getattr(self, cmd_method_name, None)
        if cmd_method:
            return cmd_method(args)
        else:
            self.io.tool_output(f"Error: Command {cmd_name} not found.")

    def matching_commands(self, inp):
        words = inp.strip().split()
        if not words:
            return

        first_word = words[0]
        rest_inp = inp[len(words[0]) :]

        all_commands = self.get_commands()
        matching_commands = [cmd for cmd in all_commands if cmd.startswith(first_word)]
        return matching_commands, first_word, rest_inp

    def run(self, inp):
        res = self.matching_commands(inp)
        if res is None:
            return
        matching_commands, first_word, rest_inp = res
        if len(matching_commands) == 1:
            return self.do_run(matching_commands[0][1:], rest_inp)
        elif len(matching_commands) > 1:
            self.io.tool_error(f"Ambiguous command: {', '.join(matching_commands)}")
        else:
            self.io.tool_error(f"Invalid command: {first_word}")

    # any method called cmd_xxx becomes a command automatically.
    # each one must take an args param.

    def cmd_commit(self, args):
        "Commit edits to the repo made outside the chat (commit message optional)"

        if not self.coder.repo:
            self.io.tool_error("No git repository found.")
            return

        if not self.coder.repo.is_dirty():
            self.io.tool_error("No more changes to commit.")
            return

        commit_message = args.strip()
        self.coder.repo.commit(message=commit_message)

    def cmd_clear(self, args):
        "Clear the chat history"

        self.coder.done_messages = []
        self.coder.cur_messages = []

    def cmd_tokens(self, args):
        "Report on the number of tokens used by the current chat context"

        res = []

        # system messages
        msgs = [
            dict(role="system", content=self.coder.gpt_prompts.main_system),
            dict(role="system", content=self.coder.gpt_prompts.system_reminder),
        ]
        tokens = len(self.tokenizer.encode(json.dumps(msgs)))
        res.append((tokens, "system messages", ""))

        # chat history
        msgs = self.coder.done_messages + self.coder.cur_messages
        if msgs:
            msgs = [dict(role="dummy", content=msg) for msg in msgs]
            msgs = json.dumps(msgs)
            tokens = len(self.tokenizer.encode(msgs))
            res.append((tokens, "chat history", "use /clear to clear"))

        # repo map
        other_files = set(self.coder.get_all_abs_files()) - set(self.coder.abs_fnames)
        if self.coder.repo_map:
            repo_content = self.coder.repo_map.get_repo_map(self.coder.abs_fnames, other_files)
            if repo_content:
                tokens = len(self.tokenizer.encode(repo_content))
                res.append((tokens, "repository map", "use --map-tokens to resize"))

        # files
        for fname in self.coder.abs_fnames:
            relative_fname = self.coder.get_rel_fname(fname)
            content = self.io.read_text(fname)
            # approximate
            content = f"{relative_fname}\n```\n" + content + "```\n"
            tokens = len(self.tokenizer.encode(content))
            res.append((tokens, f"{relative_fname}", "use /drop to drop from chat"))

        self.io.tool_output("Approximate context window usage, in tokens:")
        self.io.tool_output()

        width = 8
        cost_width = 7

        def fmt(v):
            return format(int(v), ",").rjust(width)

        col_width = max(len(row[1]) for row in res)

        cost_pad = " " * cost_width
        total = 0
        total_cost = 0.0
        for tk, msg, tip in res:
            total += tk
            cost = tk * (self.coder.main_model.prompt_price / 1000)
            total_cost += cost
            msg = msg.ljust(col_width)
            self.io.tool_output(f"${cost:5.2f} {fmt(tk)} {msg} {tip}")

        self.io.tool_output("=" * (width + cost_width + 1))
        self.io.tool_output(f"${total_cost:5.2f} {fmt(total)} tokens total")

        limit = self.coder.main_model.max_context_tokens
        remaining = limit - total
        if remaining > 1024:
            self.io.tool_output(f"{cost_pad}{fmt(remaining)} tokens remaining in context window")
        elif remaining > 0:
            self.io.tool_error(
                f"{cost_pad}{fmt(remaining)} tokens remaining in context window (use /drop or"
                " /clear to make space)"
            )
        else:
            self.io.tool_error(f"{cost_pad}{fmt(remaining)} tokens remaining, window exhausted!")
        self.io.tool_output(f"{cost_pad}{fmt(limit)} tokens max context window size")

    def cmd_undo(self, args):
        "Undo the last git commit if it was done by aider"
        if not self.coder.repo:
            self.io.tool_error("No git repository found.")
            return

        if self.coder.repo.is_dirty():
            self.io.tool_error(
                "The repository has uncommitted changes. Please commit or stash them before"
                " undoing."
            )
            return

        local_head = self.coder.repo.repo.git.rev_parse("HEAD")
        current_branch = self.coder.repo.repo.active_branch.name
        try:
            remote_head = self.coder.repo.repo.git.rev_parse(f"origin/{current_branch}")
            has_origin = True
        except git.exc.GitCommandError:
            has_origin = False

        if has_origin:
            if local_head == remote_head:
                self.io.tool_error(
                    "The last commit has already been pushed to the origin. Undoing is not"
                    " possible."
                )
                return

        last_commit = self.coder.repo.repo.head.commit
        if (
            not last_commit.message.startswith("aider:")
            or last_commit.hexsha[:7] != self.coder.last_aider_commit_hash
        ):
            self.io.tool_error("The last commit was not made by aider in this chat session.")
            self.io.tool_error(
                "You could try `/git reset --hard HEAD^` but be aware that this is a destructive"
                " command!"
            )
            return
        self.coder.repo.repo.git.reset("--hard", "HEAD~1")
        self.io.tool_output(
            f"{last_commit.message.strip()}\n"
            f"The above commit {self.coder.last_aider_commit_hash} "
            "was reset and removed from git.\n"
        )

        if self.coder.main_model.send_undo_reply:
            return prompts.undo_command_reply

    def cmd_diff(self, args):
        "Display the diff of the last aider commit"
        if not self.coder.repo:
            self.io.tool_error("No git repository found.")
            return

        if not self.coder.last_aider_commit_hash:
            self.io.tool_error("No previous aider commit found.")
            self.io.tool_error("You could try `/git diff` or `/git diff HEAD^`.")
            return

        commits = f"{self.coder.last_aider_commit_hash}~1"
        diff = self.coder.repo.diff_commits(
            self.coder.pretty,
            commits,
            self.coder.last_aider_commit_hash,
        )

        # don't use io.tool_output() because we don't want to log or further colorize
        print(diff)

    def completions_add(self, partial):
        files = set(self.coder.get_all_relative_files())
        files = files - set(self.coder.get_inchat_relative_files())
        for fname in files:
            if partial.lower() in fname.lower():
                yield Completion(fname, start_position=-len(partial))

    def glob_filtered_to_repo(self, pattern):
        try:
            raw_matched_files = list(Path(self.coder.root).glob(pattern))
        except ValueError as err:
            self.io.tool_error(f"Error matching {pattern}: {err}")
            raw_matched_files = []

        matched_files = []
        for fn in raw_matched_files:
            matched_files += expand_subdir(fn)

        matched_files = [str(Path(fn).relative_to(self.coder.root)) for fn in matched_files]

        # if repo, filter against it
        if self.coder.repo:
            git_files = self.coder.repo.get_tracked_files()
            matched_files = [fn for fn in matched_files if str(fn) in git_files]

        res = list(map(str, matched_files))
        return res

    def cmd_add(self, args):
        "Add files to the chat so GPT can edit them or review them in detail"

        added_fnames = []
        git_added = []
        git_files = self.coder.repo.get_tracked_files() if self.coder.repo else []

        all_matched_files = set()

        filenames = parse_quoted_filenames(args)
        for word in filenames:
            if Path(word).is_absolute():
                fname = Path(word)
            else:
                fname = Path(self.coder.root) / word

            if fname.exists() and fname.is_file():
                all_matched_files.add(str(fname))
                continue
                # an existing dir will fall through and get recursed by glob

            matched_files = self.glob_filtered_to_repo(word)
            if matched_files:
                all_matched_files.update(matched_files)
                continue

            if self.io.confirm_ask(f"No files matched '{word}'. Do you want to create {fname}?"):
                fname.touch()
                all_matched_files.add(str(fname))

        for matched_file in all_matched_files:
            abs_file_path = self.coder.abs_root_path(matched_file)
            rel_path = self.coder.get_rel_fname(matched_file)

            if not abs_file_path.startswith(self.coder.root):
                self.io.tool_error(
                    f"Can not add {abs_file_path}, which is not within {self.coder.root}"
                )
                continue

            if self.coder.repo and rel_path not in git_files:
                try:
                    self.coder.repo.repo.git.add(abs_file_path)
                    git_added.append(matched_file)
                except git.exc.GitCommandError as e:
                    self.io.tool_error(f"Unable to add {matched_file}: {str(e)}")
                    continue

            if abs_file_path in self.coder.abs_fnames:
                self.io.tool_error(f"{matched_file} is already in the chat")
            else:
                content = self.io.read_text(abs_file_path)
                if content is None:
                    self.io.tool_error(f"Unable to read {matched_file}")
                else:
                    self.coder.abs_fnames.add(abs_file_path)
                    self.io.tool_output(f"Added {matched_file} to the chat")
                    added_fnames.append(matched_file)

        if self.coder.repo and git_added and self.coder.auto_commits:
            git_added = " ".join(git_added)
            commit_message = f"aider: Added {git_added}"
            self.coder.repo.commit(message=commit_message)

        if not added_fnames:
            return

        # only reply if there's been some chatting since the last edit
        if not self.coder.cur_messages:
            return

        reply = prompts.added_files.format(fnames=", ".join(added_fnames))
        return reply

    def completions_drop(self, partial):
        files = self.coder.get_inchat_relative_files()

        for fname in files:
            if partial.lower() in fname.lower():
                yield Completion(fname, start_position=-len(partial))

    def cmd_drop(self, args):
        "Remove files from the chat session to free up context space"

        if not args.strip():
            self.io.tool_output("Dropping all files from the chat session.")
            self.coder.abs_fnames = set()

        filenames = parse_quoted_filenames(args)
        for word in filenames:
            matched_files = self.glob_filtered_to_repo(word)

            if not matched_files:
                self.io.tool_error(f"No files matched '{word}'")

            for matched_file in matched_files:
                abs_fname = self.coder.abs_root_path(matched_file)
                if abs_fname in self.coder.abs_fnames:
                    self.coder.abs_fnames.remove(abs_fname)
                    self.io.tool_output(f"Removed {matched_file} from the chat")

    def cmd_git(self, args):
        "Run a git command"
        combined_output = None
        try:
            args = "git " + args
            env = dict(GIT_EDITOR="true", **subprocess.os.environ)
            result = subprocess.run(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
                shell=True,
            )
            combined_output = result.stdout
        except Exception as e:
            self.io.tool_error(f"Error running git command: {e}")

        if combined_output is None:
            return

        self.io.tool_output(combined_output)

    def cmd_run(self, args):
        "Run a shell command and optionally add the output to the chat"
        combined_output = None
        try:
            result = subprocess.run(
                args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, shell=True
            )
            combined_output = result.stdout
        except Exception as e:
            self.io.tool_error(f"Error running command: {e}")

        if combined_output is None:
            return

        self.io.tool_output(combined_output)

        if self.io.confirm_ask("Add the output to the chat?", default="y"):
            for line in combined_output.splitlines():
                self.io.tool_output(line, log_only=True)

            msg = prompts.run_output.format(
                command=args,
                output=combined_output,
            )
            return msg

    def cmd_exit(self, args):
        "Exit the application"
        sys.exit()

    def cmd_ls(self, args):
        "List all known files and indicate which are included in the chat session"

        files = self.coder.get_all_relative_files()

        other_files = []
        chat_files = []
        for file in files:
            abs_file_path = self.coder.abs_root_path(file)
            if abs_file_path in self.coder.abs_fnames:
                chat_files.append(file)
            else:
                other_files.append(file)

        if not chat_files and not other_files:
            self.io.tool_output("\nNo files in chat or git repo.")
            return

        if chat_files:
            self.io.tool_output("Files in chat:\n")
        for file in chat_files:
            self.io.tool_output(f"  {file}")

        if other_files:
            self.io.tool_output("\nRepo files not in the chat:\n")
        for file in other_files:
            self.io.tool_output(f"  {file}")

    def cmd_help(self, args):
        "Show help about all commands"
        commands = sorted(self.get_commands())
        for cmd in commands:
            cmd_method_name = f"cmd_{cmd[1:]}"
            cmd_method = getattr(self, cmd_method_name, None)
            if cmd_method:
                description = cmd_method.__doc__
                self.io.tool_output(f"{cmd} {description}")
            else:
                self.io.tool_output(f"{cmd} No description available.")

    def cmd_voice(self, args):
        "Record and transcribe voice input"

        if not self.voice:
            try:
                self.voice = voice.Voice()
            except voice.SoundDeviceError:
                self.io.tool_error(
                    "Unable to import `sounddevice` and/or `soundfile`, is portaudio installed?"
                )
                return

        history_iter = self.io.get_input_history()

        history = []
        size = 0
        for line in history_iter:
            if line.startswith("/"):
                continue
            if line in history:
                continue
            if size + len(line) > 1024:
                break
            size += len(line)
            history.append(line)

        history.reverse()
        history = "\n".join(history)

        text = self.voice.record_and_transcribe(history, language=self.voice_language)
        if text:
            self.io.add_to_input_history(text)
            print()
            self.io.user_input(text, log_only=False)
            print()

        return text


def expand_subdir(file_path):
    file_path = Path(file_path)
    if file_path.is_file():
        yield file_path
        return

    if file_path.is_dir():
        for file in file_path.rglob("*"):
            if file.is_file():
                yield str(file)


def parse_quoted_filenames(args):
    filenames = re.findall(r"\"(.+?)\"|(\S+)", args)
    filenames = [name for sublist in filenames for name in sublist if name]
    return filenames
