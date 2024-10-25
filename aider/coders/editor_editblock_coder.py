from typing import Optional, Dict, Any
from .editblock_coder import EditBlockCoder
from .editor_editblock_prompts import EditorEditBlockPrompts


class EditorEditBlockCoder(EditBlockCoder):
    edit_format: str = "editor-diff"
    gpt_prompts: EditorEditBlockPrompts = EditorEditBlockPrompts()

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize EditorEditBlockCoder with type checking"""
        super().__init__(*args, **kwargs)
        self._validate_prompts()

    def _validate_prompts(self) -> None:
        """Validate that prompts are properly initialized"""
        if not isinstance(self.gpt_prompts, EditorEditBlockPrompts):
            raise TypeError("gpt_prompts must be instance of EditorEditBlockPrompts")

    @property
    def edit_format_config(self) -> Dict[str, Any]:
        """Return edit format configuration"""
        return {
            "format": self.edit_format,
            "prompts": self.gpt_prompts
        }
