# flake8: noqa: E501

from typing import Optional
from dataclasses import dataclass
from .base_prompts import CoderPrompts


@dataclass
class EditBlockFunctionPrompts(CoderPrompts):
    main_system: str = """Act as an expert software developer.
Take requests for changes to the supplied code.
If the request is ambiguous, ask questions.

Once you understand the request you MUST use the `replace_lines` function to edit the files to make the needed changes.
"""

    system_reminder: str = """
ONLY return code using the `replace_lines` function.
NEVER return code outside the `replace_lines` function.
"""

    files_content_prefix: str = "Here is the current content of the files:\n"
    files_no_full_files: str = "I am not sharing any files yet."
    redacted_edit_message: str = "No changes are needed."

    repo_content_prefix: str = (
        "Below here are summaries of other files! Do not propose changes to these *read-only*"
        " files without asking me first.\n"
    )

    def __post_init__(self):
        """Initialize any additional state after dataclass creation"""
        super().__init__()
