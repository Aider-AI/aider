#!/bin/bash

# Check if there is exactly one active window
WINDOW_COUNT=$(tmux list-windows | wc -l)
if [ "$WINDOW_COUNT" -ne 1 ]; then
    echo "Error: Expected exactly 1 tmux window, found $WINDOW_COUNT windows."
    exit 1
fi

# Get tmux window size (width x height)
TMUX_SIZE=$(tmux display -p '#{window_width}x#{window_height}')

# Print the terminal size
echo "Using terminal size: $TMUX_SIZE"

# Start asciinema recording with the tmux window size
asciinema rec -c "tmux attach -t 0 -r" --headless --tty-size $TMUX_SIZE $*

