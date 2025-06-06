from .context_coder import ContextCoder
from .auto_prompts import AutoPrompts
import re
from pathlib import Path


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

        # Enhanced context finding settings
        self.deep_context_search = kwargs.get('deep_context_search', True)
        self.min_identifier_length = kwargs.get('min_identifier_length', 3)  # Shorter than default (5)

        # Increase repo map tokens for better context
        if self.repo_map:
            self.repo_map.max_map_tokens *= 1.5  # Increase token allocation for repo map
            self.repo_map.refresh = "always"  # Always refresh the repo map

    def get_enhanced_file_mentions(self, content):
        """Enhanced method to find file mentions in content with better heuristics."""
        # Get standard file mentions
        standard_mentions = self.get_file_mentions(content, ignore_current=True)

        # Get identifiers that might be related to files
        identifiers = self.get_ident_mentions(content)

        # Use a lower threshold for identifier length
        all_fnames = {}
        for fname in self.get_all_relative_files():
            if not fname or fname == ".":
                continue

            try:
                path = Path(fname)

                # Add the file's stem (name without extension)
                base = path.stem.lower()
                if len(base) >= self.min_identifier_length:
                    if base not in all_fnames:
                        all_fnames[base] = set()
                    all_fnames[base].add(fname)

                # Add the file's parent directory name
                if path.parent.name:
                    parent = path.parent.name.lower()
                    if len(parent) >= self.min_identifier_length:
                        if parent not in all_fnames:
                            all_fnames[parent] = set()
                        all_fnames[parent].add(fname)

                # Add the full path components
                parts = [p.lower() for p in path.parts if p and len(p) >= self.min_identifier_length]
                for part in parts:
                    if part not in all_fnames:
                        all_fnames[part] = set()
                    all_fnames[part].add(fname)
            except ValueError:
                continue

        # Match identifiers to files
        identifier_matches = set()
        for ident in identifiers:
            ident_lower = ident.lower()
            if len(ident_lower) >= self.min_identifier_length and ident_lower in all_fnames:
                identifier_matches.update(all_fnames[ident_lower])

        # Look for import statements and package references
        import_pattern = re.compile(r'(?:import|from|require|include)\s+([a-zA-Z0-9_.]+)')
        imports = import_pattern.findall(content)

        import_matches = set()
        for imp in imports:
            parts = imp.split('.')
            for i in range(len(parts)):
                partial = '.'.join(parts[:i+1])
                partial_lower = partial.lower()
                if partial_lower in all_fnames:
                    import_matches.update(all_fnames[partial_lower])

                # Also check for file extensions
                for ext in ['.py', '.js', '.ts', '.java', '.c', '.cpp', '.h', '.hpp']:
                    with_ext = partial + ext
                    with_ext_lower = with_ext.lower()
                    if with_ext_lower in all_fnames:
                        import_matches.update(all_fnames[with_ext_lower])

        # Combine all matches
        all_matches = standard_mentions | identifier_matches | import_matches

        return all_matches

    def reply_completed(self):
        # First use ContextCoder's functionality to identify relevant files
        content = self.partial_response_content
        if not content or not content.strip():
            return True

        # Get files mentioned in the response using enhanced methods
        current_rel_fnames = set(self.get_inchat_relative_files())

        if self.deep_context_search:
            mentioned_rel_fnames = self.get_enhanced_file_mentions(content)
        else:
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
