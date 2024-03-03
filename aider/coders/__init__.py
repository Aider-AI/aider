import os
from .prompt_manager import PromptManager

prompt_file_path = os.path.expanduser('~/.aiderprompts.yaml')
prompt_manager = PromptManager(prompt_file_path)

from .base_coder import Coder
from .editblock_coder import EditBlockCoder
from .editblock_func_coder import EditBlockFunctionCoder
from .single_wholefile_func_coder import SingleWholeFileFunctionCoder
from .udiff_coder import UnifiedDiffCoder
from .wholefile_coder import WholeFileCoder
from .wholefile_func_coder import WholeFileFunctionCoder

__all__ = [
    Coder,
    EditBlockCoder,
    WholeFileCoder,
    WholeFileFunctionCoder,
    EditBlockFunctionCoder,
    SingleWholeFileFunctionCoder,
    UnifiedDiffCoder,
    prompt_manager,
]
