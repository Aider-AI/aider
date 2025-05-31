import re
import os
from .architect_prompts import ArchitectPrompts, ArchitectBatchEditingPrompts
from .ask_coder import AskCoder
from .base_coder import Coder


class ArchitectCoder(AskCoder):
    edit_format = "architect"
    gpt_prompts = ArchitectPrompts()
    auto_accept_architect = False
    use_batch_editing = False

    def __init__(self, main_model, io, use_batch_editing=False,
                 auto_accept_architect=None, **kwargs):
        super().__init__(main_model, io, **kwargs)
        if auto_accept_architect is not None:
            self.auto_accept_architect = auto_accept_architect
        self.use_batch_editing = use_batch_editing

        # Use the appropriate prompt class based on batch editing mode
        if use_batch_editing:
            self.gpt_prompts = ArchitectBatchEditingPrompts()
        else:
            self.gpt_prompts = ArchitectPrompts()

    def reply_completed(self):
        content = self.partial_response_content

        if not content or not content.strip():
            return

        if not self.auto_accept_architect and not self.io.confirm_ask("Edit the files?"):
            return

        kwargs = dict()

        # Use the editor_model from the main_model if it exists, otherwise use the main_model itself
        editor_model = self.main_model.editor_model or self.main_model

        kwargs["main_model"] = editor_model
        kwargs["edit_format"] = self.main_model.editor_edit_format
        # Configure settings based on batch mode
        if self.use_batch_editing:
            # In batch mode, enable full features for each separate session
            kwargs["suggest_shell_commands"] = True
            kwargs["map_tokens"] = 1024  # Enable repo mapping for batch sessions
            kwargs["cache_prompts"] = True
            # Disable auto-linting/testing for individual chunks since partial changes
            # may have false positives (e.g., calling functions not yet defined)
            kwargs["auto_lint"] = False
            kwargs["auto_test"] = False
        else:
            # In normal architect mode, use original settings (match main branch exactly)
            kwargs["suggest_shell_commands"] = False
            kwargs["map_tokens"] = 0
            kwargs["cache_prompts"] = False
            # Don't set auto_lint or auto_test to preserve original behavior
        kwargs["total_cost"] = self.total_cost
        kwargs["num_cache_warming_pings"] = 0
        kwargs["summarize_from_coder"] = False

        if self.use_batch_editing:
            # For batch editing, create minimal context sessions to avoid context limits
            # Don't pass from_coder to avoid inheriting full chat history and context
            new_kwargs = dict(io=self.io)
            new_kwargs.update(kwargs)
        else:
            # For normal architect mode, use the full context
            new_kwargs = dict(io=self.io, from_coder=self)
            new_kwargs.update(kwargs)

        if self.use_batch_editing:
            # split the architect model response into chunks using natural delimiters
            chat_files = (list(self.abs_fnames)
                          if hasattr(self, 'abs_fnames') and self.abs_fnames
                          else None)
            chunks = self.split_response_by_natural_delimiters(content,
                                                               chat_files=chat_files)

            # Set flag to indicate we're in batch editing mode to skip auto file detection
            self._in_batch_editing_mode = True

            try:
                # Store original auto-lint and auto-test settings to restore later
                original_auto_lint = getattr(self, 'auto_lint', False)
                original_auto_test = getattr(self, 'auto_test', False)
                batch_edited_files = set()

                # Add progress feedback for batch processing
                if chunks:
                    self.io.tool_output(
                        f"\nProcessing {len(chunks)} editing tasks separately to avoid "
                        f"context limits",
                        bold=True
                    )
                    self.io.tool_output(
                        "Note: Auto-linting and auto-testing disabled for individual chunks "
                        "to avoid false positives from partial changes"
                    )

                for i, chunk in enumerate(chunks, 1):
                    if not chunk.strip():
                        continue

                    # Basic validation - only skip chunks that are really too short
                    # (less than 4 lines)
                    chunk_lines = chunk.strip().split('\n')
                    if len(chunk_lines) < 4:
                        self.io.tool_warning(
                            f"Batch edit request {i} of {len(chunks)} seems too short "
                            f"(less than 4 lines), skipping"
                        )
                        continue

                    # Show progress for current task
                    self.io.tool_output(
                        f"→ Batch edit request {i} of {len(chunks)} sent to model "
                        f"{editor_model.name}"
                    )

                    # Extract filenames from chunk to determine minimal context needed
                    chunk_files = self.extract_filenames_from_chunk(chunk, chat_files)
                    if self.verbose and chunk_files:
                        self.io.tool_output(f"Debug: Chunk files extracted: {chunk_files}")
                    relevant_files = self._match_chunk_files_to_abs_files(chunk_files)

                    # Create minimal context kwargs for this specific chunk
                    chunk_kwargs = new_kwargs.copy()

                    # Create a new chat session with the editor coder llm model for each chunk
                    # of the architect model response
                    editor_coder = Coder.create(**chunk_kwargs)
                    editor_coder.cur_messages = []
                    editor_coder.done_messages = []

                    # Pass the batch editing mode flag to the editor coder
                    editor_coder._in_batch_editing_mode = True

                    # Set minimal file context for this chunk only
                    if relevant_files:
                        editor_coder.abs_fnames = set(relevant_files)
                        if self.verbose:
                            self.io.tool_output(f"Processing files: {', '.join(relevant_files)}")
                    else:
                        editor_coder.abs_fnames = set()
                        if self.verbose:
                            self.io.tool_output("Processing chunk without specific file context")

                    if self.verbose:
                        editor_coder.show_announcements()

                    # Pass the chunk as-is to editor (same as normal architect mode)
                    # Add safety mechanism to prevent infinite loops
                    max_attempts = 3
                    attempt = 0
                    success = False

                    while attempt < max_attempts and not success:
                        attempt += 1
                        try:
                            if self.verbose and attempt > 1:
                                self.io.tool_output(
                                    f"Retry attempt {attempt}/{max_attempts} for batch edit "
                                    f"request {i} of {len(chunks)}"
                                )

                            editor_coder.run(with_message=chunk, preproc=False)
                            success = True
                            self.io.tool_output(
                                f"✓ Batch edit answer {i} of {len(chunks)} received from "
                                f"{editor_model.name}"
                            )

                        except Exception as chunk_error:
                            self.io.tool_error(
                                f"Attempt {attempt} failed for batch edit request {i} of {len(chunks)}: "
                                f"{str(chunk_error)}"
                            )
                            if attempt >= max_attempts:
                                self.io.tool_error(
                                    f"Batch edit request {i} of {len(chunks)} failed after "
                                    f"{max_attempts} attempts, skipping"
                                )
                                break

                    if not success and not self.io.confirm_ask("Continue with remaining batch edit requests?"):
                        break

                    self.move_back_cur_messages("I made those changes to the files.")
                    self.total_cost += editor_coder.total_cost
                    if self.aider_commit_hashes is None:
                        self.aider_commit_hashes = set()
                    self.aider_commit_hashes.update(editor_coder.aider_commit_hashes or set())

                    # Track files edited during batch processing
                    if hasattr(editor_coder, 'aider_edited_files'):
                        batch_edited_files.update(editor_coder.aider_edited_files)

                # After all chunks processed, run final linting and testing if originally enabled
                if batch_edited_files and (original_auto_lint or original_auto_test):
                    self.io.tool_output(f"\nRunning final validation on {len(batch_edited_files)} modified files...")

                    if original_auto_lint and hasattr(self, 'lint_edited'):
                        lint_errors = self.lint_edited(batch_edited_files)
                        if hasattr(self, 'auto_commit'):
                            self.auto_commit(batch_edited_files, context="Ran final linting after batch processing")
                        self.lint_outcome = not lint_errors
                        if lint_errors:
                            ok = self.io.confirm_ask("Attempt to fix lint errors found after batch processing?")
                            if ok:
                                self.reflected_message = lint_errors
                                return

                    if original_auto_test and hasattr(self, 'commands') and hasattr(self, 'test_cmd') and self.test_cmd:
                        test_errors = self.commands.cmd_test(self.test_cmd)
                        self.test_outcome = not test_errors
                        if test_errors:
                            ok = self.io.confirm_ask("Attempt to fix test errors found after batch processing?")
                            if ok:
                                self.reflected_message = test_errors
                                return

                # Provide final status message
                if chunks and not batch_edited_files:
                    self.io.tool_output("\nBatch processing completed (no files were modified)", bold=True)
                elif chunks:
                    self.io.tool_output("\nBatch processing completed successfully!", bold=True)

            finally:
                # Clear batch editing mode flag
                self._in_batch_editing_mode = False
        else:
            # Create only one chat session with the editor coder llm model, not splitting the architect answer in chunks.
            # Ensure batch editing mode flag is false for non-batch processing
            self._in_batch_editing_mode = False

            editor_coder = Coder.create(**new_kwargs)
            editor_coder.cur_messages = []
            editor_coder.done_messages = []

            # Pass the batch editing mode flag to the editor coder
            editor_coder._in_batch_editing_mode = False

            if self.verbose:
                editor_coder.show_announcements()

            # Run the editor coder with the entire architect model response
            editor_coder.run(with_message=content, preproc=False)

            self.move_back_cur_messages("I made those changes to the files.")
            self.total_cost = editor_coder.total_cost
            self.aider_commit_hashes = editor_coder.aider_commit_hashes

    def split_response_by_natural_delimiters(self, content, chat_files=None) -> list:
        """
        Split the response into chunks for batch processing.

        In batch editing mode, splits on BATCH_EDIT_SEPARATOR.
        Otherwise falls back to treating the entire content as one chunk.
        """
        # First, try separator-based splitting for batch editing mode
        separator = "---BATCH_EDIT_SEPARATOR---"
        if separator in content:
            # Split on the separator and return non-empty chunks
            chunks = [chunk.strip() for chunk in content.split(separator) if chunk.strip()]
            return chunks

        # Fall back to treating the entire content as one chunk if no separators
        return [content.strip()] if content.strip() else []

    def extract_filenames_from_chunk(self, chunk, chat_files=None):
        """
        Extract filenames mentioned in a chunk to determine which files this chunk needs access to.
        For the new batch format, looks for **filename** at the start of chunks.
        Returns a list of filenames found in the chunk.
        """
        found_files = set()

        # Look for the new batch format: **filename** at the start of lines
        # More comprehensive pattern for valid filename characters
        batch_format_pattern = r'^\*\*([a-zA-Z0-9_\-./\\@+~]+\.[a-zA-Z0-9]+)\*\*'
        matches = re.findall(batch_format_pattern, chunk, re.MULTILINE)

        for filename in matches:
            filename = filename.strip()
            if filename and len(filename) < 250:  # Reasonable filename length
                # If chat_files provided, match against known files
                if chat_files:
                    # Try exact match first
                    if filename in chat_files:
                        found_files.add(filename)
                    else:
                        # Check if any chat_file matches this filename
                        for chat_file in chat_files:
                            if (os.path.basename(chat_file) == filename
                                    or chat_file.endswith(f"/{filename}")
                                    or chat_file == filename):
                                found_files.add(chat_file)
                                break
                else:
                    found_files.add(filename)

        return list(found_files)

    def _match_chunk_files_to_abs_files(self, chunk_files):
        """Helper method to match chunk filenames to absolute file paths."""
        relevant_files = []
        if chunk_files and hasattr(self, 'abs_fnames'):
            # Only include files mentioned in this specific chunk
            for filename in chunk_files:
                # Try both exact match and basename match
                matched = False
                for abs_fname in self.abs_fnames:
                    if filename == abs_fname or filename == os.path.basename(abs_fname):
                        relevant_files.append(abs_fname)
                        matched = True
                        break
                if not matched:
                    # Try relative path match - remove leading ./ if present
                    clean_filename = filename.lstrip('./')
                    for abs_fname in self.abs_fnames:
                        if abs_fname.endswith(clean_filename):
                            relevant_files.append(abs_fname)
                            break
        return relevant_files
