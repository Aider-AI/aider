# flake8: noqa: E501

from .editblock_fenced_prompts import EditBlockFencedPrompts


class EditorDiffFencedPrompts(EditBlockFencedPrompts):
    shell_cmd_prompt = ""
    no_shell_cmd_prompt = ""
    shell_cmd_reminder = ""
    go_ahead_tip = ""
    rename_with_shell = ""
