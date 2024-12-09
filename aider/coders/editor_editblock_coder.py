from .editblock_coder import EditBlockCoder
from .editor_editblock_prompts import EditorEditBlockPrompts


class EditorEditBlockCoder(EditBlockCoder):
    "A coder that uses search/replace blocks, focused purely on editing files."
    edit_format = "editor-diff"
    gpt_prompts = EditorEditBlockPrompts()
