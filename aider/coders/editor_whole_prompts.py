# flake8: noqa: E501

from .wholefile_prompts import WholeFilePrompts


class EditorWholeFilePrompts(WholeFilePrompts):
    main_system = """Act as an expert software developer and make changes to source code.
{final_reminders}
Output a copy of each file that needs changes.
"""
