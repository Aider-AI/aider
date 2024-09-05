import pyperclip
import sys

if len(sys.argv) > 1 and sys.argv[1] in ('-c', '--copy'):
    if len(sys.argv) > 2:
        pyperclip.copy(sys.argv[2])
    else:
        pyperclip.copy(sys.stdin.read())
elif len(sys.argv) > 1 and sys.argv[1] in ('-p', '--paste'):
    sys.stdout.write(pyperclip.paste())
else:
    print('Usage: python -m pyperclip [-c | --copy] [text_to_copy] | [-p | --paste]')
    print()
    print('If a text_to_copy argument is provided, it is copied to the')
    print('clipboard. Otherwise, the stdin stream is copied to the')
    print('clipboard. (If reading this in from the keyboard, press')
    print('CTRL-Z on Windows or CTRL-D on Linux/macOS to stop.')
    print('When pasting, the clipboard will be written to stdout.')