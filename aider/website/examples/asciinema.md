---
parent: Example chat transcripts
---

# Editing an asciinema cast file with aider

The user needs to make some tedious edits to the escape sequences in an `asciinema` screencast file.

<div class="chat-transcript" markdown="1">

> $ aider hello.cast  
> Added hello.cast to the chat  

#### when the "hello.py> " prompt is displayed, it's including some escape codes to add a few blank lines below the prompt and then bringing the cursor back up. remove all that. just show the prompt followed by a space and leave the cursor showing right after that.  

```python
hello.cast
<<<<<<< ORIGINAL
[19.534013, "o", "\u001b[?2004h\u001b[?1l\u001b[?25l\u001b[0m\u001b[?7l\u001b[0m\u001b[J\u001b[0;38;5;28mhello.py>  \u001b[0m\r\r\n\r\r\n\r\r\n\u001b[0;38;5;28m                                                                \r\u001b[64C \r\u001b[3A\u001b[10C\u001b[?7h\u001b[0m\u001b[?12l\u001b[?25h"]
=======
[19.534013, "o", "\u001b[?2004h\u001b[?1l\u001b[?25l\u001b[0m\u001b[?7l\u001b[0m\u001b[J\u001b[0;38;5;28mhello.py> \u001b[0m\u001b[?7h\u001b[0m\u001b[?12l\u001b[?25h"]
>>>>>>> UPDATED
```

> Applied edit to hello.cast  
> Commit a3fa4d2 aider: Removed escape codes to display prompt and cursor correctly.  


</div>
