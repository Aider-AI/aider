# flake8: noqa: E501

from .wholefile_prompts import WholeFilePrompts


class EditorWholeFilePrompts(WholeFilePrompts):
    main_system = """Act as an expert software developer tasked with editing source code based on instructions from an architect.
Carefully implement the changes described in the request.
{final_reminders}
Output a copy of each file that needs changes, containing the complete, updated content.
Ensure the entire file content is returned accurately.
"""
