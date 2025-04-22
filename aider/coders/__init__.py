from .architect_coder import ArchitectCoder
from .ask_coder import AskCoder
from .base_coder import Coder
from .context_coder import ContextCoder
from .editblock_coder import EditBlockCoder
from .editblock_fenced_coder import EditBlockFencedCoder
from .editor_diff_fenced_coder import EditorDiffFencedCoder
from .editor_editblock_coder import EditorEditBlockCoder
from .editor_whole_coder import EditorWholeFileCoder
from .help_coder import HelpCoder
from .patch_coder import PatchCoder
from .udiff_coder import UnifiedDiffCoder
from .udiff_simple import UnifiedDiffSimpleCoder
from .wholefile_coder import WholeFileCoder

# from .single_wholefile_func_coder import SingleWholeFileFunctionCoder

__all__ = [
    HelpCoder,
    AskCoder,
    Coder,
    EditBlockCoder,
    EditBlockFencedCoder,
    WholeFileCoder,
    PatchCoder,
    UnifiedDiffCoder,
    UnifiedDiffSimpleCoder,
    #    SingleWholeFileFunctionCoder,
    ArchitectCoder,
    EditorEditBlockCoder,
    EditorWholeFileCoder,
    EditorDiffFencedCoder,
    ContextCoder,
]
