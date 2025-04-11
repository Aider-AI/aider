import re
import fnmatch
import os
import time
import random
import subprocess
import traceback
from pathlib import Path
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import ParseError

from .base_coder import Coder
from .editblock_coder import find_original_update_blocks, do_replace, find_similar_lines
from .navigator_prompts import NavigatorPrompts
from aider.repo import ANY_GIT_ERROR
from aider import urls
# Import run_cmd_subprocess directly for non-interactive execution
from aider.run_cmd import run_cmd_subprocess

class NavigatorCoder(Coder):
    """Mode where the LLM autonomously manages which files are in context."""
    
    edit_format = "navigator"
    gpt_prompts = NavigatorPrompts()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Dictionary to track recently removed files
        self.recently_removed = {}
        
        # Configuration parameters
        self.max_tool_calls = 100          # Maximum number of tool calls per response
        
        # Context management parameters
        self.large_file_token_threshold = 25000  # Files larger than this in tokens are considered large
        self.max_files_per_glob = 50             # Maximum number of files to add at once via glob/grep
        
        # Enable context management by default only in navigator mode
        self.context_management_enabled = True   # Enabled by default for navigator mode
        
        
        # Track files added during current exploration
        self.files_added_in_exploration = set()
        
        # Counter for tool calls
        self.tool_call_count = 0
        
        # Set high max reflections to allow many exploration rounds
        # This controls how many automatic iterations the LLM can do
        self.max_reflections = 15
        
        # Enable enhanced context blocks by default
        self.use_enhanced_context = True

    def format_chat_chunks(self):
        """
        Override parent's format_chat_chunks to include enhanced context blocks.
        """
        # First get the normal chat chunks from the parent method
        chunks = super().format_chat_chunks()
        
        # If enhanced context blocks are enabled, prepend them to the current messages
        if self.use_enhanced_context:
            # Create an enhanced context message if we have the directory structure or git status
            context_blocks = []
            
            # Get directory structure
            dir_structure = self.get_directory_structure()
            if dir_structure:
                context_blocks.append(dir_structure)
            
            # Get git status
            git_status = self.get_git_status()
            if git_status:
                context_blocks.append(git_status)
            
            # If we have any context blocks, prepend them to the current messages
            if context_blocks:
                context_message = "\n\n".join(context_blocks)
                # Prepend to system context but don't overwrite existing system content
                if chunks.system:
                    # If we already have system messages, append our context to the first one
                    original_content = chunks.system[0]["content"]
                    chunks.system[0]["content"] = context_message + "\n\n" + original_content
                else:
                    # Otherwise, create a new system message
                    chunks.system = [dict(role="system", content=context_message)]
                    
        return chunks
        
    def reply_completed(self):
        """Process the completed response from the LLM.
        
        This is a key method that:
        1. Processes any tool commands in the response
        2. If tool commands were found, sets up for another automatic round
        3. Otherwise, completes the response normally
        
        This enables the "auto-exploration" workflow where the LLM can
        iteratively discover and analyze relevant files before providing
        a final answer to the user's question.
        """
        content = self.partial_response_content
        if not content or not content.strip():
            return True
        original_content = content # Keep the original response

        # Process tool commands: returns content with tool calls removed, results, and continue flag
        processed_content, result_messages, continue_requested = self._process_tool_commands(content)

        # Since we are no longer suppressing, the partial_response_content IS the final content.
        # We might want to update it to the processed_content (without tool calls) if we don't
        # want the raw tool calls to remain in the final assistant message history.
        # Let's update it for cleaner history.
        self.partial_response_content = processed_content.strip()

        # Process implicit file mentions using the content *after* tool calls were removed
        self._process_file_mentions(processed_content)

        # If continue was requested and we haven't exceeded reflection limits, set up for another iteration
        if continue_requested and self.num_reflections < self.max_reflections:
            # Reset tool counter for next iteration
            self.tool_call_count = 0
            # Clear exploration files for the next round
            self.files_added_in_exploration = set()
            
            # Get the original user question from the most recent user message
            if self.cur_messages and len(self.cur_messages) >= 1:
                for msg in reversed(self.cur_messages):
                    if msg["role"] == "user":
                        original_question = msg["content"]
                        break
                else:
                    # Default if no user message found
                    original_question = "Please continue your exploration and provide a final answer."
                
                # Construct the message for the next turn, including tool results
                next_prompt_parts = []
                next_prompt_parts.append(
                    "I have processed the results of the previous tool calls. "
                    "Let me analyze them and continue working towards your request."
                )

                if result_messages:
                    next_prompt_parts.append("\nResults from previous tool calls:")
                    # result_messages already have [Result (...): ...] format
                    next_prompt_parts.extend(result_messages)
                    next_prompt_parts.append("\nBased on these results and the updated file context, I will proceed.")
                else:
                    next_prompt_parts.append("\nNo specific results were returned from the previous tool calls, but the file context may have been updated. I will proceed based on the current context.")

                next_prompt_parts.append(f"\nYour original question was: {original_question}")

                self.reflected_message = "\n".join(next_prompt_parts)

                self.io.tool_output("Continuing exploration...")
                return False  # Indicate that we need another iteration
        else:
            # Exploration finished for this turn.
            # Append results to the content that will be stored in history.
            if result_messages:
                 results_block = "\n\n" + "\n".join(result_messages)
                 # Append results to the cleaned content
                 self.partial_response_content += results_block

            # Check if the content contains the SEARCH/REPLACE markers
            has_search = "<<<<<<< SEARCH" in self.partial_response_content
            has_divider = "=======" in self.partial_response_content
            has_replace = ">>>>>>> REPLACE" in self.partial_response_content
            edit_match = has_search and has_divider and has_replace

            if edit_match:
                self.io.tool_output("Detected edit blocks, applying changes within Navigator...")
                edited_files = self._apply_edits_from_response()
                # If _apply_edits_from_response set a reflected_message (due to errors),
                # return False to trigger a reflection loop.
                if self.reflected_message:
                    return False
            else:
                # No edits detected.
                pass

        # After applying edits OR determining no edits were needed (and no reflection needed),
        # the turn is complete. Reset counters and finalize history.
        self.tool_call_count = 0
        self.files_added_in_exploration = set()
        # Move cur_messages to done_messages
        self.move_back_cur_messages(None) # Pass None as we handled commit message earlier if needed
        return True # Indicate exploration is finished for this round

    def _process_tool_commands(self, content):
        """
        Process tool commands in the `[tool_call(name, param=value)]` format within the content.
        """
        result_messages = []
        modified_content = content # Start with original content
        continue_requested = False
        call_count = 0
        max_calls = self.max_tool_calls

        # Regex to find tool calls: [tool_call(name, key=value, key="value", ...)]
        # It captures the tool name and the arguments string.
        # It handles quoted and unquoted values.
        tool_call_pattern = re.compile(
            r"\[tool_call\(\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*" # Tool name
            r"(?:,\s*(.*?))?\s*\)\]" # Optional arguments string (non-greedy)
        )

        # Regex to parse key=value pairs within the arguments string
        # Handles key=value, key="value", key='value'
        # Allows values to contain commas if quoted
        args_pattern = re.compile(
            r"([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*" # Key
            r"(?:\"(.*?)\"|\'(.*?)\'|([^,\s\'\"]*))" # Value (quoted or unquoted)
        )

        processed_indices = set() # Keep track of processed match ranges

        for match in tool_call_pattern.finditer(content):
            # Skip overlapping matches if a previous match already covered this area
            if any(match.start() >= start and match.end() <= end for start, end in processed_indices):
                continue

            call_count += 1
            if call_count > max_calls:
                self.io.tool_warning(f"Exceeded maximum tool calls ({max_calls}). Skipping remaining calls.")
                break

            tool_name = match.group(1)
            args_str = match.group(2) or ""
            full_match_str = match.group(0)

            # Handle Continue separately
            if tool_name.lower() == 'continue':
                continue_requested = True
                # Remove this specific call from the content
                modified_content = modified_content.replace(full_match_str, "", 1)
                processed_indices.add((match.start(), match.end()))
                continue # Don't process further, just note the request

            # Extract parameters
            params = {}
            suppressed_arg_values = ["..."] # Values to ignore during parsing
            try:
                for arg_match in args_pattern.finditer(args_str):
                    key = arg_match.group(1)
                    # Value can be in group 2 (double quotes), 3 (single quotes), or 4 (unquoted)
                    value = arg_match.group(2) or arg_match.group(3) or arg_match.group(4)

                    # Check if the value is suppressed
                    if value in suppressed_arg_values:
                        self.io.tool_warning(f"Skipping suppressed argument value '{value}' for key '{key}' in tool '{tool_name}'")
                        continue # Skip this argument

                    params[key] = value if value is not None else ""
            except Exception as e:
                 result_messages.append(f"[Result ({tool_name}): Error parsing arguments '{args_str}': {e}]")
                 # Remove the malformed call from the content
                 modified_content = modified_content.replace(full_match_str, "", 1)
                 processed_indices.add((match.start(), match.end()))
                 continue # Skip execution if args parsing failed

            # Execute the tool based on its name
            result_message = None
            try:
                # Normalize tool name for case-insensitive matching
                norm_tool_name = tool_name.lower()

                if norm_tool_name == 'glob':
                    pattern = params.get('pattern')
                    if pattern is not None:
                        result_message = self._execute_glob(pattern)
                    else:
                        result_message = "Error: Missing 'pattern' parameter for Glob"
                elif norm_tool_name == 'grep':
                    pattern = params.get('pattern')
                    file_pattern = params.get('file_pattern') # Optional
                    if pattern is not None:
                        result_message = self._execute_grep(pattern, file_pattern)
                    else:
                        result_message = "Error: Missing 'pattern' parameter for Grep"
                elif norm_tool_name == 'ls':
                    directory = params.get('directory')
                    if directory is not None:
                        result_message = self._execute_ls(directory)
                    else:
                        result_message = "Error: Missing 'directory' parameter for Ls"
                elif norm_tool_name == 'add':
                    file_path = params.get('file_path')
                    if file_path is not None:
                        result_message = self._execute_add(file_path)
                    else:
                        result_message = "Error: Missing 'file_path' parameter for Add"
                elif norm_tool_name == 'remove':
                    file_path = params.get('file_path')
                    if file_path is not None:
                        result_message = self._execute_remove(file_path)
                    else:
                        result_message = "Error: Missing 'file_path' parameter for Remove"
                elif norm_tool_name == 'makeeditable':
                    file_path = params.get('file_path')
                    if file_path is not None:
                        result_message = self._execute_make_editable(file_path)
                    else:
                        result_message = "Error: Missing 'file_path' parameter for MakeEditable"
                elif norm_tool_name == 'makereadonly':
                    file_path = params.get('file_path')
                    if file_path is not None:
                        result_message = self._execute_make_readonly(file_path)
                    else:
                        result_message = "Error: Missing 'file_path' parameter for MakeReadonly"
                elif norm_tool_name == 'find':
                    symbol = params.get('symbol')
                    if symbol is not None:
                        result_message = self._execute_find(symbol)
                    else:
                        result_message = "Error: Missing 'symbol' parameter for Find"
                elif norm_tool_name == 'command':
                    command_string = params.get('command_string')
                    if command_string is not None:
                        result_message = self._execute_command(command_string)
                    else:
                        result_message = "Error: Missing 'command_string' parameter for Command"
                else:
                    result_message = f"Error: Unknown tool name '{tool_name}'"

            except Exception as e:
                result_message = f"Error executing {tool_name}: {str(e)}"
                self.io.tool_error(f"Error during {tool_name} execution: {e}")

            if result_message:
                result_messages.append(f"[Result ({tool_name}): {result_message}]")

            # Remove the processed tool call from the content
            modified_content = modified_content.replace(full_match_str, "", 1)
            processed_indices.add((match.start(), match.end()))

        # Update internal counter
        self.tool_call_count += call_count

        return modified_content, result_messages, continue_requested

    def _apply_edits_from_response(self):
        """
        Parses and applies SEARCH/REPLACE edits found in self.partial_response_content.
        Returns a set of relative file paths that were successfully edited.
        """
        edited_files = set()
        try:
            # 1. Get edits (logic from EditBlockCoder.get_edits)
            # Use the current partial_response_content which contains the LLM response
            # including the edit blocks but excluding the tool calls.
            edits = list(
                find_original_update_blocks(
                    self.partial_response_content,
                    self.fence,
                    self.get_inchat_relative_files(),
                )
            )
            # Separate shell commands from file edits
            self.shell_commands += [edit[1] for edit in edits if edit[0] is None]
            edits = [edit for edit in edits if edit[0] is not None]

            # 2. Prepare edits (check permissions, commit dirty files)
            prepared_edits = []
            seen_paths = dict()
            self.need_commit_before_edits = set() # Reset before checking

            for edit in edits:
                path = edit[0]
                if path in seen_paths:
                    allowed = seen_paths[path]
                else:
                    # Use the base Coder's permission check method
                    allowed = self.allowed_to_edit(path)
                    seen_paths[path] = allowed
                if allowed:
                    prepared_edits.append(edit)

            # Commit any dirty files identified by allowed_to_edit
            self.dirty_commit()
            self.need_commit_before_edits = set() # Clear after commit

            # 3. Apply edits (logic adapted from EditBlockCoder.apply_edits)
            failed = []
            passed = []
            for edit in prepared_edits:
                path, original, updated = edit
                full_path = self.abs_root_path(path)
                new_content = None

                if Path(full_path).exists():
                    content = self.io.read_text(full_path)
                    # Use the imported do_replace function
                    new_content = do_replace(full_path, content, original, updated, self.fence)

                # Simplified cross-file patching check from EditBlockCoder
                if not new_content and original.strip():
                     for other_full_path in self.abs_fnames:
                         if other_full_path == full_path: continue
                         other_content = self.io.read_text(other_full_path)
                         other_new_content = do_replace(other_full_path, other_content, original, updated, self.fence)
                         if other_new_content:
                             path = self.get_rel_fname(other_full_path)
                             full_path = other_full_path
                             new_content = other_new_content
                             self.io.tool_warning(f"Applied edit intended for {edit[0]} to {path}")
                             break

                if new_content:
                    if not self.dry_run:
                        self.io.write_text(full_path, new_content)
                        self.io.tool_output(f"Applied edit to {path}")
                    else:
                        self.io.tool_output(f"Did not apply edit to {path} (--dry-run)")
                    passed.append((path, original, updated)) # Store path relative to root
                else:
                    failed.append(edit)

            if failed:
                # Handle failed edits (adapted from EditBlockCoder)
                blocks = "block" if len(failed) == 1 else "blocks"
                error_message = f"# {len(failed)} SEARCH/REPLACE {blocks} failed to match!\n"
                for edit in failed:
                    path, original, updated = edit
                    full_path = self.abs_root_path(path)
                    content = self.io.read_text(full_path) # Read content again for context

                    error_message += f"""
## SearchReplaceNoExactMatch: This SEARCH block failed to exactly match lines in {path}
<<<<<<< SEARCH
{original}=======
{updated}>>>>>>> REPLACE

"""
                    did_you_mean = find_similar_lines(original, content)
                    if did_you_mean:
                        error_message += f"""Did you mean to match some of these actual lines from {path}?

{self.fence[0]}
{did_you_mean}
{self.fence[1]}

"""
                    if updated in content and updated:
                         error_message += f"""Are you sure you need this SEARCH/REPLACE block?
The REPLACE lines are already in {path}!

"""
                error_message += (
                    "The SEARCH section must exactly match an existing block of lines including all white"
                    " space, comments, indentation, docstrings, etc\n"
                )
                if passed:
                    pblocks = "block" if len(passed) == 1 else "blocks"
                    error_message += f"""
# The other {len(passed)} SEARCH/REPLACE {pblocks} were applied successfully.
Don't re-send them.
Just reply with fixed versions of the {blocks} above that failed to match.
"""
                self.io.tool_error(error_message)
                # Set reflected_message to prompt LLM to fix the failed blocks
                self.reflected_message = error_message

            edited_files = set(edit[0] for edit in passed) # Use relative paths stored in passed

            # 4. Post-edit actions (commit, lint, test, shell commands)
            if edited_files:
                self.aider_edited_files.update(edited_files) # Track edited files
                saved_message = self.auto_commit(edited_files)
                # We don't use saved_message here as we are not moving history back

                if self.auto_lint:
                     lint_errors = self.lint_edited(edited_files)
                     self.auto_commit(edited_files, context="Ran the linter")
                     if lint_errors and not self.reflected_message: # Reflect only if no edit errors
                         ok = self.io.confirm_ask("Attempt to fix lint errors?")
                         if ok:
                             self.reflected_message = lint_errors

                shared_output = self.run_shell_commands()
                if shared_output:
                     # Add shell output as a new user message? Or just display?
                     # Let's just display for now to avoid complex history manipulation
                     self.io.tool_output("Shell command output:\n" + shared_output)

                if self.auto_test and not self.reflected_message: # Reflect only if no prior errors
                     test_errors = self.commands.cmd_test(self.test_cmd)
                     if test_errors:
                         ok = self.io.confirm_ask("Attempt to fix test errors?")
                         if ok:
                             self.reflected_message = test_errors

            self.show_undo_hint()

        except ValueError as err:
            # Handle parsing errors from find_original_update_blocks
            self.num_malformed_responses += 1
            error_message = err.args[0]
            self.io.tool_error("The LLM did not conform to the edit format.")
            self.io.tool_output(urls.edit_errors)
            self.io.tool_output()
            self.io.tool_output(str(error_message))
            self.reflected_message = str(error_message) # Reflect parsing errors
        except ANY_GIT_ERROR as err:
            self.io.tool_error(f"Git error during edit application: {str(err)}")
            self.reflected_message = f"Git error during edit application: {str(err)}"
        except Exception as err:
            self.io.tool_error("Exception while applying edits:")
            self.io.tool_error(str(err), strip=False)
            traceback.print_exc()
            self.reflected_message = f"Exception while applying edits: {str(err)}"

        return edited_files

    def _execute_glob(self, pattern):
        """
        Execute a glob pattern and add matching files to context.
        
        This tool helps the LLM find files by pattern matching, similar to
        how a developer would use glob patterns to find files.
        """
        try:
            # Find files matching the pattern
            matching_files = []
            
            # Make the pattern relative to root if it's absolute
            if pattern.startswith('/'):
                pattern = os.path.relpath(pattern, self.root)
            
            # Get all files in the repo
            all_files = self.get_all_relative_files()
            
            # Find matches with pattern matching
            for file in all_files:
                if fnmatch.fnmatch(file, pattern):
                    matching_files.append(file)
            
            # Limit the number of files added if there are too many matches
            if len(matching_files) > self.max_files_per_glob:
                self.io.tool_output(
                    f"⚠️ Found {len(matching_files)} files matching '{pattern}', "
                    f"limiting to {self.max_files_per_glob} most relevant files."
                )
                # Sort by modification time (most recent first)
                matching_files.sort(key=lambda f: os.path.getmtime(self.abs_root_path(f)), reverse=True)
                matching_files = matching_files[:self.max_files_per_glob]
                
            # Add files to context
            for file in matching_files:
                self._add_file_to_context(file)
            
            # Return a user-friendly result
            if matching_files:
                if len(matching_files) > 10:
                    brief = ', '.join(matching_files[:5]) + f', and {len(matching_files)-5} more'
                    self.io.tool_output(f"📂 Added {len(matching_files)} files matching '{pattern}': {brief}")
                else:
                    self.io.tool_output(f"📂 Added files matching '{pattern}': {', '.join(matching_files)}")
                return f"Added {len(matching_files)} files: {', '.join(matching_files[:5])}{' and more' if len(matching_files) > 5 else ''}"
            else:
                self.io.tool_output(f"⚠️ No files found matching '{pattern}'")
                return f"No files found matching '{pattern}'"
        except Exception as e:
            self.io.tool_error(f"Error in glob: {str(e)}")
            return f"Error: {str(e)}"
    
    def _execute_grep(self, search_pattern, file_pattern=None):
        """
        Search for pattern in files and add matching files to context.
        
        This tool lets the LLM search for content within files, mimicking
        how a developer would use grep to find relevant code.
        """
        try:
            # Get list of files to search
            if file_pattern:
                # Use glob pattern to filter files
                all_files = self.get_all_relative_files()
                files_to_search = []
                for file in all_files:
                    if fnmatch.fnmatch(file, file_pattern):
                        files_to_search.append(file)
                        
                if not files_to_search:
                    return f"No files matching '{file_pattern}' to search for pattern '{search_pattern}'"
            else:
                # Search all files if no pattern provided
                files_to_search = self.get_all_relative_files()
            
            # Search for pattern in files
            matches = {}
            for file in files_to_search:
                abs_path = self.abs_root_path(file)
                try:
                    with open(abs_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if search_pattern in content:
                            matches[file] = content.count(search_pattern)
                except Exception:
                    # Skip files that can't be read (binary, etc.)
                    pass
                    
            # Limit the number of files added if there are too many matches
            if len(matches) > self.max_files_per_glob:
                self.io.tool_output(
                    f"⚠️ Found '{search_pattern}' in {len(matches)} files, "
                    f"limiting to {self.max_files_per_glob} files with most matches."
                )
                # Sort by number of matches (most matches first)
                sorted_matches = sorted(matches.items(), key=lambda x: x[1], reverse=True)
                matches = dict(sorted_matches[:self.max_files_per_glob])
                
            # Add matching files to context
            for file in matches:
                self._add_file_to_context(file)
            
            # Return a user-friendly result
            if matches:
                # Sort by number of matches (most matches first)
                sorted_matches = sorted(matches.items(), key=lambda x: x[1], reverse=True)
                match_list = [f"{file} ({count} matches)" for file, count in sorted_matches[:5]]
                
                if len(sorted_matches) > 5:
                    self.io.tool_output(f"🔍 Found '{search_pattern}' in {len(matches)} files: {', '.join(match_list)} and {len(matches)-5} more")
                    return f"Found in {len(matches)} files: {', '.join(match_list)} and {len(matches)-5} more"
                else:
                    self.io.tool_output(f"🔍 Found '{search_pattern}' in: {', '.join(match_list)}")
                    return f"Found in {len(matches)} files: {', '.join(match_list)}"
            else:
                self.io.tool_output(f"⚠️ Pattern '{search_pattern}' not found in any files")
                return f"Pattern not found in any files"
        except Exception as e:
            self.io.tool_error(f"Error in grep: {str(e)}")
            return f"Error: {str(e)}"
    
    def _execute_ls(self, dir_path):
        """
        List files in directory and optionally add some to context.
        
        This provides information about the structure of the codebase,
        similar to how a developer would explore directories.
        """
        try:
            # Make the path relative to root if it's absolute
            if dir_path.startswith('/'):
                rel_dir = os.path.relpath(dir_path, self.root)
            else:
                rel_dir = dir_path
            
            # Get absolute path
            abs_dir = self.abs_root_path(rel_dir)
            
            # Check if path exists
            if not os.path.exists(abs_dir):
                self.io.tool_output(f"⚠️ Directory '{dir_path}' not found")
                return f"Directory not found"
            
            # Get directory contents
            contents = []
            try:
                with os.scandir(abs_dir) as entries:
                    for entry in entries:
                        if entry.is_file() and not entry.name.startswith('.'):
                            rel_path = os.path.join(rel_dir, entry.name) 
                            contents.append(rel_path)
            except NotADirectoryError:
                # If it's a file, just return the file
                contents = [rel_dir]
                
            if contents:
                self.io.tool_output(f"📋 Listed {len(contents)} file(s) in '{dir_path}'")
                if len(contents) > 10:
                    return f"Found {len(contents)} files: {', '.join(contents[:10])}..."
                else:
                    return f"Found {len(contents)} files: {', '.join(contents)}"
            else:
                self.io.tool_output(f"📋 No files found in '{dir_path}'")
                return f"No files found in directory"
        except Exception as e:
            self.io.tool_error(f"Error in ls: {str(e)}")
            return f"Error: {str(e)}"
    
    def _execute_add(self, file_path):
        """
        Explicitly add a file to context as read-only.
        
        This gives the LLM explicit control over what files to add,
        rather than relying on indirect mentions.
        """
        try:
            return self._add_file_to_context(file_path, True)
        except Exception as e:
            self.io.tool_error(f"Error adding file: {str(e)}")
            return f"Error: {str(e)}"
    
    def _add_file_to_context(self, file_path, explicit=False):
        """
        Helper method to add a file to context as read-only.
        
        Parameters:
        - file_path: Path to the file to add
        - explicit: Whether this was an explicit add command (vs. implicit through glob/grep)
        """
        # Check if file exists
        abs_path = self.abs_root_path(file_path)
        rel_path = self.get_rel_fname(abs_path)
        
        if not os.path.isfile(abs_path):
            self.io.tool_output(f"⚠️ File '{file_path}' not found")
            return f"File not found"
        
        # Check if the file is already in context (either editable or read-only)
        if abs_path in self.abs_fnames:
            if explicit:
                self.io.tool_output(f"📎 File '{file_path}' already in context as editable")
                return f"File already in context as editable"
            return f"File already in context as editable"
            
        if abs_path in self.abs_read_only_fnames:
            if explicit:
                self.io.tool_output(f"📎 File '{file_path}' already in context as read-only")
                return f"File already in context as read-only"
            return f"File already in context as read-only"
        
        # Add file to context as read-only
        try:
            # Check for large file and apply context management if enabled
            content = self.io.read_text(abs_path)
            if content is None:
                return f"Error reading file: {file_path}"
            
            # Check if file is very large and context management is enabled
            if self.context_management_enabled:
                file_tokens = self.main_model.token_count(content)
                if file_tokens > self.large_file_token_threshold:
                    self.io.tool_output(
                        f"⚠️ '{file_path}' is very large ({file_tokens} tokens). "
                        "Use /context-management to toggle truncation off if needed."
                    )
                
            # Add to read-only files
            self.abs_read_only_fnames.add(abs_path)
            
            # Track in exploration set
            self.files_added_in_exploration.add(rel_path)
            
            # Inform user
            if explicit:
                self.io.tool_output(f"📎 Added '{file_path}' to context as read-only")
                return f"Added file to context as read-only"
            else:
                # For implicit adds (from glob/grep), just return success
                return f"Added file to context as read-only"
                
        except Exception as e:
            self.io.tool_error(f"Error adding file '{file_path}': {str(e)}")
            return f"Error adding file: {str(e)}"
            
    def _execute_make_editable(self, file_path):
        """
        Convert a read-only file to an editable file.
        
        This allows the LLM to upgrade a file from read-only to editable
        when it determines it needs to make changes to that file.
        """
        try:
            # Get absolute path
            abs_path = self.abs_root_path(file_path)
            rel_path = self.get_rel_fname(abs_path)
            
            # Check if file is in read-only context
            if abs_path not in self.abs_read_only_fnames:
                if abs_path in self.abs_fnames:
                    self.io.tool_output(f"📝 File '{file_path}' is already editable")
                    return f"File is already editable"
                else:
                    self.io.tool_output(f"⚠️ File '{file_path}' not in context")
                    return f"File not in context"
            
            # Move from read-only to editable
            self.abs_read_only_fnames.remove(abs_path)
            self.abs_fnames.add(abs_path)
            
            self.io.tool_output(f"📝 Made '{file_path}' editable")
            return f"File is now editable"
        except Exception as e:
            self.io.tool_error(f"Error making file editable: {str(e)}")
            return f"Error: {str(e)}"

    def _execute_make_readonly(self, file_path):
        """
        Convert an editable file to a read-only file.
        
        This allows the LLM to downgrade a file from editable to read-only
        when it determines it no longer needs to make changes to that file.
        """
        try:
            # Get absolute path
            abs_path = self.abs_root_path(file_path)
            rel_path = self.get_rel_fname(abs_path)
            
            # Check if file is in editable context
            if abs_path not in self.abs_fnames:
                if abs_path in self.abs_read_only_fnames:
                    self.io.tool_output(f"📚 File '{file_path}' is already read-only")
                    return f"File is already read-only"
                else:
                    self.io.tool_output(f"⚠️ File '{file_path}' not in context")
                    return f"File not in context"
            
            # Move from editable to read-only
            self.abs_fnames.remove(abs_path)
            self.abs_read_only_fnames.add(abs_path)
            
            self.io.tool_output(f"📚 Made '{file_path}' read-only")
            return f"File is now read-only"
        except Exception as e:
            self.io.tool_error(f"Error making file read-only: {str(e)}")
            return f"Error: {str(e)}"
    
    def _execute_remove(self, file_path):
        """
        Explicitly remove a file from context.
        
        This allows the LLM to clean up its context when files are no
        longer needed, keeping the context focused and efficient.
        """
        try:
            # Get absolute path
            abs_path = self.abs_root_path(file_path)
            rel_path = self.get_rel_fname(abs_path)

            # Check if file is in context (either editable or read-only)
            removed = False
            if abs_path in self.abs_fnames:
                # Don't remove if it's the last editable file and there are no read-only files
                if len(self.abs_fnames) <= 1 and not self.abs_read_only_fnames:
                     self.io.tool_output(f"⚠️ Cannot remove '{file_path}' - it's the only file in context")
                     return f"Cannot remove - last file in context"
                self.abs_fnames.remove(abs_path)
                removed = True
            elif abs_path in self.abs_read_only_fnames:
                # Don't remove if it's the last read-only file and there are no editable files
                if len(self.abs_read_only_fnames) <= 1 and not self.abs_fnames:
                     self.io.tool_output(f"⚠️ Cannot remove '{file_path}' - it's the only file in context")
                     return f"Cannot remove - last file in context"
                self.abs_read_only_fnames.remove(abs_path)
                removed = True

            if not removed:
                self.io.tool_output(f"⚠️ File '{file_path}' not in context")
                return f"File not in context"

            # Track in recently removed
            self.recently_removed[rel_path] = {
                'removed_at': time.time()
            }
            
            self.io.tool_output(f"🗑️ Explicitly removed '{file_path}' from context")
            return f"Removed file from context"
        except Exception as e:
            self.io.tool_error(f"Error removing file: {str(e)}")
            return f"Error: {str(e)}"

    def _execute_find(self, symbol):
        """
        Find files containing a specific symbol and add them to context as read-only.
        """
        try:
            if not self.repo_map:
                self.io.tool_output("⚠️ Repo map not available, cannot use Find tool.")
                return "Repo map not available"

            if not symbol:
                return "Error: Missing 'symbol' parameter for Find"

            self.io.tool_output(f"🔎 Searching for symbol '{symbol}'...")
            found_files = set()
            current_context_files = self.abs_fnames | self.abs_read_only_fnames
            files_to_search = set(self.get_all_abs_files()) - current_context_files

            rel_fname_to_abs = {}
            all_tags = []

            for fname in files_to_search:
                rel_fname = self.get_rel_fname(fname)
                rel_fname_to_abs[rel_fname] = fname
                try:
                    tags = self.repo_map.get_tags(fname, rel_fname)
                    all_tags.extend(tags)
                except Exception as e:
                    self.io.tool_warning(f"Could not get tags for {rel_fname}: {e}")

            # Find matching symbols
            for tag in all_tags:
                if tag.name == symbol:
                    # Use absolute path directly if available, otherwise resolve from relative path
                    abs_fname = rel_fname_to_abs.get(tag.rel_fname) or self.abs_root_path(tag.fname)
                    if abs_fname in files_to_search: # Ensure we only add files we intended to search
                        found_files.add(abs_fname)

            # Limit the number of files added
            if len(found_files) > self.max_files_per_glob:
                 self.io.tool_output(
                    f"⚠️ Found symbol '{symbol}' in {len(found_files)} files, "
                    f"limiting to {self.max_files_per_glob} most relevant files."
                )
                 # Sort by modification time (most recent first) - approximate relevance
                 sorted_found_files = sorted(list(found_files), key=lambda f: os.path.getmtime(f), reverse=True)
                 found_files = set(sorted_found_files[:self.max_files_per_glob])

            # Add files to context (as read-only)
            added_count = 0
            added_files_rel = []
            for abs_file_path in found_files:
                rel_path = self.get_rel_fname(abs_file_path)
                # Double check it's not already added somehow
                if abs_file_path not in self.abs_fnames and abs_file_path not in self.abs_read_only_fnames:
                    add_result = self._add_file_to_context(rel_path, explicit=True) # Use explicit=True for clear output
                    if "Added" in add_result:
                        added_count += 1
                        added_files_rel.append(rel_path)

            if added_count > 0:
                if added_count > 5:
                    brief = ', '.join(added_files_rel[:5]) + f', and {added_count-5} more'
                    self.io.tool_output(f"🔎 Found '{symbol}' and added {added_count} files: {brief}")
                else:
                    self.io.tool_output(f"🔎 Found '{symbol}' and added files: {', '.join(added_files_rel)}")
                return f"Found symbol '{symbol}' and added {added_count} files as read-only."
            else:
                self.io.tool_output(f"⚠️ Symbol '{symbol}' not found in searchable files.")
                return f"Symbol '{symbol}' not found in searchable files."

        except Exception as e:
            self.io.tool_error(f"Error in find: {str(e)}")
            return f"Error: {str(e)}"

    def _execute_command(self, command_string):
        """
        Execute an aider command after user confirmation.
        """
        try:
            # Ask for confirmation before executing, allowing 'Always'
            # Use the command string itself as the group key to remember preference per command
            if not self.io.confirm_ask(
                "Allow execution of this command?",
                subject=command_string,
                explicit_yes_required=True, # Require explicit 'yes' or 'always'
                allow_never=True           # Enable the 'Don't ask again' option
            ):
                # Check if the reason for returning False was *not* because it's remembered
                # (confirm_ask returns False if 'n' or 'no' is chosen, even if remembered)
                # We only want to skip if the user actively said no *this time* or if it's
                # remembered as 'never' (which shouldn't happen with allow_never=True,
                # but checking io.never_ask_group is robust).
                # If the command is in never_ask_group with a True value (meaning Always),
                # confirm_ask would have returned True directly.
                # So, if confirm_ask returns False here, it means the user chose No this time.
                self.io.tool_output(f"Skipped execution of shell command: {command_string}")
                return "Shell command execution skipped by user."

            self.io.tool_output(f"⚙️ Executing non-interactive shell command: {command_string}")

            # Use run_cmd_subprocess for non-interactive execution
            exit_status, combined_output = run_cmd_subprocess(
                command_string,
                verbose=self.verbose,
                cwd=self.root # Execute in the project root
            )

            # Format the output for the result message, include more content
            output_content = combined_output or ""
            # Use the existing token threshold constant as the character limit for truncation
            output_limit = self.large_file_token_threshold
            if len(output_content) > output_limit:
                # Truncate and add a clear message using the constant value
                output_content = output_content[:output_limit] + f"\n... (output truncated at {output_limit} characters, based on large_file_token_threshold)"

            if exit_status == 0:
                return f"Shell command executed successfully (exit code 0). Output:\n{output_content}"
            else:
                return f"Shell command failed with exit code {exit_status}. Output:\n{output_content}"

        except Exception as e:
            self.io.tool_error(f"Error executing non-interactive shell command '{command_string}': {str(e)}")
            # Optionally include traceback for debugging if verbose
            # if self.verbose:
            #     self.io.tool_error(traceback.format_exc())
            return f"Error executing command: {str(e)}"


    def _process_file_mentions(self, content):
        """
        Process implicit file mentions in the content, adding files if they're not already in context.
        
        This handles the case where the LLM mentions file paths without using explicit tool commands.
        """
        # Extract file mentions using the parent class's method
        mentioned_files = set(self.get_file_mentions(content, ignore_current=False))
        current_files = set(self.get_inchat_relative_files())
        
        # Get new files to add (not already in context)
        new_files = mentioned_files - current_files
        
        # In navigator mode, we *only* add files via explicit tool commands.
        # Do nothing here for implicit mentions.
        pass
        
    
    
    
    def check_for_file_mentions(self, content):
        """
        Override parent's method to use our own file processing logic.
        
        Override parent's method to disable implicit file mention handling in navigator mode.
        Files should only be added via explicit tool commands (`Add`, `Glob`, `Grep`).
        """
        # Do nothing - disable implicit file adds in navigator mode.
        pass

    def get_directory_structure(self):
        """
        Generate a structured directory listing similar to Claude Code's directoryStructure.
        Returns a formatted string representation of the directory tree.
        """
        if not self.use_enhanced_context:
            return None
            
        try:
            # Start with the header
            result = "<context name=\"directoryStructure\">Below is a snapshot of this project's file structure at the current time. It skips over .gitignore patterns.\n\n"
            
            # Get the root directory
            root_path = Path(self.root)
            root_str = str(root_path)
            
            # Get all files in the repo (both tracked and untracked)
            if self.repo:
                # Get tracked files
                tracked_files = self.repo.get_tracked_files()
                
                # Get untracked files (files present in the working directory but not in git)
                untracked_files = []
                try:
                    # Run git status to get untracked files
                    untracked_output = self.repo.repo.git.status('--porcelain')
                    for line in untracked_output.splitlines():
                        if line.startswith('??'):
                            # Extract the filename (remove the '?? ' prefix)
                            untracked_file = line[3:]
                            if not self.repo.git_ignored_file(untracked_file):
                                untracked_files.append(untracked_file)
                except Exception as e:
                    self.io.tool_warning(f"Error getting untracked files: {str(e)}")
                
                # Combine tracked and untracked files
                all_files = tracked_files + untracked_files
            else:
                # If no repo, get all files relative to root
                all_files = []
                for path in Path(self.root).rglob('*'):
                    if path.is_file():
                        all_files.append(str(path.relative_to(self.root)))
            
            # Sort files to ensure deterministic output
            all_files = sorted(all_files)

            # Filter out .aider files/dirs
            all_files = [f for f in all_files if not any(part.startswith('.aider') for part in f.split('/'))]

            # Build tree structure
            tree = {}
            for file in all_files:
                parts = file.split('/')
                current = tree
                for i, part in enumerate(parts):
                    if i == len(parts) - 1:  # Last part (file)
                        if '.' not in current:
                            current['.'] = []
                        current['.'].append(part)
                    else:  # Directory
                        if part not in current:
                            current[part] = {}
                        current = current[part]
            
            # Function to recursively print the tree
            def print_tree(node, prefix="- ", indent="  ", path=""):
                lines = []
                # First print all directories
                dirs = sorted([k for k in node.keys() if k != '.'])
                for i, dir_name in enumerate(dirs):
                    full_path = f"{path}/{dir_name}" if path else dir_name
                    lines.append(f"{prefix}{full_path}/")
                    sub_lines = print_tree(node[dir_name], prefix=prefix, indent=indent, path=full_path)
                    for sub_line in sub_lines:
                        lines.append(f"{indent}{sub_line}")
                
                # Then print all files
                if '.' in node:
                    for file_name in sorted(node['.']):
                        lines.append(f"{prefix}{path}/{file_name}" if path else f"{prefix}{file_name}")
                
                return lines
            
            # Generate the tree starting from root
            tree_lines = print_tree(tree, prefix="- ")
            result += "\n".join(tree_lines)
            result += "\n</context>"
            
            return result
        except Exception as e:
            self.io.tool_error(f"Error generating directory structure: {str(e)}")
            return None
    
    def get_git_status(self):
        """
        Generate a git status context block similar to Claude Code's gitStatus.
        Returns a formatted string with git branch, status, and recent commits.
        """
        if not self.use_enhanced_context or not self.repo:
            return None
            
        try:
            result = "<context name=\"gitStatus\">This is a snapshot of the git status at the current time.\n"
            
            # Get current branch
            try:
                current_branch = self.repo.repo.active_branch.name
                result += f"Current branch: {current_branch}\n\n"
            except Exception:
                result += "Current branch: (detached HEAD state)\n\n"
            
            # Get main/master branch
            main_branch = None
            try:
                for branch in self.repo.repo.branches:
                    if branch.name in ('main', 'master'):
                        main_branch = branch.name
                        break
                if main_branch:
                    result += f"Main branch (you will usually use this for PRs): {main_branch}\n\n"
            except Exception:
                pass
            
            # Git status
            result += "Status:\n"
            try:
                # Get modified files
                status = self.repo.repo.git.status('--porcelain')
                
                # Process and categorize the status output
                if status:
                    status_lines = status.strip().split('\n')
                    
                    # Group by status type for better organization
                    staged_added = []
                    staged_modified = []
                    staged_deleted = []
                    unstaged_modified = []
                    unstaged_deleted = []
                    untracked = []
                    
                    for line in status_lines:
                        if len(line) < 4:  # Ensure the line has enough characters
                            continue
                            
                        status_code = line[:2]
                        file_path = line[3:]

                        # Skip .aider files/dirs
                        if any(part.startswith('.aider') for part in file_path.split('/')):
                            continue
                        
                        # Staged changes
                        if status_code[0] == 'A':
                            staged_added.append(file_path)
                        elif status_code[0] == 'M':
                            staged_modified.append(file_path)
                        elif status_code[0] == 'D':
                            staged_deleted.append(file_path)
                        # Unstaged changes
                        if status_code[1] == 'M':
                            unstaged_modified.append(file_path)
                        elif status_code[1] == 'D':
                            unstaged_deleted.append(file_path)
                        # Untracked files
                        if status_code == '??':
                            untracked.append(file_path)
                    
                    # Output in a nicely formatted manner
                    if staged_added:
                        for file in staged_added:
                            result += f"A  {file}\n"
                    if staged_modified:
                        for file in staged_modified:
                            result += f"M  {file}\n"
                    if staged_deleted:
                        for file in staged_deleted:
                            result += f"D  {file}\n"
                    if unstaged_modified:
                        for file in unstaged_modified:
                            result += f" M {file}\n"
                    if unstaged_deleted:
                        for file in unstaged_deleted:
                            result += f" D {file}\n"
                    if untracked:
                        for file in untracked:
                            result += f"?? {file}\n"
                else:
                    result += "Working tree clean\n"
            except Exception as e:
                result += f"Unable to get modified files: {str(e)}\n"
            
            # Recent commits
            result += "\nRecent commits:\n"
            try:
                commits = list(self.repo.repo.iter_commits(max_count=5))
                for commit in commits:
                    short_hash = commit.hexsha[:8]
                    message = commit.message.strip().split('\n')[0]  # First line only
                    result += f"{short_hash} {message}\n"
            except Exception:
                result += "Unable to get recent commits\n"
                
            result += "</context>"
            return result
        except Exception as e:
            self.io.tool_error(f"Error generating git status: {str(e)}")
            return None
            
    def cmd_context_blocks(self, args=""):
        """
        Toggle enhanced context blocks feature.
        """
        self.use_enhanced_context = not self.use_enhanced_context
        
        if self.use_enhanced_context:
            self.io.tool_output("Enhanced context blocks are now ON - directory structure and git status will be included.")
        else:
            self.io.tool_output("Enhanced context blocks are now OFF - directory structure and git status will not be included.")
        
        return True
