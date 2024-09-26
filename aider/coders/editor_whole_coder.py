from .editor_whole_prompts import EditorWholeFilePrompts
from .wholefile_coder import WholeFileCoder


class EditorWholeFileCoder(WholeFileCoder):
    edit_format = "editor-whole"
    gpt_prompts = EditorWholeFilePrompts()
