from .base_coder import Coder
from aider import prompts


class AutoApproveCoder(Coder):
    # This AutoApproveCoder auto approves to complete task.
    # Overload check_for_file_mentions to auto approve files.

    def run(self, with_message=None, preproc=True):
        try:
            if with_message:
                self.io.user_input(with_message)
                self.run_one(with_message, preproc)
                return self.partial_response_content
            while True:
                try:
                    if not self.io.placeholder:
                        self.copy_context()
                    user_message = self.get_input()
                    self.run_one(user_message, preproc)
                    self.show_undo_hint()
                except KeyboardInterrupt:
                    self.keyboard_interrupt()
        except EOFError:
            return
        
    def check_for_file_mentions(self, content):
        mentioned_rel_fnames = self.get_file_mentions(content)

        new_mentions = mentioned_rel_fnames - self.ignore_mentions

        if not new_mentions:
            return

        added_fnames = []
        for rel_fname in sorted(new_mentions):
            self.io.print(f"=====Adding file: {rel_fname}")
            self.add_rel_fname(rel_fname)
            added_fnames.append(rel_fname)

        if added_fnames:
            return prompts.added_files.format(fnames=", ".join(added_fnames))
