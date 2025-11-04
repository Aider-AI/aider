import asyncio
import base64
import functools
import os
import shutil
import signal
import subprocess
import sys
import time
import webbrowser
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from io import StringIO
from pathlib import Path

from prompt_toolkit.completion import Completer, Completion, ThreadedCompleter
from prompt_toolkit.cursor_shapes import ModalCursorShapeConfig
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.filters import Condition, is_searching
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.vi_state import InputMode
from prompt_toolkit.keys import Keys
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.output.vt100 import is_dumb_terminal
from prompt_toolkit.shortcuts import CompleteStyle, PromptSession
from prompt_toolkit.styles import Style
from pygments.lexers import MarkdownLexer, guess_lexer_for_filename
from pygments.token import Token
from rich.color import ColorParseError
from rich.columns import Columns
from rich.console import Console
from rich.markdown import Markdown
from rich.spinner import SPINNERS
from rich.style import Style as RichStyle
from rich.text import Text

from .dump import dump  # noqa: F401
from .editor import pipe_editor
from .utils import is_image_file, run_fzf
from .waiting import Spinner

# Constants
NOTIFICATION_MESSAGE = "Aider is waiting for your input"


def ensure_hash_prefix(color):
    """Ensure hex color values have a # prefix."""
    if not color:
        return color
    if isinstance(color, str) and color.strip() and not color.startswith("#"):
        # Check if it's a valid hex color (3 or 6 hex digits)
        if all(c in "0123456789ABCDEFabcdef" for c in color) and len(color) in (3, 6):
            return f"#{color}"
    return color


def restore_multiline(func):
    """Decorator to restore multiline mode after function execution"""

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        orig_multiline = self.multiline_mode
        self.multiline_mode = False
        try:
            return func(self, *args, **kwargs)
        except Exception:
            raise
        finally:
            self.multiline_mode = orig_multiline

    return wrapper


def restore_multiline_async(func):
    """Decorator to restore multiline mode after async function execution"""

    @functools.wraps(func)
    async def wrapper(self, *args, **kwargs):
        orig_multiline = self.multiline_mode
        self.multiline_mode = False
        try:
            return await func(self, *args, **kwargs)
        except Exception:
            raise
        finally:
            self.multiline_mode = orig_multiline

    return wrapper


def without_input_history(func):
    """Decorator to temporarily disable history saving for the prompt session buffer."""

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        orig_buf_append = None
        try:
            orig_buf_append = self.prompt_session.default_buffer.append_to_history
            self.prompt_session.default_buffer.append_to_history = (
                lambda: None
            )  # Replace with no-op
        except AttributeError:
            pass

        try:
            return func(self, *args, **kwargs)
        except Exception:
            raise
        finally:
            if orig_buf_append:
                self.prompt_session.default_buffer.append_to_history = orig_buf_append

    return wrapper


class CommandCompletionException(Exception):
    """Raised when a command should use the normal autocompleter instead of
    command-specific completion."""

    pass


@dataclass
class ConfirmGroup:
    preference: str = None
    show_group: bool = True

    def __init__(self, items=None):
        if items is not None:
            self.show_group = len(items) > 1


class AutoCompleter(Completer):
    def __init__(
        self, root, rel_fnames, addable_rel_fnames, commands, encoding, abs_read_only_fnames=None
    ):
        self.addable_rel_fnames = addable_rel_fnames
        self.rel_fnames = rel_fnames
        self.encoding = encoding
        self.abs_read_only_fnames = abs_read_only_fnames or []

        fname_to_rel_fnames = defaultdict(list)
        for rel_fname in addable_rel_fnames:
            fname = os.path.basename(rel_fname)
            if fname != rel_fname:
                fname_to_rel_fnames[fname].append(rel_fname)
        self.fname_to_rel_fnames = fname_to_rel_fnames

        self.words = set()

        self.commands = commands
        self.command_completions = dict()
        if commands:
            self.command_names = self.commands.get_commands()

        for rel_fname in addable_rel_fnames:
            self.words.add(rel_fname)

        for rel_fname in rel_fnames:
            self.words.add(rel_fname)

        all_fnames = [Path(root) / rel_fname for rel_fname in rel_fnames]
        if abs_read_only_fnames:
            all_fnames.extend(abs_read_only_fnames)

        self.all_fnames = all_fnames
        self.tokenized = False

    def tokenize(self):
        if self.tokenized:
            return
        self.tokenized = True

        # Performance optimization for large file sets
        if len(self.all_fnames) > 100:
            # Skip tokenization for very large numbers of files to avoid input lag
            self.tokenized = True
            return

        # Limit number of files to process to avoid excessive tokenization time
        process_fnames = self.all_fnames
        if len(process_fnames) > 50:
            # Only process a subset of files to maintain responsiveness
            process_fnames = process_fnames[:50]

        for fname in process_fnames:
            try:
                with open(fname, "r", encoding=self.encoding) as f:
                    content = f.read()
            except (FileNotFoundError, UnicodeDecodeError, IsADirectoryError):
                continue
            try:
                lexer = guess_lexer_for_filename(fname, content)
            except Exception:  # On Windows, bad ref to time.clock which is deprecated
                continue

            tokens = list(lexer.get_tokens(content))
            self.words.update(
                (token[1], f"`{token[1]}`") for token in tokens if token[0] in Token.Name
            )

    def get_command_completions(self, document, complete_event, text, words):
        if len(words) == 1 and not text[-1].isspace():
            partial = words[0].lower()
            candidates = [cmd for cmd in self.command_names if cmd.startswith(partial)]
            for candidate in sorted(candidates):
                yield Completion(candidate, start_position=-len(words[-1]))
            return

        if len(words) <= 1 or text[-1].isspace():
            return

        cmd = words[0]
        partial = words[-1].lower()

        matches, _, _ = self.commands.matching_commands(cmd)
        if len(matches) == 1:
            cmd = matches[0]
        elif cmd not in matches:
            return

        raw_completer = self.commands.get_raw_completions(cmd)
        if raw_completer:
            yield from raw_completer(document, complete_event)
            return

        if cmd not in self.command_completions:
            candidates = self.commands.get_completions(cmd)
            self.command_completions[cmd] = candidates
        else:
            candidates = self.command_completions[cmd]

        if candidates is None:
            return

        candidates = [word for word in candidates if partial in word.lower()]
        for candidate in sorted(candidates):
            yield Completion(candidate, start_position=-len(words[-1]))

    def get_completions(self, document, complete_event):
        self.tokenize()

        text = document.text_before_cursor
        words = text.split()
        if not words:
            return

        if text and text[-1].isspace():
            # don't keep completing after a space
            return

        if text[0] == "/":
            try:
                yield from self.get_command_completions(document, complete_event, text, words)
                return
            except CommandCompletionException:
                # Fall through to normal completion
                pass

        candidates = self.words
        candidates.update(set(self.fname_to_rel_fnames))
        candidates = [word if type(word) is tuple else (word, word) for word in candidates]

        last_word = words[-1]

        # Only provide completions if the user has typed at least 3 characters
        if len(last_word) < 3:
            return

        completions = []
        for word_match, word_insert in candidates:
            if word_match.lower().startswith(last_word.lower()):
                completions.append((word_insert, -len(last_word), word_match))

                rel_fnames = self.fname_to_rel_fnames.get(word_match, [])
                if rel_fnames:
                    for rel_fname in rel_fnames:
                        completions.append((rel_fname, -len(last_word), rel_fname))

        for ins, pos, match in sorted(completions):
            yield Completion(ins, start_position=pos, display=match)


