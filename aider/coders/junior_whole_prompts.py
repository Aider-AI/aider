# flake8: noqa: E501

from .wholefile_prompts import WholeFilePrompts


class EditorWholeFilePrompts(WholeFilePrompts):
    main_system = """Act as an expert software developer and make changes to source code.
{lazy_prompt}
Output a copy of each file that needs changes.
"""
