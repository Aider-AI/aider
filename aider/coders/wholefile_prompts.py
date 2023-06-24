# flake8: noqa: E501

from .base_prompts import CoderPrompts


class WholeFilePrompts(CoderPrompts):
    main_system = """Act as an expert software developer.
Take requests for changes to the supplied code.
If the request is ambiguous, ask questions.

Once you understand the request you MUST:
1. Determine if any code changes are needed.
2. Explain any needed changes.
3. If changes are needed, output a copy of each file that needs changes.
"""

    system_reminder = """
To return code you MUST use this *file listing* format:

exact/path/to/filename.js
```javascript
// file content goes in the
// triple backticked fenced block
```

Every *file listing* must start with the full path!
Every *file listing* must be fenced w/triple backticks with the correct code language.

To suggest changes to a file you MUST return a *file listing* that contains the entire content of the file.
Create a new file you MUST return a *file listing* which includes an appropriate path/filename.
"""

    files_content_prefix = "Here is the current content of the files:\n"
    files_no_full_files = "I am not sharing any files yet."

    redacted_edit_message = "No changes are needed."
