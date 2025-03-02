from aider.aider.coders.base_coder_auto_approve import AutoApproveCoder
from .architect_prompts import ArchitectPrompts
from .base_coder import Coder


class GameArchitectCoder(AutoApproveCoder):
    edit_format = "garchitect"
    gpt_prompts = ArchitectPrompts()

    def reply_completed(self):
        content = self.partial_response_content

        if not content or not content.strip():
            return

        if not self.io.confirm_ask("Edit the files?"):
            return

        kwargs = dict()

        # Use the editor_model from the main_model if it exists, otherwise use the main_model itself
        editor_model = self.main_model.editor_model or self.main_model

        kwargs["main_model"] = editor_model
        kwargs["edit_format"] = self.main_model.editor_edit_format
        kwargs["suggest_shell_commands"] = False
        kwargs["map_tokens"] = 0
        kwargs["total_cost"] = self.total_cost
        kwargs["cache_prompts"] = False
        kwargs["num_cache_warming_pings"] = 0
        kwargs["summarize_from_coder"] = False

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


    def review_changes(self):
        content = self.partial_response_content

        if not content or not content.strip():
            return

        kwargs = dict()
        kwargs["main_model"] = self.main_model
        kwargs["edit_format"] = 'review'
        kwargs["suggest_shell_commands"] = False
        kwargs["map_tokens"] = 0
        kwargs["total_cost"] = self.total_cost
        kwargs["cache_prompts"] = False
        kwargs["num_cache_warming_pings"] = 0
        kwargs["summarize_from_coder"] = False
        kwargs["fnames"] = self.abs_fnames


        new_kwargs = dict(io=self.io)
        new_kwargs.update(kwargs)

        editor_coder = Coder.create(**new_kwargs)
        editor_coder.cur_messages = []
        editor_coder.done_messages = []

        if self.verbose:
            editor_coder.show_announcements()

        editor_coder.run(with_message=content, preproc=False)

        self.move_back_cur_messages("I reviewed those changes to the files.")
        self.total_cost = editor_coder.total_cost

        if "LGTM!" not in editor_coder.partial_response_content:
            self.reflected_message = editor_coder.partial_response_content
            
        return