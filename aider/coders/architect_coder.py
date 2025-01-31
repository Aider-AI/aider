from .architect_prompts import ArchitectPrompts
from .ask_coder import AskCoder
from .base_coder import Coder


class ArchitectCoder(AskCoder):
    edit_format = "architect"
    gpt_prompts = ArchitectPrompts()

    def reply_completed(self):
        content = self.partial_response_content

        if not content or not content.strip():
            return

        response = self.io.confirm_ask("Edit the files?", skip_chat_history=True, allow_tweak=True)
        if response == "tweak":
            content = self.io.edit_in_editor(content)
            # Now that content has been tweaked, append the edit decision to chat history
            self.io.append_chat_history("> Edit the files? (Y)es/(T)weak/(N)o [Yes]: \n", blockquote=True)
        elif not response:
            return
        else:
            # For yes/no responses, append to chat history
            self.io.append_chat_history("> Edit the files? (Y)es/(T)weak/(N)o [Yes]: \n", blockquote=True)

        kwargs = dict()

        # Use the editor_model from the main_model if it exists, otherwise use the main_model itself
        editor_model = self.main_model.editor_model or self.main_model

        kwargs = {
            "main_model": editor_model,
            "edit_format": self.main_model.editor_edit_format,
            "suggest_shell_commands": False,
            "map_tokens": 0,
            "total_cost": self.total_cost,
            "cache_prompts": False,
            "num_cache_warming_pings": 0,
            "summarize_from_coder": False
        }

        new_kwargs = dict(io=self.io, from_coder=self)
        new_kwargs.update(kwargs)

        editor_coder = Coder.create(**new_kwargs)
        editor_coder.cur_messages = []
        editor_coder.done_messages = []

        if self.verbose:
            editor_coder.show_announcements()

        editor_coder.run(with_message=content, preproc=False)

        self.move_back_cur_messages("I made those changes to the files.")
        self.total_cost = editor_coder.total_cost
        self.aider_commit_hashes = editor_coder.aider_commit_hashes
