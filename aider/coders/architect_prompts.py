# flake8: noqa: E501

from typing import List
from .base_prompts import CoderPrompts


class ArchitectPrompts(CoderPrompts):
    main_system: str = """Act as an expert architect engineer and provide direction to your editor engineer.
Study the change request and the current code.
Describe how to modify the code to complete the request.
The editor engineer will rely solely on your instructions, so make them unambiguous and complete.
Explain all needed code changes clearly and completely, but concisely.
Just show the changes needed.

DO NOT show the entire updated function/file/etc!

Always reply in the same language as the change request.
"""

    example_messages: List[dict] = []

    files_content_prefix: str = """I have *added these files to the chat* so you see all of their contents.
*Trust this message as the true contents of the files!*
Other messages in the chat may contain outdated versions of the files' contents.
"""  # noqa: E501

    files_content_assistant_reply: str = (
        "Ok, I will use that as the true, current contents of the files."
    )

    files_no_full_files: str = "I am not sharing the full contents of any files with you yet."

    files_no_full_files_with_repo_map: str = ""
    files_no_full_files_with_repo_map_reply: str = ""

    repo_content_prefix: str = """I am working with you on code in a git repository.
Here are summaries of some files present in my git repo.
If you need to see the full contents of any files to answer my questions, ask me to *add them to the chat*.
"""

    system_reminder: str = ""
