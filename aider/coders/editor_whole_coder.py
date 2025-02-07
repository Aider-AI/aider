from .editor_whole_prompts import EditorWholeFilePrompts
from .wholefile_coder import WholeFileCoder


class EditorWholeFileCoder(WholeFileCoder):
    "A coder that operates on entire files, focused purely on editing files."
    edit_format = "editor-whole"
    gpt_prompts = EditorWholeFilePrompts()
