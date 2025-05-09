KITT_CHARS = ["\u2591", "\u2592", "\u2593", "\u2588"]  # ░, ▒, ▓, █

ASCII_FRAMES = [
    "#=        ",  # C1 C2 space(8)
    "=#        ",  # C2 C1 space(8)
    " =#       ",  # space(1) C2 C1 space(7)
    "  =#      ",  # space(2) C2 C1 space(6)
    "   =#     ",  # space(3) C2 C1 space(5)
    "    =#    ",  # space(4) C2 C1 space(4)
    "     =#   ",  # space(5) C2 C1 space(3)
    "      =#  ",  # space(6) C2 C1 space(2)
    "       =# ",  # space(7) C2 C1 space(1)
    "        =#",  # space(8) C2 C1
    "        #=",  # space(8) C1 C2
    "       #= ",  # space(7) C1 C2 space(1)
    "      #=  ",  # space(6) C1 C2 space(2)
    "     #=   ",  # space(5) C1 C2 space(3)
    "    #=    ",  # space(4) C1 C2 space(4)
    "   #=     ",  # space(3) C1 C2 space(5)
    "  #=      ",  # space(2) C1 C2 space(6)
    " #=       ",  # space(1) C1 C2 space(7)
]

# Class variable to store the last frame index for ASCII spinner
default_spinner_last_frame_idx = 0


def generate_default_frame(current_frame_idx, use_unicode_palette, original_unicode_palette_str):
    global default_spinner_last_frame_idx

    frames_to_use = list(ASCII_FRAMES) # Make a copy to modify if unicode is used
    scan_char = "#"

    if use_unicode_palette:
        translation_table = str.maketrans("=#", original_unicode_palette_str)
        frames_to_use = [f.translate(translation_table) for f in ASCII_FRAMES]
        try:
            scan_char = original_unicode_palette_str[ASCII_FRAMES[0].find("#")]
        except IndexError:
            scan_char = original_unicode_palette_str[0] if original_unicode_palette_str else "#"

    frame = frames_to_use[current_frame_idx]
    next_frame_idx = (current_frame_idx + 1) % len(frames_to_use)
    default_spinner_last_frame_idx = next_frame_idx  # Update shared last frame index
    return frame, next_frame_idx, scan_char


def generate_kitt_frame(scanner_width, current_scanner_position, current_scanner_direction):
    current_display_chars = [" "] * scanner_width

    if 0 <= current_scanner_position < scanner_width:
        current_display_chars[current_scanner_position] = KITT_CHARS[3]

    tail_symbols = [KITT_CHARS[2], KITT_CHARS[1], KITT_CHARS[0]]
    for i, tail_symbol in enumerate(tail_symbols):
        distance_from_head = i + 1
        tail_pos = current_scanner_position - distance_from_head if current_scanner_direction == 1 else current_scanner_position + distance_from_head
        if 0 <= tail_pos < scanner_width:
            current_display_chars[tail_pos] = tail_symbol
    
    if scanner_width <= 0:
        return "".join(current_display_chars), current_scanner_position, current_scanner_direction

    next_scanner_position = current_scanner_position
    next_scanner_direction = current_scanner_direction

    if current_scanner_direction == 1:
        if current_scanner_position >= scanner_width - 1:
            next_scanner_direction = -1
            next_scanner_position = max(0, scanner_width - 1)
        else:
            next_scanner_position += 1
    else:  # scanner_direction == -1
        if current_scanner_position <= 0:
            next_scanner_direction = 1
            next_scanner_position = 0
        else:
            next_scanner_position -= 1
    
    if not (0 <= next_scanner_position < scanner_width) and scanner_width > 0:
            next_scanner_position = next_scanner_position % scanner_width
            
    return "".join(current_display_chars), next_scanner_position, next_scanner_direction


SNAKE_CHARS = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"] # Braille characters for snake
snake_spinner_last_frame_idx = 0

def generate_snake_frame(current_frame_idx):
    global snake_spinner_last_frame_idx
    frame = SNAKE_CHARS[current_frame_idx]
    next_frame_idx = (current_frame_idx + 1) % len(SNAKE_CHARS)
    snake_spinner_last_frame_idx = next_frame_idx
    return frame, next_frame_idx


PUMP_CHARS = ["▂", "▃", "▄", "▅", "▆", "▇", "█", "▇", "▆", "▅", "▄", "▃"] # Characters for pump
pump_spinner_last_frame_idx = 0

def generate_pump_frame(current_frame_idx):
    global pump_spinner_last_frame_idx
    frame = PUMP_CHARS[current_frame_idx]
    next_frame_idx = (current_frame_idx + 1) % len(PUMP_CHARS)
    pump_spinner_last_frame_idx = next_frame_idx
    return frame, next_frame_idx


BALL_CHARS = ["◐", "◓", "◑", "◒"]
# No global last_frame_idx needed for ball as its state is more complex (pos, char_idx, direction)

def generate_ball_frame(current_pos, current_char_idx, current_direction, width):
    frame_chars = [" "] * width
    
    # Place current ball character
    if 0 <= current_pos < width:
        frame_chars[current_pos] = BALL_CHARS[current_char_idx]

    # Determine next state
    next_char_idx = (current_char_idx + 1) % len(BALL_CHARS)
    next_pos = current_pos
    next_direction = current_direction

    if width <= 0: # Should not happen if width is validated in Spinner
        return "".join(frame_chars), current_pos, next_char_idx, current_direction

    if current_direction == 1: # Moving right
        next_pos = current_pos + 1
        if next_pos >= width -1: # Hit right edge
            next_pos = width - 1
            next_direction = -1 # Change direction to left
    else: # Moving left (current_direction == -1)
        next_pos = current_pos - 1
        if next_pos <= 0: # Hit left edge
            next_pos = 0
            next_direction = 1 # Change direction to right
            
    return "".join(frame_chars), next_pos, next_char_idx, next_direction
