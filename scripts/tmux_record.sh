#!/bin/bash

# Get tmux window size (width x height)
TMUX_SIZE=$(tmux display -p '#{window_width}x#{window_height}')

# Start asciinema recording with the tmux window size
asciinema rec -c "tmux attach -t 0 -r" --headless --tty-size $TMUX_SIZE $*

