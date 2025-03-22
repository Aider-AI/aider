from .editor_editblock_coder import EditBlockCoder
from .general_editor_editblock_prompts import GeneralEditorEditBlockPrompts


class GeneralEditorEditBlockCoder(EditorEditBlockCoder):
    """A coder that uses search/replace blocks, focused purely on editing general documents."""

    edit_format = "general-editor-diff"
    gpt_prompts = GeneralEditorEditBlockPrompts()
