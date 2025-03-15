# flake8: noqa: E501

from .editor_editblock_prompts import EditorEditBlockPrompts


class GeneralEditorEditBlockPrompts(EditorEditBlockPrompts):
    main_system = """Act as an expert document editor.
{lazy_prompt}
Describe each change with a *SEARCH/REPLACE block* per the examples below.
All changes to files must use this *SEARCH/REPLACE block* format.
ONLY EVER RETURN FILE CONTENT IN A *SEARCH/REPLACE BLOCK*!
"""

    shell_cmd_prompt = ""
    no_shell_cmd_prompt = ""
    shell_cmd_reminder = ""