class InputOutput:
    num_error_outputs = 0
    num_user_asks = 0
    clipboard_watcher = None
    bell_on_next_input = False
    notifications_command = None
    encoding = "utf-8"

    def __init__(
        self,
        pretty=True,
        yes=None,
        input_history_file=None,
        chat_history_file=None,
        input=None,
        output=None,
        user_input_color="blue",
        tool_output_color=None,
        tool_error_color="red",
        tool_warning_color="#FFA500",
        assistant_output_color="blue",
        completion_menu_color=None,
        completion_menu_bg_color=None,
        completion_menu_current_color=None,
        completion_menu_current_bg_color=None,
        code_theme="default",
        encoding="utf-8",
        line_endings="platform",
        dry_run=False,
        llm_history_file=None,
        editingmode=EditingMode.EMACS,
        fancy_input=True,
        file_watcher=None,
        multiline_mode=False,
        root=".",
        notifications=False,
        notifications_command=None,
        verbose=False,
    ):
        self.console = Console()
        self.pretty = pretty
        if chat_history_file is not None:
            self.chat_history_file = Path(chat_history_file)
        else:
            self.chat_history_file = None

        self.placeholder = None
        self.fallback_spinner = None
        self.prompt_session = None
        self.interrupted = False
        self.never_prompts = set()
        self.editingmode = editingmode
        self.multiline_mode = multiline_mode
        self.bell_on_next_input = False
        self.notifications = notifications
        self.verbose = verbose

        if notifications and notifications_command is None:
            self.notifications_command = self.get_default_notification_command()
        else:
            self.notifications_command = notifications_command

        no_color = os.environ.get("NO_COLOR")
        if no_color is not None and no_color != "":
            pretty = False

        self.user_input_color = ensure_hash_prefix(user_input_color) if pretty else None
        self.tool_output_color = ensure_hash_prefix(tool_output_color) if pretty else None
        self.tool_error_color = ensure_hash_prefix(tool_error_color) if pretty else None
        self.tool_warning_color = ensure_hash_prefix(tool_warning_color) if pretty else None
        self.assistant_output_color = ensure_hash_prefix(assistant_output_color)
        self.completion_menu_color = ensure_hash_prefix(completion_menu_color) if pretty else None
        self.completion_menu_bg_color = (
            ensure_hash_prefix(completion_menu_bg_color) if pretty else None
        )
        self.completion_menu_current_color = (
            ensure_hash_prefix(completion_menu_current_color) if pretty else None
        )
        self.completion_menu_current_bg_color = (
            ensure_hash_prefix(completion_menu_current_bg_color) if pretty else None
        )

        self.fzf_available = shutil.which("fzf")
        if not self.fzf_available and self.verbose:
            self.tool_warning(
                "fzf not found, fuzzy finder features will be disabled. Install it for enhanced"
                " file/history search."
            )

        self.code_theme = code_theme

        self._stream_buffer = ""
        self._stream_line_count = 0

        self.input = input
        self.output = output

        self.pretty = pretty
        if self.output:
            self.pretty = False

        self.yes = yes

        self.input_history_file = input_history_file
        if self.input_history_file:
            try:
                Path(self.input_history_file).parent.mkdir(parents=True, exist_ok=True)
            except (PermissionError, OSError) as e:
                self.tool_warning(f"Could not create directory for input history: {e}")
                self.input_history_file = None
        self.llm_history_file = llm_history_file
        if chat_history_file is not None:
            self.chat_history_file = Path(chat_history_file)
        else:
            self.chat_history_file = None

        self.encoding = encoding
        valid_line_endings = {"platform", "lf", "crlf"}
        if line_endings not in valid_line_endings:
            raise ValueError(
                f"Invalid line_endings value: {line_endings}. "
                f"Must be one of: {', '.join(valid_line_endings)}"
            )
        self.newline = (
            None if line_endings == "platform" else "\n" if line_endings == "lf" else "\r\n"
        )
        self.dry_run = dry_run

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.append_chat_history(f"\n# aider chat started at {current_time}\n\n")

        self.is_dumb_terminal = is_dumb_terminal()
        self.is_tty = sys.stdout.isatty()

        if self.is_dumb_terminal:
            self.pretty = False
            fancy_input = False

        # Spinner state
        self.spinner_running = False
        self.spinner_text = ""
        self.last_spinner_text = ""
        self.spinner_frame_index = 0
        self.spinner_last_frame_index = 0
        self.unicode_palette = "░█"

        if fancy_input:
            # If unicode is supported, use the rich 'dots2' spinner, otherwise an ascii fallback
            if self._spinner_supports_unicode():
                self.spinner_frames = SPINNERS["dots2"]["frames"]
            else:
                # A simple ascii spinner
                self.spinner_frames = SPINNERS["line"]["frames"]

            # Initialize PromptSession only if we have a capable terminal
            session_kwargs = {
                "input": self.input,
                "output": self.output,
                "lexer": PygmentsLexer(MarkdownLexer),
                "editing_mode": self.editingmode,
                "bottom_toolbar": self.get_bottom_toolbar,
                "refresh_interval": 0.1,
            }
            if self.editingmode == EditingMode.VI:
                session_kwargs["cursor"] = ModalCursorShapeConfig()
            if self.input_history_file is not None:
                session_kwargs["history"] = FileHistory(self.input_history_file)
            try:
                self.prompt_session = PromptSession(**session_kwargs)
                self.console = Console()  # pretty console
            except Exception as err:
                self.console = Console(force_terminal=False, no_color=True)
                self.tool_error(f"Can't initialize prompt toolkit: {err}")  # non-pretty
        else:
            self.console = Console(force_terminal=False, no_color=True)  # non-pretty
            if self.is_dumb_terminal:
                self.tool_output("Detected dumb terminal, disabling fancy input and pretty output.")

        self.file_watcher = file_watcher
        self.root = root

        # Variables used to interface with base_coder
        self.coder = None
        self.input_task = None
        self.processing_task = None
        self.confirmation_in_progress = False
        self.confirmation_acknowledgement = False

        # State tracking for confirmation input
        self.confirmation_input_active = False
        self.saved_input_text = ""

        # Validate color settings after console is initialized
        self._validate_color_settings()

    def _spinner_supports_unicode(self) -> bool:
        if not self.is_tty:
            return False
        try:
            out = self.unicode_palette
            out += "\b" * len(self.unicode_palette)
            out += " " * len(self.unicode_palette)
            out += "\b" * len(self.unicode_palette)
            sys.stdout.write(out)
            sys.stdout.flush()
            return True
        except UnicodeEncodeError:
            return False
        except Exception:
            return False

    def start_spinner(self, text, update_last_text=True):
        """Start the spinner."""
        self.stop_spinner()

        if self.prompt_session:
            self.spinner_running = True
            self.spinner_text = text
            self.spinner_frame_index = self.spinner_last_frame_index

            if update_last_text:
                self.last_spinner_text = text
        else:
            self.fallback_spinner = Spinner(text)
            self.fallback_spinner.step()

    def stop_spinner(self):
        """Stop the spinner."""
        self.spinner_running = False
        self.spinner_text = ""
        # Keep last frame index to avoid spinner "jumping" on restart
        self.spinner_last_frame_index = self.spinner_frame_index
        if self.fallback_spinner:
            self.fallback_spinner.end()
            self.fallback_spinner = None

    def get_bottom_toolbar(self):
        """Get the current spinner frame and text for the bottom toolbar."""
        if not self.spinner_running or not self.spinner_frames:
            return None

        frame = self.spinner_frames[self.spinner_frame_index]
        self.spinner_frame_index = (self.spinner_frame_index + 1) % len(self.spinner_frames)

        return f"{frame} {self.spinner_text}"

    def _validate_color_settings(self):
        """Validate configured color strings and reset invalid ones."""
        color_attributes = [
            "user_input_color",
            "tool_output_color",
            "tool_error_color",
            "tool_warning_color",
            "assistant_output_color",
            "completion_menu_color",
            "completion_menu_bg_color",
            "completion_menu_current_color",
            "completion_menu_current_bg_color",
        ]
        for attr_name in color_attributes:
            color_value = getattr(self, attr_name, None)
            if color_value:
                try:
                    # Try creating a style to validate the color
                    RichStyle(color=color_value)
                except ColorParseError as e:
                    self.console.print(
                        "[bold red]Warning:[/bold red] Invalid configuration for"
                        f" {attr_name}: '{color_value}'. {e}. Disabling this color."
                    )
                    setattr(self, attr_name, None)  # Reset invalid color to None

    def _get_style(self):
        style_dict = {}
        if not self.pretty:
            return Style.from_dict(style_dict)

        if self.user_input_color:
            style_dict.setdefault("", self.user_input_color)
            style_dict.update(
                {
                    "pygments.literal.string": f"bold italic {self.user_input_color}",
                }
            )
            style_dict["bottom-toolbar"] = f"{self.user_input_color} noreverse"

        # Conditionally add 'completion-menu' style
        completion_menu_style = []
        if self.completion_menu_bg_color:
            completion_menu_style.append(f"bg:{self.completion_menu_bg_color}")
        if self.completion_menu_color:
            completion_menu_style.append(self.completion_menu_color)
        if completion_menu_style:
            style_dict["completion-menu"] = " ".join(completion_menu_style)

        # Conditionally add 'completion-menu.completion.current' style
        completion_menu_current_style = []
        if self.completion_menu_current_bg_color:
            completion_menu_current_style.append(self.completion_menu_current_bg_color)
        if self.completion_menu_current_color:
            completion_menu_current_style.append(f"bg:{self.completion_menu_current_color}")
        if completion_menu_current_style:
            style_dict["completion-menu.completion.current"] = " ".join(
                completion_menu_current_style
            )

        return Style.from_dict(style_dict)

    def read_image(self, filename):
        try:
            with open(str(filename), "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read())
                return encoded_string.decode("utf-8")
        except OSError as err:
            self.tool_error(f"{filename}: unable to read: {err}")
            return
        except FileNotFoundError:
            self.tool_error(f"{filename}: file not found error")
            return
        except IsADirectoryError:
            self.tool_error(f"{filename}: is a directory")
            return
        except Exception as e:
            self.tool_error(f"{filename}: {e}")
            return

    def read_text(self, filename, silent=False):
        if is_image_file(filename):
            return self.read_image(filename)

        try:
            with open(str(filename), "r", encoding=self.encoding) as f:
                return f.read()
        except FileNotFoundError:
            if not silent:
                self.tool_error(f"{filename}: file not found error")
            return
        except IsADirectoryError:
            if not silent:
                self.tool_error(f"{filename}: is a directory")
            return
        except OSError as err:
            if not silent:
                self.tool_error(f"{filename}: unable to read: {err}")
            return
        except UnicodeError as e:
            if not silent:
                self.tool_error(f"{filename}: {e}")
                self.tool_error("Use --encoding to set the unicode encoding.")
            return

    def write_text(self, filename, content, max_retries=5, initial_delay=0.1):
        """
        Writes content to a file, retrying with progressive backoff if the file is locked.

        :param filename: Path to the file to write.
        :param content: Content to write to the file.
        :param max_retries: Maximum number of retries if a file lock is encountered.
        :param initial_delay: Initial delay (in seconds) before the first retry.
        """
        if self.dry_run:
            return

        delay = initial_delay
        for attempt in range(max_retries):
            try:
                with open(str(filename), "w", encoding=self.encoding, newline=self.newline) as f:
                    f.write(content)
                return  # Successfully wrote the file
            except PermissionError as err:
                if attempt < max_retries - 1:
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    self.tool_error(
                        f"Unable to write file {filename} after {max_retries} attempts: {err}"
                    )
                    raise
            except OSError as err:
                self.tool_error(f"Unable to write file {filename}: {err}")
                raise

    def rule(self):
        if self.pretty:
            style = dict(style=self.user_input_color) if self.user_input_color else dict()
            self.console.rule(**style)
        else:
            print()

    def interrupt_input(self):
        if self.input_task and not self.input_task.done():
            self.input_task.cancel()

        if self.prompt_session and self.prompt_session.app:
            # Store any partial input before interrupting
            self.placeholder = self.prompt_session.app.current_buffer.text
            self.interrupted = True

            try:
                self.prompt_session.app.exit()
            finally:
                pass

    def reject_outstanding_confirmations(self):
        """Reject all outstanding confirmation dialogs."""
        # This method is now a no-op since we removed the confirmation_future logic
        pass

    async def get_input(
        self,
        root,
        rel_fnames,
        addable_rel_fnames,
        commands,
        abs_read_only_fnames=None,
        abs_read_only_stubs_fnames=None,
        edit_format=None,
    ):
        self.rule()

        rel_fnames = list(rel_fnames)
        show = ""
        if rel_fnames:
            rel_read_only_fnames = [
                get_rel_fname(fname, root) for fname in (abs_read_only_fnames or [])
            ]
            rel_read_only_stubs_fnames = [
                get_rel_fname(fname, root) for fname in (abs_read_only_stubs_fnames or [])
            ]
            show = self.format_files_for_input(
                rel_fnames, rel_read_only_fnames, rel_read_only_stubs_fnames
            )

        prompt_prefix = ""

        if edit_format:
            prompt_prefix += edit_format
        if self.multiline_mode:
            prompt_prefix += (" " if edit_format else "") + "multi"
        prompt_prefix += "> "

        show += prompt_prefix
        self.prompt_prefix = prompt_prefix

        inp = ""
        multiline_input = False

        style = self._get_style()

        completer_instance = ThreadedCompleter(
            AutoCompleter(
                root,
                rel_fnames,
                addable_rel_fnames,
                commands,
                self.encoding,
                abs_read_only_fnames=(abs_read_only_fnames or set())
                | (abs_read_only_stubs_fnames or set()),
            )
        )

        def suspend_to_bg(event):
            """Suspend currently running application."""
            event.app.suspend_to_background()

        kb = KeyBindings()

        @kb.add(Keys.ControlZ, filter=Condition(lambda: hasattr(signal, "SIGTSTP")))
        def _(event):
            "Suspend to background with ctrl-z"
            suspend_to_bg(event)

        @kb.add("c-space")
        def _(event):
            "Ignore Ctrl when pressing space bar"
            event.current_buffer.insert_text(" ")

        @kb.add("c-up")
        def _(event):
            "Navigate backward through history"
            event.current_buffer.history_backward()

        @kb.add("c-down")
        def _(event):
            "Navigate forward through history"
            event.current_buffer.history_forward()

        @kb.add("c-x", "c-e")
        def _(event):
            "Edit current input in external editor (like Bash)"
            buffer = event.current_buffer
            current_text = buffer.text

            # Open the editor with the current text
            edited_text = pipe_editor(input_data=current_text, suffix="md")

            # Replace the buffer with the edited text, strip any trailing newlines
            buffer.text = edited_text.rstrip("\n")

            # Move cursor to the end of the text
            buffer.cursor_position = len(buffer.text)

        @kb.add("c-t", filter=Condition(lambda: self.fzf_available))
        def _(event):
            "Fuzzy find files to add to the chat"
            buffer = event.current_buffer
            if not buffer.text.strip().startswith("/add "):
                return

            files = run_fzf(addable_rel_fnames, multi=True)
            if files:
                buffer.text = "/add " + " ".join(files)
                buffer.cursor_position = len(buffer.text)

        @kb.add("c-r", filter=Condition(lambda: self.fzf_available))
        def _(event):
            "Fuzzy search in history and paste it in the prompt"
            buffer = event.current_buffer
            history_lines = self.get_input_history()
            selected_lines = run_fzf(history_lines)
            if selected_lines:
                buffer.text = "".join(selected_lines)
                buffer.cursor_position = len(buffer.text)

        @kb.add("enter", eager=True, filter=~is_searching)
        def _(event):
            "Handle Enter key press"
            if self.multiline_mode and not (
                self.editingmode == EditingMode.VI
                and event.app.vi_state.input_mode == InputMode.NAVIGATION
            ):
                # In multiline mode and if not in vi-mode or vi navigation/normal mode,
                # Enter adds a newline
                event.current_buffer.insert_text("\n")
            else:
                # In normal mode, Enter submits
                event.current_buffer.validate_and_handle()

        @kb.add("escape", "enter", eager=True, filter=~is_searching)  # This is Alt+Enter
        def _(event):
            "Handle Alt+Enter key press"
            if self.multiline_mode:
                # In multiline mode, Alt+Enter submits
                event.current_buffer.validate_and_handle()
            else:
                # In normal mode, Alt+Enter adds a newline
                event.current_buffer.insert_text("\n")

        while True:
            if multiline_input:
                show = self.prompt_prefix

            try:
                if self.prompt_session:
                    # Use placeholder if set, then clear it
                    default = self.placeholder or ""
                    self.placeholder = None

                    self.interrupted = False
                    if not multiline_input:
                        if self.file_watcher:
                            self.file_watcher.start()
                        if self.clipboard_watcher:
                            self.clipboard_watcher.start()

                    def get_continuation(width, line_number, is_soft_wrap):
                        return self.prompt_prefix

                    line = await self.prompt_session.prompt_async(
                        show,
                        default=default,
                        completer=completer_instance,
                        reserve_space_for_menu=4,
                        complete_style=CompleteStyle.MULTI_COLUMN,
                        style=style,
                        key_bindings=kb,
                        complete_while_typing=True,
                        prompt_continuation=get_continuation,
                    )
                else:
                    line = await asyncio.get_event_loop().run_in_executor(None, input, show)

                # Check if we were interrupted by a file change
                if self.interrupted:
                    line = line or ""
                    if self.file_watcher:
                        cmd = self.file_watcher.process_changes()
                        return cmd

            except EOFError:
                raise
            except KeyboardInterrupt:
                self.console.print()
                return ""
            except UnicodeEncodeError as err:
                self.tool_error(str(err))
                return ""
            except Exception as err:
                try:
                    self.prompt_session.app.exit()
                except Exception:
                    pass

                import traceback

                self.tool_error(str(err))
                self.tool_error(traceback.format_exc())
                return ""
            finally:
                if self.file_watcher:
                    self.file_watcher.stop()
                if self.clipboard_watcher:
                    self.clipboard_watcher.stop()

            if line.strip("\r\n") and not multiline_input:
                stripped = line.strip("\r\n")
                if stripped == "{":
                    multiline_input = True
                    multiline_tag = None
                    inp += ""
                elif stripped[0] == "{":
                    # Extract tag if it exists (only alphanumeric chars)
                    tag = "".join(c for c in stripped[1:] if c.isalnum())
                    if stripped == "{" + tag:
                        multiline_input = True
                        multiline_tag = tag
                        inp += ""
                    else:
                        inp = line
                        break
                else:
                    inp = line
                    break
                continue
            elif multiline_input and line.strip():
                if multiline_tag:
                    # Check if line is exactly "tag}"
                    if line.strip("\r\n") == f"{multiline_tag}}}":
                        break
                    else:
                        inp += line + "\n"
                # Check if line is exactly "}"
                elif line.strip("\r\n") == "}":
                    break
                else:
                    inp += line + "\n"
            elif multiline_input:
                inp += line + "\n"
            else:
                inp = line
                break

        self.user_input(inp)
        return inp

    async def cancel_input_task(self):
        if self.input_task:
            input_task = self.input_task
            self.input_task = None
            try:
                input_task.cancel()
                await input_task
            except (asyncio.CancelledError, IndexError):
                pass

    async def cancel_processing_task(self):
        if self.processing_task:
            processing_task = self.processing_task
            self.processing_task = None
            try:
                processing_task.cancel()
                await processing_task
            except (asyncio.CancelledError, IndexError):
                pass

    def add_to_input_history(self, inp):
        if not self.input_history_file:
            return
        try:
            FileHistory(self.input_history_file).append_string(inp)
            # Also add to the in-memory history if it exists
            if self.prompt_session and self.prompt_session.history:
                self.prompt_session.history.append_string(inp)
        except OSError as err:
            self.tool_warning(f"Unable to write to input history file: {err}")

    def get_input_history(self):
        if not self.input_history_file:
            return []

        fh = FileHistory(self.input_history_file)
        return fh.load_history_strings()

    def log_llm_history(self, role, content):
        if not self.llm_history_file:
            return
        timestamp = datetime.now().isoformat(timespec="seconds")
        try:
            Path(self.llm_history_file).parent.mkdir(parents=True, exist_ok=True)
            with open(self.llm_history_file, "a", encoding="utf-8") as log_file:
                log_file.write(f"{role.upper()} {timestamp}\n")
                log_file.write(content + "\n")
        except (PermissionError, OSError) as err:
            self.tool_warning(f"Unable to write to llm history file {self.llm_history_file}: {err}")
            self.llm_history_file = None

    def display_user_input(self, inp):
        if self.pretty and self.user_input_color:
            style = dict(style=self.user_input_color)
        else:
            style = dict()

        self.stream_print(Text(inp), **style)

    def user_input(self, inp, log_only=True):
        if not log_only:
            self.display_user_input(inp)

        prefix = "####"
        if inp:
            hist = inp.splitlines()
        else:
            hist = ["<blank>"]

        hist = f"  \n{prefix} ".join(hist)

        hist = f"""
{prefix} {hist}"""
        self.append_chat_history(hist, linebreak=True)

    # OUTPUT

    def ai_output(self, content):
        hist = "\n" + content.strip() + "\n\n"
        self.append_chat_history(hist)

    async def offer_url(self, url, prompt="Open URL for more info?", allow_never=True):
        """Offer to open a URL in the browser, returns True if opened."""
        if url in self.never_prompts:
            return False
        if await self.confirm_ask(prompt, subject=url, allow_never=allow_never):
            webbrowser.open(url)
            return True
        return False

    def set_confirmation_acknowledgement(self):
        self.confirmation_acknowledgement = True

    def get_confirmation_acknowledgement(self):
        return self.confirmation_acknowledgement

    def acknowledge_confirmation(self):
        outstanding_confirmation = self.confirmation_acknowledgement
        self.confirmation_acknowledgement = False
        return outstanding_confirmation

    @restore_multiline_async
    async def confirm_ask(
        self,
        *args,
        **kwargs,
    ):
        self.confirmation_in_progress = True

        try:
            self.set_confirmation_acknowledgement()
            return await asyncio.create_task(self._confirm_ask(*args, **kwargs))
        except KeyboardInterrupt:
            # Re-raise KeyboardInterrupt to allow it to propagate
            raise
        finally:
            self.confirmation_in_progress = False

    async def _confirm_ask(
        self,
        question,
        default="y",
        subject=None,
        explicit_yes_required=False,
        group=None,
        allow_never=False,
    ):
        self.num_user_asks += 1

        question_id = (question, subject)

        try:
            if question_id in self.never_prompts:
                return False

            if group and not group.show_group:
                group = None
            if group:
                allow_never = True

            valid_responses = ["yes", "no", "skip", "all"]
            options = " (Y)es/(N)o"
            if group:
                if not explicit_yes_required:
                    options += "/(A)ll"
                options += "/(S)kip all"
            if allow_never:
                options += "/(D)on't ask again"
                valid_responses.append("don't")

            if default.lower().startswith("y"):
                question += options + " [Yes]: "
            elif default.lower().startswith("n"):
                question += options + " [No]: "
            else:
                question += options + f" [{default}]: "

            if subject:
                self.tool_output()
                if "\n" in subject:
                    lines = subject.splitlines()
                    max_length = max(len(line) for line in lines)
                    padded_lines = [line.ljust(max_length) for line in lines]
                    padded_subject = "\n".join(padded_lines)
                    self.tool_output(padded_subject, bold=True)
                else:
                    self.tool_output(subject, bold=True)

            if self.yes is True:
                res = "n" if explicit_yes_required else "y"
                self.acknowledge_confirmation()
            elif self.yes is False:
                res = "n"
                self.acknowledge_confirmation()
            elif group and group.preference:
                res = group.preference
                self.user_input(f"{question}{res}", log_only=False)
                self.acknowledge_confirmation()
            else:
                # Ring the bell if needed
                self.ring_bell()
                self.start_spinner("Awaiting Confirmation...", False)

                while True:
                    try:
                        if self.prompt_session:
                            if (
                                not self.input_task
                                or self.input_task.done()
                                or self.input_task.cancelled()
                            ):
                                coder = self.coder() if self.coder else None

                                if coder:
                                    self.input_task = asyncio.create_task(coder.get_input())
                                    await asyncio.sleep(0)

                            if (
                                self.input_task
                                and not self.input_task.done()
                                and not self.input_task.cancelled()
                            ):
                                self.prompt_session.message = question
                                self.prompt_session.app.invalidate()
                            else:
                                continue

                            res = await self.input_task
                        else:
                            res = await asyncio.get_event_loop().run_in_executor(
                                None, input, question
                            )
                    except EOFError:
                        # Treat EOF (Ctrl+D) as if the user pressed Enter
                        res = default
                        break
                    except asyncio.CancelledError:
                        return False

                    if not res:
                        res = default
                        break
                    res = res.lower()
                    good = any(valid_response.startswith(res) for valid_response in valid_responses)

                    if good:
                        self.start_spinner(self.last_spinner_text)
                        break

                    error_message = f"Please answer with one of: {', '.join(valid_responses)}"
                    self.tool_error(error_message)

            res = res.lower()[0]

            if res == "d" and allow_never:
                self.never_prompts.add(question_id)
                hist = f"{question.strip()} {res}"
                self.append_chat_history(hist, linebreak=True, blockquote=True)
                return False

            if explicit_yes_required:
                is_yes = res == "y"
            else:
                is_yes = res in ("y", "a")

            is_all = res == "a" and group is not None and not explicit_yes_required
            is_skip = res == "s" and group is not None

            if group:
                if is_all and not explicit_yes_required:
                    group.preference = "all"
                elif is_skip:
                    group.preference = "skip"

            hist = f"{question.strip()} {res}"
            self.append_chat_history(hist, linebreak=True, blockquote=True)
        except asyncio.CancelledError:
            return False
        finally:
            pass
        return is_yes

    @restore_multiline
    def prompt_ask(self, question, default="", subject=None):
        self.num_user_asks += 1

        # Ring the bell if needed
        self.ring_bell()

        if subject:
            self.tool_output()
            self.tool_output(subject, bold=True)

        style = self._get_style()

        if self.yes is True:
            res = "yes"
        elif self.yes is False:
            res = "no"
        else:
            try:
                if self.prompt_session:
                    res = self.prompt_session.prompt(
                        question + " ",
                        default=default,
                        style=style,
                        complete_while_typing=True,
                    )
                else:
                    res = input(question + " ")
            except EOFError:
                # Treat EOF (Ctrl+D) as if the user pressed Enter
                res = default

        hist = f"{question.strip()} {res.strip()}"
        self.append_chat_history(hist, linebreak=True, blockquote=True)
        if self.yes in (True, False):
            self.tool_output(hist)

        return res

    def _tool_message(self, message="", strip=True, color=None):
        if message.strip():
            if "\n" in message:
                for line in message.splitlines():
                    self.append_chat_history(line, linebreak=True, blockquote=True, strip=strip)
            else:
                hist = message.strip() if strip else message
                self.append_chat_history(hist, linebreak=True, blockquote=True)

        if not isinstance(message, Text):
            message = Text(message)

        style = dict()
        if self.pretty:
            if color:
                style["color"] = ensure_hash_prefix(color)

        style = RichStyle(**style)

        try:
            self.stream_print(message, style=style)
        except UnicodeEncodeError:
            # Fallback to ASCII-safe output
            if isinstance(message, Text):
                message = message.plain
            message = str(message).encode("ascii", errors="replace").decode("ascii")
            self.stream_print(message, style=style)

    def tool_success(self, message="", strip=True):
        self._tool_message(message, strip, self.user_input_color)

    def tool_error(self, message="", strip=True):
        self.num_error_outputs += 1
        self._tool_message(message, strip, self.tool_error_color)

    def tool_warning(self, message="", strip=True):
        self._tool_message(message, strip, self.tool_warning_color)

    def tool_output(self, *messages, log_only=False, bold=False):
        if messages:
            hist = " ".join(messages)
            hist = f"{hist.strip()}"
            self.append_chat_history(hist, linebreak=True, blockquote=True)

        if log_only:
            return

        messages = list(map(Text, messages))
        style = dict()
        if self.pretty:
            if self.tool_output_color:
                style["color"] = ensure_hash_prefix(self.tool_output_color)
            # if bold:
            #     style["bold"] = True

        style = RichStyle(**style)

        self.stream_print(*messages, style=style)

    def assistant_output(self, message, pretty=None):
        if not message:
            self.tool_warning("Empty response received from LLM. Check your provider account?")
            return

        show_resp = message

        # Coder will force pretty off if fence is not triple-backticks
        if pretty is None:
            pretty = self.pretty

        if pretty:
            show_resp = Markdown(
                message, style=self.assistant_output_color, code_theme=self.code_theme
            )
        else:
            show_resp = Text(message or "(empty response)")

        self.stream_print(show_resp)

    def render_markdown(self, text):
        output = StringIO()
        console = Console(file=output, force_terminal=True, color_system="truecolor")
        md = Markdown(text, style=self.assistant_output_color, code_theme=self.code_theme)
        console.print(md)
        return output.getvalue()

    def stream_output(self, text, final=False):
        """
        Stream output using Rich console to respect pretty print settings.
        This preserves formatting, colors, and other Rich features during streaming.
        """
        # Initialize buffer if not exists
        if not hasattr(self, "_stream_buffer"):
            self._stream_buffer = ""

        # Initialize buffer if not exists
        if not hasattr(self, "_stream_line_count"):
            self._stream_line_count = 0

        self._stream_buffer += text

        # Process the buffer to find complete lines
        lines = self._stream_buffer.split("\n")
        complete_lines = []
        incomplete_line = ""
        output = ""

        if len(lines) > 1 or final:
            # All lines except the last one are complete
            complete_lines = lines[:-1] if not final else lines
            incomplete_line = lines[-1] if not final else ""

            for complete_line in complete_lines:
                output += complete_line
                self._stream_line_count += 1

            self._stream_buffer = incomplete_line

        if not final:
            if len(lines) > 1:
                self.console.print(
                    Text.from_ansi(output) if self.has_ansi_codes(output) else output
                )
        else:
            # Ensure any remaining buffered content is printed using the full response
            self.console.print(Text.from_ansi(output) if self.has_ansi_codes(output) else output)
            self.reset_streaming_response()

    def has_ansi_codes(self, s: str) -> bool:
        """Check if a string contains the ANSI escape character."""
        return "\x1b" in s

    def reset_streaming_response(self):
        self._stream_buffer = ""
        self._stream_line_count = 0

    def stream_print(self, *messages, **kwargs):
        with self.console.capture() as capture:
            self.console.print(*messages, **kwargs)
        capture_text = capture.get()
        self.stream_output(capture_text, final=False)

    def set_placeholder(self, placeholder):
        """Set a one-time placeholder text for the next input prompt."""
        self.placeholder = placeholder

    def print(self, message=""):
        print(message)

    def llm_started(self):
        """Mark that the LLM has started processing, so we should ring the bell on next input"""
        self.bell_on_next_input = True

    def get_default_notification_command(self):
        """Return a default notification command based on the operating system."""
        import platform

        system = platform.system()

        if system == "Darwin":  # macOS
            # Check for terminal-notifier first
            if shutil.which("terminal-notifier"):
                return f"terminal-notifier -title 'Aider' -message '{NOTIFICATION_MESSAGE}'"
            # Fall back to osascript
            return (
                f'osascript -e \'display notification "{NOTIFICATION_MESSAGE}" with title "Aider"\''
            )
        elif system == "Linux":
            # Check for common Linux notification tools
            for cmd in ["notify-send", "zenity"]:
                if shutil.which(cmd):
                    if cmd == "notify-send":
                        return f"notify-send 'Aider' '{NOTIFICATION_MESSAGE}'"
                    elif cmd == "zenity":
                        return f"zenity --notification --text='{NOTIFICATION_MESSAGE}'"
            return None  # No known notification tool found
        elif system == "Windows":
            # PowerShell notification
            return (
                "powershell -command"
                " \"[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms');"
                f" [System.Windows.Forms.MessageBox]::Show('{NOTIFICATION_MESSAGE}',"
                " 'Aider')\""
            )

        return None  # Unknown system

    def ring_bell(self):
        """Ring the terminal bell if needed and clear the flag"""
        if self.bell_on_next_input and self.notifications:
            if self.notifications_command:
                try:
                    result = subprocess.run(
                        self.notifications_command, shell=True, capture_output=True
                    )
                    if result.returncode != 0 and result.stderr:
                        error_msg = result.stderr.decode("utf-8", errors="replace")
                        self.tool_warning(f"Failed to run notifications command: {error_msg}")
                except Exception as e:
                    self.tool_warning(f"Failed to run notifications command: {e}")
            else:
                print("\a", end="", flush=True)  # Ring the bell
            self.bell_on_next_input = False  # Clear the flag

    def toggle_multiline_mode(self):
        """Toggle between normal and multiline input modes"""
        self.multiline_mode = not self.multiline_mode
        if self.multiline_mode:
            self.tool_output(
                "Multiline mode: Enabled. Enter inserts newline, Alt-Enter submits text"
            )
        else:
            self.tool_output(
                "Multiline mode: Disabled. Alt-Enter inserts newline, Enter submits text"
            )

    def append_chat_history(self, text, linebreak=False, blockquote=False, strip=True):
        if blockquote:
            if strip:
                text = text.strip()
            text = "> " + text
        if linebreak:
            if strip:
                text = text.rstrip()
            text = text + "  \n"
        if not text.endswith("\n"):
            text += "\n"
        if self.chat_history_file is not None:
            try:
                self.chat_history_file.parent.mkdir(parents=True, exist_ok=True)
                with self.chat_history_file.open(
                    "a", encoding=self.encoding or "utf-8", errors="ignore"
                ) as f:
                    f.write(text)
            except (PermissionError, OSError) as err:
                print(f"Warning: Unable to write to chat history file {self.chat_history_file}.")
                print(err)
                self.chat_history_file = None  # Disable further attempts to write

    def format_files_for_input(self, rel_fnames, rel_read_only_fnames, rel_read_only_stubs_fnames):
        # Optimization for large number of files
        total_files = (
            len(rel_fnames)
            + len(rel_read_only_fnames or [])
            + len(rel_read_only_stubs_fnames or [])
        )

        # For very large numbers of files, use a summary display
        if total_files > 50:
            read_only_count = len(rel_read_only_fnames or [])
            stub_file_count = len(rel_read_only_stubs_fnames or [])
            editable_count = len([f for f in rel_fnames if f not in (rel_read_only_fnames or [])])

            summary = f"{editable_count} editable file(s)"
            if read_only_count > 0:
                summary += f", {read_only_count} read-only file(s)"
            if stub_file_count > 0:
                summary += f", {stub_file_count} stub file(s)"
            summary += " (use /ls to list all files)\n"
            return summary

        # Original implementation for reasonable number of files
        if not self.pretty:
            lines = []
            # Handle regular read-only files
            for fname in sorted(rel_read_only_fnames or []):
                lines.append(f"{fname} (read only)")
            # Handle stub files separately
            for fname in sorted(rel_read_only_stubs_fnames or []):
                lines.append(f"{fname} (read only stub)")
            # Handle editable files
            for fname in sorted(rel_fnames):
                if fname not in rel_read_only_fnames and fname not in rel_read_only_stubs_fnames:
                    lines.append(fname)
            return "\n".join(lines) + "\n"

        output = StringIO()
        console = Console(file=output, force_terminal=False)

        # Handle read-only files
        if rel_read_only_fnames or rel_read_only_stubs_fnames:
            ro_paths = []
            # Regular read-only files
            for rel_path in sorted(rel_read_only_fnames or []):
                abs_path = os.path.abspath(os.path.join(self.root, rel_path))
                ro_paths.append(abs_path if len(abs_path) < len(rel_path) else rel_path)
            # Stub files with (stub) marker
            for rel_path in sorted(rel_read_only_stubs_fnames or []):
                abs_path = os.path.abspath(os.path.join(self.root, rel_path))
                path = abs_path if len(abs_path) < len(rel_path) else rel_path
                ro_paths.append(f"{path} (stub)")

            if ro_paths:
                files_with_label = ["Readonly:"] + ro_paths
                read_only_output = StringIO()
                Console(file=read_only_output, force_terminal=False).print(
                    Columns(files_with_label)
                )
                read_only_lines = read_only_output.getvalue().splitlines()
                console.print(Columns(files_with_label))

        # Handle editable files
        editable_files = [
            f
            for f in sorted(rel_fnames)
            if f not in rel_read_only_fnames and f not in rel_read_only_stubs_fnames
        ]
        if editable_files:
            files_with_label = editable_files
            if rel_read_only_fnames or rel_read_only_stubs_fnames:
                files_with_label = ["Editable:"] + editable_files
                editable_output = StringIO()
                Console(file=editable_output, force_terminal=False).print(Columns(files_with_label))
                editable_lines = editable_output.getvalue().splitlines()
                if len(read_only_lines) > 1 or len(editable_lines) > 1:
                    console.print()
            console.print(Columns(files_with_label))
        return output.getvalue()


def get_rel_fname(fname, root):
    try:
        return os.path.relpath(fname, root)
    except ValueError:
        return fname
