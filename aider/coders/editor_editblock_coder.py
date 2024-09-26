from .editblock_coder import EditBlockCoder
from .editor_editblock_prompts import EditorEditBlockPrompts


class EditorEditBlockCoder(EditBlockCoder):
    edit_format = "editor-diff"
    gpt_prompts = EditorEditBlockPrompts()
