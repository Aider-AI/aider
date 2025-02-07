You can send long, multi-line messages in the chat in a few ways:
  - Paste a multi-line message directly into the chat.
  - Enter `{` alone on the first line to start a multiline message and `}` alone on the last line to end it.
    - Or, start with `{tag` (where "tag" is any sequence of letters/numbers) and end with `tag}`. This is useful when you need to include closing braces `}` in your message.
  - Use Meta-ENTER to start a new line without sending the message (Esc+ENTER in some environments).
  - Use `/paste` to paste text from the clipboard into the chat.
  - Use the `/editor` command to open your editor to create the next chat message. See [editor configuration docs](/docs/config/editor.html) for more info.
  - Use multiline-mode, which swaps the function of Meta-Enter and Enter, so that Enter inserts a newline, and Meta-Enter submits your command. To enable multiline mode:
    - Use the `/multiline-mode` command to toggle it during a session.
    - Use the `--multiline` switch.
  
Example with a tag:
```
{python
def hello():
    print("Hello}")  # Note: contains a brace
python}
```

{: .note }
People often ask for SHIFT-ENTER to be a soft-newline.
Unfortunately there is no portable way to detect that keystroke in terminals.
