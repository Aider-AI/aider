from .editblock_fenced_coder import EditBlockFencedCoder
from .editor_diff_fenced_prompts import EditorDiffFencedPrompts


class EditorDiffFencedCoder(EditBlockFencedCoder):
    "A coder that uses search/replace blocks, focused purely on editing files."

    edit_format = "editor-diff-fenced"
    gpt_prompts = EditorDiffFencedPrompts()
