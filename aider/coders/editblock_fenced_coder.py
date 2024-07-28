from ..dump import dump  # noqa: F401
from .editblock_coder import EditBlockCoder
from .editblock_fenced_prompts import EditBlockFencedPrompts


class EditBlockFencedCoder(EditBlockCoder):
    """A coder that uses fenced search/replace blocks for code modifications."""
    edit_format = "diff-fenced"
    gpt_prompts = EditBlockFencedPrompts()
