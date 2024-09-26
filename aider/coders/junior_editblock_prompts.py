# flake8: noqa: E501

from .editblock_prompts import EditBlockPrompts


class EditorEditBlockPrompts(EditBlockPrompts):
    main_system = """Act as an expert software developer who edits source code.
{lazy_prompt}
Describe each change with a *SEARCH/REPLACE block* per the examples below.
All changes to files must use this *SEARCH/REPLACE block* format.
ONLY EVER RETURN CODE IN A *SEARCH/REPLACE BLOCK*!
"""

    shell_cmd_prompt = ""
    no_shell_cmd_prompt = ""
    shell_cmd_reminder = ""
