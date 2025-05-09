import sys
import time
from io import StringIO

from rich.console import Console
from rich.text import Text

from .config import SpinnerConfig, SpinnerStyle
from .frames import (
    KITT_CHARS,
    generate_default_frame,
    generate_kitt_frame,
    generate_snake_frame, 
    generate_pump_frame,
    generate_ball_frame, # Add ball frame generator
    default_spinner_last_frame_idx,
    snake_spinner_last_frame_idx,
    pump_spinner_last_frame_idx,
    # No global index for ball, its state is managed in Spinner instance
)


class Spinner:
    """
    Minimal spinner.
    Supports multiple animation styles (DEFAULT, KITT, ILOVECANDY).
    Falls back to simpler animations if Unicode is not well supported.
    """

    UNICODE_TEST_CHARS = KITT_CHARS[3] + "≋"  # For testing unicode support robustly

    def __init__(self, text: str, config: SpinnerConfig):
        self.text = text
        self.config = config
        self.start_time = time.time()
        self.last_update = 0.0
        self.visible = False
        self.is_tty = sys.stdout.isatty()
        self.console = Console()
        self.last_display_len = 0

        self.active_style = SpinnerStyle.DEFAULT # Fallback style
        self.animation_len = 0

        # Style-specific state
        self.default_frame_idx = default_spinner_last_frame_idx
        self.default_scan_char = "#"
        self.original_unicode_palette = "░█"
        self.supports_default_unicode = False

        self.kitt_scanner_width = 0
        self.kitt_scanner_position = 0
        self.kitt_scanner_direction = 1

        self.snake_frame_idx = snake_spinner_last_frame_idx
        self.pump_frame_idx = pump_spinner_last_frame_idx
        
        self.ball_width = 0
        self.ball_position = 0
        self.ball_char_idx = 0
        self.ball_direction = 1 # 1 for right, -1 for left
        

        # Determine active style and initialize
        if self.config.style == SpinnerStyle.KITT and self._supports_unicode_for_kitt():
            self.active_style = SpinnerStyle.KITT
            self.kitt_scanner_width = max(self.config.width, 4)
            self.animation_len = self.kitt_scanner_width
        elif self.config.style == SpinnerStyle.SNAKE and self._supports_unicode_for_snake():
            self.active_style = SpinnerStyle.SNAKE
            self.animation_len = 1 # Snake spinner is a single character
        elif self.config.style == SpinnerStyle.PUMP and self._supports_unicode_for_pump(): 
            self.active_style = SpinnerStyle.PUMP
            self.animation_len = 1 # Pump spinner is a single character
        elif self.config.style == SpinnerStyle.BALL and self._supports_unicode_for_ball():
            self.active_style = SpinnerStyle.BALL
            self.ball_width = max(self.config.width, 2) # Min width for ball to move
            self.animation_len = self.ball_width
        else: # Default or fallback
            self.active_style = SpinnerStyle.DEFAULT
            if self.config.style != SpinnerStyle.DEFAULT and self.is_tty:
                 print(f"\rWarning: {self.config.style.value} spinner requires better unicode/TTY support, falling back to default.", file=sys.stderr)
            
            self.supports_default_unicode = self._supports_unicode_for_default_style()
            # Animation length for default is fixed by its frames
            # A typical default frame like "#=        " has length 10.
            from .frames import ASCII_FRAMES # circular import guard
            self.animation_len = len(ASCII_FRAMES[0])


    def _supports_unicode_for_kitt(self) -> bool:
        if not self.is_tty:
            return False
        try:
            chars_to_test = self.UNICODE_TEST_CHARS
            num_chars_printed = len(chars_to_test)
            out = chars_to_test
            out += "\b" * num_chars_printed
            out += " " * num_chars_printed
            out += "\b" * num_chars_printed
            sys.stdout.write(out)
            sys.stdout.flush()
            return True
        except UnicodeEncodeError:
            return False
        except Exception:
            return False

    def _supports_unicode_for_snake(self) -> bool: 
        if not self.is_tty:
            return False
        try:
            from .frames import SNAKE_CHARS 
            out = SNAKE_CHARS[0]
            out += "\b" * len(out)
            out += " " * len(out)
            out += "\b" * len(out)
            sys.stdout.write(out)
            sys.stdout.flush()
            return True
        except UnicodeEncodeError:
            return False
        except Exception:
            return False

    def _supports_unicode_for_pump(self) -> bool: 
        if not self.is_tty:
            return False
        try:
            from .frames import PUMP_CHARS 
            out = PUMP_CHARS[0]
            out += "\b" * len(out)
            out += " " * len(out)
            out += "\b" * len(out)
            sys.stdout.write(out)
            sys.stdout.flush()
            return True
        except UnicodeEncodeError:
            return False
        except Exception:
            return False

    def _supports_unicode_for_ball(self) -> bool:
        if not self.is_tty:
            return False
        try:
            from .frames import BALL_CHARS
            out = BALL_CHARS[0]
            out += "\b" * len(out)
            out += " " * len(out)
            out += "\b" * len(out)
            sys.stdout.write(out)
            sys.stdout.flush()
            return True
        except UnicodeEncodeError:
            return False
        except Exception:
            return False

    def _supports_unicode_for_default_style(self) -> bool:
        if not self.is_tty:
            return False
        try:
            out = self.original_unicode_palette
            out += "\b" * len(self.original_unicode_palette)
            out += " " * len(self.original_unicode_palette)
            out += "\b" * len(self.original_unicode_palette)
            sys.stdout.write(out)
            sys.stdout.flush()
            return True
        except UnicodeEncodeError:
            return False
        except Exception:
            return False

    def _next_frame(self) -> str:
        frame_str = ""
        if self.active_style == SpinnerStyle.KITT:
            frame_str, self.kitt_scanner_position, self.kitt_scanner_direction = generate_kitt_frame(
                self.kitt_scanner_width, self.kitt_scanner_position, self.kitt_scanner_direction
            )
        elif self.active_style == SpinnerStyle.SNAKE: 
            frame_str, self.snake_frame_idx = generate_snake_frame(self.snake_frame_idx) 
            self.default_scan_char = frame_str # For cursor logic, treat as default
        elif self.active_style == SpinnerStyle.PUMP: 
            frame_str, self.pump_frame_idx = generate_pump_frame(self.pump_frame_idx) 
            self.default_scan_char = frame_str # For cursor logic, treat as default
        elif self.active_style == SpinnerStyle.BALL:
            frame_str, self.ball_position, self.ball_char_idx, self.ball_direction = generate_ball_frame(
                self.ball_position, self.ball_char_idx, self.ball_direction, self.ball_width
            )
            # For cursor logic, the "scan char" is the ball itself.
            # Since its character changes, we use its position.
        else: # DEFAULT
            frame_str, self.default_frame_idx, self.default_scan_char = generate_default_frame(
                self.default_frame_idx, self.supports_default_unicode, self.original_unicode_palette
            )
        return frame_str

    def step(self, text: str = None) -> None:
        if text is not None:
            self.text = text

        if not self.is_tty:
            return

        now = time.time()
        if not self.visible and now - self.start_time >= 0.5:
            self.visible = True
            self.last_update = 0.0
            if self.is_tty:
                self.console.show_cursor(False)

        if not self.visible or now - self.last_update < 0.1: # Animation speed
            return

        self.last_update = now
        frame_str = self._next_frame()
        
        max_spinner_width = self.console.width - 2
        if max_spinner_width < 0: max_spinner_width = 0

        current_text_payload_str = f" {self.text}"

        if self.config.color != "default" and self.config.color:
            frame_text_obj = Text(frame_str, style=self.config.color)
        else:
            frame_text_obj = Text(frame_str)
        
        payload_text_obj = Text(current_text_payload_str)
        text_line_obj = Text.assemble(frame_text_obj, payload_text_obj)
        text_line_obj.truncate(max_spinner_width, overflow="crop")
        
        temp_buffer = StringIO()
        temp_console = Console(
            file=temp_buffer,
            width=self.console.width,
            color_system=self.console.color_system,
            force_terminal=self.is_tty,
        )
        temp_console.print(text_line_obj, end="")
        rendered_text_line_str = temp_buffer.getvalue()
        
        len_line_to_display = text_line_obj.cell_len 
        padding_to_clear = " " * max(0, self.last_display_len - len_line_to_display)
        sys.stdout.write(f"\r{rendered_text_line_str}{padding_to_clear}")
        self.last_display_len = len_line_to_display
        
        total_chars_written_on_line = len_line_to_display + len(padding_to_clear)
        scan_char_abs_pos = -1

        if self.active_style == SpinnerStyle.KITT:
            scan_char_abs_pos = self.kitt_scanner_position
        elif self.active_style == SpinnerStyle.BALL:
            scan_char_abs_pos = self.ball_position
        else: # DEFAULT (includes SNAKE and PUMP which set default_scan_char)
            scan_char_abs_pos = frame_str.find(self.default_scan_char)

        if scan_char_abs_pos != -1 and 0 <= scan_char_abs_pos < len(frame_str):
            num_backspaces = total_chars_written_on_line - scan_char_abs_pos
            if num_backspaces > 0 :
                 sys.stdout.write("\b" * num_backspaces)
        sys.stdout.flush()

    def end(self) -> None:
        if self.visible and self.is_tty:
            clear_len = self.last_display_len 
            sys.stdout.write("\r" + " " * clear_len + "\r")
            sys.stdout.flush()
            self.console.show_cursor(True)
        self.visible = False
