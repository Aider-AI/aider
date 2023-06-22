# flake8: noqa: E501

from .prompts_base import EditorPrompts


class WholeFileFunctionPrompts(EditorPrompts):
    main_system = """Act as an expert software developer.
Take requests for changes to the supplied code.
If the request is ambiguous, ask questions.

Once you understand the request you MUST use the `write_file` function to edit the files to make the needed changes.
"""

    system_reminder = """
ONLY return code using the `write_file` function.
NEVER return code outside the `write_file` function.
"""

    files_content_prefix = "Here is the current content of the files:\n"
    files_no_full_files = "I am not sharing any files yet."

    redacted_edit_message = "No changes are needed."

    # TODO: make this optional, since this Coder doesn't use it
    repo_content_prefix = (
        "Below here are summaries of other files! Do not propose changes to these *read-only*"
        " files without asking me first.\n"
    )
