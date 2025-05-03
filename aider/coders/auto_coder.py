from .context_coder import ContextCoder
from .auto_prompts import AutoPrompts


class AutoCoder(ContextCoder):
    """Automatically identify files and make changes without confirmation."""

    edit_format = "auto"
    gpt_prompts = AutoPrompts()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set yes_to_all to bypass confirmations
        self.io.yes = True
        
        # Ensure auto_accept_architect is True
        self.auto_accept_architect = True
        
        # Enable auto-linting and auto-testing if configured
        self.auto_lint = kwargs.get('auto_lint', True)
        self.auto_test = kwargs.get('auto_test', False)

    def reply_completed(self):
        # First use ContextCoder's functionality to identify relevant files
        content = self.partial_response_content
        if not content or not content.strip():
            return True

        # Get files mentioned in the response
        current_rel_fnames = set(self.get_inchat_relative_files())
        mentioned_rel_fnames = set(self.get_file_mentions(content, ignore_current=True))

        # If the files are different, automatically add the mentioned files
        if mentioned_rel_fnames != current_rel_fnames:
            self.abs_fnames = set()
            for fname in mentioned_rel_fnames:
                self.add_rel_fname(fname)
            
            # Now that we've added the files, we need to get the content again
            # and apply the changes automatically
            self.io.tool_output(f"Automatically added files: {', '.join(mentioned_rel_fnames)}")
            
            # Refresh the repository map if needed
            if self.repo_map:
                self.get_repo_map(force_refresh=True)
            
            # Create a new message to apply the changes
            self.reflected_message = "I've identified the relevant files. Now I'll make the requested changes."
            return False
        
        # If we already have all the files, apply the changes
        edited = self.apply_updates()
        
        if edited:
            self.io.tool_output(f"Automatically applied changes to: {', '.join(edited)}")
            self.aider_edited_files.update(edited)
            saved_message = self.auto_commit(edited)
            
            if saved_message:
                self.move_back_cur_messages(saved_message)
            
            # Run linting if enabled
            if self.auto_lint:
                lint_errors = self.lint_edited(edited)
                if lint_errors:
                    self.io.tool_output("Linting found errors. Attempting to fix...")
                    self.reflected_message = lint_errors
                    return False
            
            # Run tests if enabled
            if self.auto_test:
                test_output = self.run_tests()
                if test_output:
                    self.io.tool_output(f"Test results: {test_output}")
        
        return True
