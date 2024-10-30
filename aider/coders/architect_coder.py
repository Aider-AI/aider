from .architect_prompts import ArchitectPrompts
from .ask_coder import AskCoder
from .base_coder import Coder
from functools import lru_cache
from typing import Dict, Optional

class ArchitectCoder(AskCoder):
    edit_format = "architect"
    gpt_prompts = ArchitectPrompts()

    @lru_cache(maxsize=128)
    def _get_editor_model(self) -> object:
        """Cache and return editor model to avoid repeated lookups"""
        return self.main_model.editor_model or self.main_model
    
    def reply_completed(self):
        content = self.partial_response_content

        if not self.io.confirm_ask("Edit the files?"):
            return

        kwargs: Dict[str, any] = {
            "main_model": self._get_editor_model(),
            "edit_format": self.main_model.editor_edit_format,
            "suggest_shell_commands": False,
            "map_tokens": 0, 
            "total_cost": self.total_cost,
            "cache_prompts": False,
            "num_cache_warming_pings": 0,
            "summarize_from_coder": False
        }

        editor_coder = self._create_editor_coder(kwargs)
        self._run_editor_coder(editor_coder, content)
        self._update_state(editor_coder)

    def _create_editor_coder(self, kwargs: Dict[str, any]) -> Optional['Coder']:
        """Create and initialize editor coder instance"""
        new_kwargs = {"io": self.io, "from_coder": self, **kwargs}
        editor_coder = Coder.create(**new_kwargs)
        editor_coder.cur_messages = []
        editor_coder.done_messages = []
        return editor_coder

    def _run_editor_coder(self, editor_coder: 'Coder', content: str) -> None:
        """Run the editor coder with content"""
        if self.verbose:
            editor_coder.show_announcements()
        editor_coder.run(with_message=content, preproc=False)

    def _update_state(self, editor_coder: 'Coder') -> None:
        """Update state after editor coder run"""
        self.move_back_cur_messages("I made those changes to the files.")
        self.total_cost = editor_coder.total_cost
        self.aider_commit_hashes = editor_coder.aider_commit_hashes
