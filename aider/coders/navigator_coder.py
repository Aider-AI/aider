import ast
import re
import fnmatch
import os
import time
import random
import subprocess
import traceback
import platform
import locale
from datetime import datetime
from pathlib import Path
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import ParseError
# Add necessary imports if not already present
from collections import defaultdict

from .base_coder import Coder
from .editblock_coder import find_original_update_blocks, do_replace, find_similar_lines
from .navigator_prompts import NavigatorPrompts
from .navigator_legacy_prompts import NavigatorLegacyPrompts
from aider.repo import ANY_GIT_ERROR
from aider import urls
# Import run_cmd for potentially interactive execution and run_cmd_subprocess for guaranteed non-interactive
from aider.run_cmd import run_cmd, run_cmd_subprocess
# Import the change tracker
from aider.change_tracker import ChangeTracker
# Import tool functions
from aider.tools.view_files_at_glob import execute_view_files_at_glob
from aider.tools.view_files_matching import execute_view_files_matching
from aider.tools.ls import execute_ls
from aider.tools.view import execute_view
from aider.tools.remove import _execute_remove
from aider.tools.make_editable import _execute_make_editable
from aider.tools.make_readonly import _execute_make_readonly
from aider.tools.view_files_with_symbol import _execute_view_files_with_symbol
from aider.tools.command import _execute_command
from aider.tools.command_interactive import _execute_command_interactive
from aider.tools.replace_text import _execute_replace_text
from aider.tools.replace_all import _execute_replace_all
from aider.tools.insert_block import _execute_insert_block
from aider.tools.delete_block import _execute_delete_block
from aider.tools.replace_line import _execute_replace_line
from aider.tools.replace_lines import _execute_replace_lines
from aider.tools.indent_lines import _execute_indent_lines
from aider.tools.delete_line import _execute_delete_line
from aider.tools.delete_lines import _execute_delete_lines
from aider.tools.undo_change import _execute_undo_change
from aider.tools.list_changes import _execute_list_changes
from aider.tools.extract_lines import _execute_extract_lines
from aider.tools.show_numbered_context import execute_show_numbered_context


class NavigatorCoder(Coder):
    """Mode where the LLM autonomously manages which files are in context."""

    edit_format = "navigator"
    
    # TODO: We'll turn on granular editing by default once those tools stabilize
    use_granular_editing = False
    
    def __init__(self, *args, **kwargs):
        # Initialize appropriate prompt set before calling parent constructor
        # This needs to happen before super().__init__ so the parent class has access to gpt_prompts
        self.gpt_prompts = NavigatorPrompts() if self.use_granular_editing else NavigatorLegacyPrompts()

        # Dictionary to track recently removed files
        self.recently_removed = {}

        # Configuration parameters
        self.max_tool_calls = 100          # Maximum number of tool calls per response

        # Context management parameters
        self.large_file_token_threshold = 25000  # Files larger than this in tokens are considered large
        self.max_files_per_glob = 50             # Maximum number of files to add at once via glob/grep

        # Enable context management by default only in navigator mode
        self.context_management_enabled = True   # Enabled by default for navigator mode

        # Initialize change tracker for granular editing
        self.change_tracker = ChangeTracker()

        # Track files added during current exploration
        self.files_added_in_exploration = set()

        # Counter for tool calls
        self.tool_call_count = 0

        # Set high max reflections to allow many exploration rounds
        # This controls how many automatic iterations the LLM can do
        self.max_reflections = 15

        # Enable enhanced context blocks by default
        self.use_enhanced_context = True
        
        super().__init__(*args, **kwargs)
        
    def set_granular_editing(self, enabled):
        """
        Switch between granular editing tools and legacy search/replace.
        
        Args:
            enabled (bool): True to use granular editing tools, False to use legacy search/replace
        """
        self.use_granular_editing = enabled
        self.gpt_prompts = NavigatorPrompts() if enabled else NavigatorLegacyPrompts()

    def get_context_symbol_outline(self):
        """
        Generate a symbol outline for files currently in context using Tree-sitter,
        bypassing the cache for freshness.
        """
        if not self.use_enhanced_context or not self.repo_map:
            return None

        try:
            result = "<context name=\"symbol_outline\">\n"
            result += "## Symbol Outline (Current Context)\n\n"
            result += "Code definitions (classes, functions, methods, etc.) found in files currently in chat context.\n\n"

            files_to_outline = list(self.abs_fnames) + list(self.abs_read_only_fnames)
            if not files_to_outline:
                result += "No files currently in context.\n"
                result += "</context>"
                return result

            all_tags_by_file = defaultdict(list)
            has_symbols = False

            # Use repo_map which should be initialized in BaseCoder
            if not self.repo_map:
                 self.io.tool_warning("RepoMap not initialized, cannot generate symbol outline.")
                 return None # Or return a message indicating repo map is unavailable

            for abs_fname in sorted(files_to_outline):
                rel_fname = self.get_rel_fname(abs_fname)
                try:
                    # Call get_tags_raw directly to bypass cache and ensure freshness
                    tags = list(self.repo_map.get_tags_raw(abs_fname, rel_fname))
                    if tags:
                        all_tags_by_file[rel_fname].extend(tags)
                        has_symbols = True
                except Exception as e:
                    self.io.tool_warning(f"Could not get symbols for {rel_fname}: {e}")

            if not has_symbols:
                 result += "No symbols found in the current context files.\n"
            else:
                for rel_fname in sorted(all_tags_by_file.keys()):
                    tags = sorted(all_tags_by_file[rel_fname], key=lambda t: (t.line, t.name))

                    definition_tags = []
                    for tag in tags:
                        # Use specific_kind first if available, otherwise fall back to kind
                        kind_to_check = tag.specific_kind or tag.kind
                        # Check if the kind represents a definition using the set from RepoMap
                        if kind_to_check and kind_to_check.lower() in self.repo_map.definition_kinds:
                            definition_tags.append(tag)

                    if definition_tags:
                        result += f"### {rel_fname}\n"
                        # Simple list format for now, could be enhanced later (e.g., indentation for scope)
                        for tag in definition_tags:
                            # Display line number if available
                            line_info = f", line {tag.line + 1}" if tag.line >= 0 else ""
                            # Display the specific kind (which we checked)
                            kind_to_check = tag.specific_kind or tag.kind # Recalculate for safety
                            result += f"- {tag.name} ({kind_to_check}{line_info})\n"
                        result += "\n" # Add space between files

            result += "</context>"
            return result.strip() # Remove trailing newline if any

        except Exception as e:
            self.io.tool_error(f"Error generating symbol outline: {str(e)}")
            # Optionally include traceback for debugging if verbose
            # if self.verbose:
            #     self.io.tool_error(traceback.format_exc())
            return None

    def format_chat_chunks(self):
        """
        Override parent's format_chat_chunks to include enhanced context blocks with a
        cleaner, more hierarchical structure for better organization.
        """
        # First get the normal chat chunks from the parent method
        chunks = super().format_chat_chunks() # Calls BaseCoder's format_chat_chunks

        # If enhanced context blocks are enabled, prepend them to the current messages
        if self.use_enhanced_context:
            # Create environment info context block
            env_context = self.get_environment_info()

            # Get current context summary
            context_summary = self.get_context_summary()

            # Get directory structure
            dir_structure = self.get_directory_structure()

            # Get git status
            git_status = self.get_git_status()

            # Get symbol outline for current context files
            symbol_outline = self.get_context_symbol_outline()

            # Collect all context blocks that exist
            context_blocks = []
            if env_context:
                context_blocks.append(env_context)
            if context_summary:
                context_blocks.append(context_summary)
            if dir_structure:
                context_blocks.append(dir_structure)
            if git_status:
                context_blocks.append(git_status)
            if symbol_outline: # Add the new block if it was generated
                context_blocks.append(symbol_outline)

            # If we have any context blocks, prepend them to the system message
            if context_blocks:
                context_message = "\n\n".join(context_blocks)
                # Prepend to system context but don't overwrite existing system content
                if chunks.system:
                    # If we already have system messages, append our context to the first one
                    original_content = chunks.system[0]["content"]
                    # Ensure there's separation between our blocks and the original prompt
                    chunks.system[0]["content"] = context_message + "\n\n" + original_content
                else:
                    # Otherwise, create a new system message
                    chunks.system = [dict(role="system", content=context_message)]

        return chunks

    def get_context_summary(self):
        """
        Generate a summary of the current context, including file content tokens and additional context blocks,
        with an accurate total token count.
        """
        if not self.use_enhanced_context:
            return None
        try:
            result = "<context name=\"context_summary\">\n"
            result += "## Current Context Overview\n\n"
            max_input_tokens = self.main_model.info.get("max_input_tokens") or 0
            max_output_tokens = self.main_model.info.get("max_output_tokens") or 0
            if max_input_tokens:
                result += f"Model context limit: {max_input_tokens:,} tokens\n\n"

            total_file_tokens = 0
            editable_tokens = 0
            readonly_tokens = 0
            editable_files = []
            readonly_files = []

            # Editable files
            if self.abs_fnames:
                result += "### Editable Files\n\n"
                for fname in sorted(self.abs_fnames):
                    rel_fname = self.get_rel_fname(fname)
                    content = self.io.read_text(fname)
                    if content is not None:
                        tokens = self.main_model.token_count(content)
                        total_file_tokens += tokens
                        editable_tokens += tokens
                        size_indicator = "🔴 Large" if tokens > 5000 else ("🟡 Medium" if tokens > 1000 else "🟢 Small")
                        editable_files.append(f"- {rel_fname}: {tokens:,} tokens ({size_indicator})")
                if editable_files:
                    result += "\n".join(editable_files) + "\n\n"
                    result += f"**Total editable: {len(editable_files)} files, {editable_tokens:,} tokens**\n\n"
                else:
                    result += "No editable files in context\n\n"

            # Read-only files
            if self.abs_read_only_fnames:
                result += "### Read-Only Files\n\n"
                for fname in sorted(self.abs_read_only_fnames):
                    rel_fname = self.get_rel_fname(fname)
                    content = self.io.read_text(fname)
                    if content is not None:
                        tokens = self.main_model.token_count(content)
                        total_file_tokens += tokens
                        readonly_tokens += tokens
                        size_indicator = "🔴 Large" if tokens > 5000 else ("🟡 Medium" if tokens > 1000 else "🟢 Small")
                        readonly_files.append(f"- {rel_fname}: {tokens:,} tokens ({size_indicator})")
                if readonly_files:
                    result += "\n".join(readonly_files) + "\n\n"
                    result += f"**Total read-only: {len(readonly_files)} files, {readonly_tokens:,} tokens**\n\n"
                else:
                    result += "No read-only files in context\n\n"

            # Additional enhanced context blocks
            env_info = self.get_environment_info()
            dir_structure = self.get_directory_structure()
            git_status = self.get_git_status()
            symbol_outline = self.get_context_symbol_outline()

            extra_context = ""
            extra_tokens = 0
            if env_info:
                extra_context += env_info + "\n\n"
                extra_tokens += self.main_model.token_count(env_info)
            if dir_structure:
                extra_context += dir_structure + "\n\n"
                extra_tokens += self.main_model.token_count(dir_structure)
            if git_status:
                extra_context += git_status + "\n\n"
                extra_tokens += self.main_model.token_count(git_status)
            if symbol_outline:
                extra_context += symbol_outline + "\n\n"
                extra_tokens += self.main_model.token_count(symbol_outline)

            total_tokens = total_file_tokens + extra_tokens

            result += f"**Total files usage: {total_file_tokens:,} tokens**\n\n"
            result += f"**Additional context usage: {extra_tokens:,} tokens**\n\n"
            result += f"**Total context usage: {total_tokens:,} tokens**"
            if max_input_tokens:
                percentage = (total_tokens / max_input_tokens) * 100
                result += f" ({percentage:.1f}% of limit)"
                if percentage > 80:
                    result += "\n\n⚠️ **Context is getting full!** Remove non-essential files via:\n"
                    result += "- `[tool_call(Remove, file_path=\"path/to/large_file.ext\")]`\n"
                    result += "- Keep only essential files in context for best performance"
            result += "\n</context>"
            return result
        except Exception as e:
            self.io.tool_error(f"Error generating context summary: {str(e)}")
            return None
        
    def get_environment_info(self):
        """
        Generate an environment information context block with key system details.
        Returns formatted string with working directory, platform, date, and other relevant environment details.
        """
        if not self.use_enhanced_context:
            return None
            
        try:
            # Get current date in ISO format
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            # Get platform information
            platform_info = platform.platform()
            
            # Get language preference
            language = self.chat_language or locale.getlocale()[0] or "en-US"
            
            result = "<context name=\"environment_info\">\n"
            result += "## Environment Information\n\n"
            result += f"- Working directory: {self.root}\n"
            result += f"- Current date: {current_date}\n"
            result += f"- Platform: {platform_info}\n"
            result += f"- Language preference: {language}\n"
            
            # Add git repo information if available
            if self.repo:
                try:
                    rel_repo_dir = self.repo.get_rel_repo_dir()
                    num_files = len(self.repo.get_tracked_files())
                    result += f"- Git repository: {rel_repo_dir} with {num_files:,} files\n"
                except Exception:
                    result += "- Git repository: active but details unavailable\n"
            else:
                result += "- Git repository: none\n"
                
            # Add enabled features information
            features = []
            if self.context_management_enabled:
                features.append("context management")
            if self.use_enhanced_context:
                features.append("enhanced context blocks")
            if features:
                result += f"- Enabled features: {', '.join(features)}\n"
                
            result += "</context>"
            return result
        except Exception as e:
            self.io.tool_error(f"Error generating environment info: {str(e)}")
            return None
        
    def reply_completed(self):
        """Process the completed response from the LLM.
        
        This is a key method that:
        1. Processes any tool commands in the response (only after a '---' line)
        2. Processes any SEARCH/REPLACE blocks in the response (only before the '---' line if one exists)
        3. If tool commands were found, sets up for another automatic round
        
        This enables the "auto-exploration" workflow where the LLM can
        iteratively discover and analyze relevant files before providing
        a final answer to the user's question.
        """
        content = self.partial_response_content
        if not content or not content.strip():
            return True
        original_content = content # Keep the original response

        # Process tool commands: returns content with tool calls removed, results, flag if any tool calls were found,
        # and the content before the last '---' line
        processed_content, result_messages, tool_calls_found, content_before_last_separator = self._process_tool_commands(content)

        # Since we are no longer suppressing, the partial_response_content IS the final content.
        # We might want to update it to the processed_content (without tool calls) if we don't
        # want the raw tool calls to remain in the final assistant message history.
        # Let's update it for cleaner history.
        self.partial_response_content = processed_content.strip()

        # Process implicit file mentions using the content *after* tool calls were removed
        self._process_file_mentions(processed_content)

        # Check if the content contains the SEARCH/REPLACE markers
        has_search = "<<<<<<< SEARCH" in self.partial_response_content
        has_divider = "=======" in self.partial_response_content
        has_replace = ">>>>>>> REPLACE" in self.partial_response_content
        edit_match = has_search and has_divider and has_replace

        # Check if there's a '---' line - if yes, SEARCH/REPLACE blocks can only appear before it
        separator_marker = "\n---\n"
        if separator_marker in original_content and edit_match:
            # Check if the edit blocks are only in the part before the last '---' line
            has_search_before = "<<<<<<< SEARCH" in content_before_last_separator
            has_divider_before = "=======" in content_before_last_separator
            has_replace_before = ">>>>>>> REPLACE" in content_before_last_separator
            edit_match = has_search_before and has_divider_before and has_replace_before

        if edit_match:
            self.io.tool_output("Detected edit blocks, applying changes within Navigator...")
            edited_files = self._apply_edits_from_response()
            # If _apply_edits_from_response set a reflected_message (due to errors),
            # return False to trigger a reflection loop.
            if self.reflected_message:
                return False

        # If any tool calls were found and we haven't exceeded reflection limits, set up for another iteration
        # This is implicit continuation when any tool calls are present, rather than requiring Continue explicitly
        if tool_calls_found and self.num_reflections < self.max_reflections:
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
        
        Rules:
        1. Tool calls must appear after the LAST '---' line separator in the content
        2. Any tool calls before this last separator are treated as text (not executed)
        3. SEARCH/REPLACE blocks can only appear before this last separator
        
        Returns processed content, result messages, and a flag indicating if any tool calls were found.
        Also returns the content before the last separator for SEARCH/REPLACE block validation.
        """
        result_messages = []
        modified_content = content # Start with original content
        tool_calls_found = False
        call_count = 0
        max_calls = self.max_tool_calls

        # Check if there's a '---' separator and only process tool calls after the LAST one
        separator_marker = "\n---\n"
        content_parts = content.split(separator_marker)
        
        # If there's no separator, treat the entire content as before the separator
        if len(content_parts) == 1:
            # Return the original content with no tool calls processed, and the content itself as before_separator
            return content, result_messages, False, content
            
        # Take everything before the last separator (including intermediate separators)
        content_before_separator = separator_marker.join(content_parts[:-1])
        # Take only what comes after the last separator
        content_after_separator = content_parts[-1]
        
        # Find tool calls using a more robust method, but only in the content after separator
        processed_content = content_before_separator + separator_marker
        last_index = 0
        start_marker = "[tool_call("
        end_marker = "]" # The parenthesis balancing finds the ')', we just need the final ']'

        while True:
            start_pos = content_after_separator.find(start_marker, last_index)
            if start_pos == -1:
                processed_content += content_after_separator[last_index:]
                break

            # Check for escaped tool call: \[tool_call(
            if start_pos > 0 and content_after_separator[start_pos - 1] == '\\':
                # Append the content including the escaped marker
                # We append up to start_pos + len(start_marker) to include the marker itself.
                processed_content += content_after_separator[last_index : start_pos + len(start_marker)]
                # Update last_index to search after this escaped marker
                last_index = start_pos + len(start_marker)
                continue # Continue searching for the next potential marker

            # Append content before the (non-escaped) tool call
            processed_content += content_after_separator[last_index:start_pos]

            scan_start_pos = start_pos + len(start_marker)
            paren_level = 1
            in_single_quotes = False
            in_double_quotes = False
            escaped = False
            end_paren_pos = -1

            # Scan to find the matching closing parenthesis, respecting quotes
            for i in range(scan_start_pos, len(content_after_separator)):
                char = content_after_separator[i]

                if escaped:
                    escaped = False
                elif char == '\\':
                    escaped = True
                elif char == "'" and not in_double_quotes:
                    in_single_quotes = not in_single_quotes
                elif char == '"' and not in_single_quotes:
                    in_double_quotes = not in_double_quotes
                elif char == '(' and not in_single_quotes and not in_double_quotes:
                    paren_level += 1
                elif char == ')' and not in_single_quotes and not in_double_quotes:
                    paren_level -= 1
                    if paren_level == 0:
                        end_paren_pos = i
                        break

            # Check for the end marker after the closing parenthesis, skipping whitespace
            expected_end_marker_start = end_paren_pos + 1
            actual_end_marker_start = -1
            end_marker_found = False
            if end_paren_pos != -1: # Only search if we found a closing parenthesis
                for j in range(expected_end_marker_start, len(content_after_separator)):
                    if not content_after_separator[j].isspace():
                        actual_end_marker_start = j
                        # Check if the found character is the end marker ']'
                        if content_after_separator[actual_end_marker_start] == end_marker:
                            end_marker_found = True
                        break # Stop searching after first non-whitespace char

            if not end_marker_found:
                # Try to extract the tool name for better error message
                tool_name = "unknown"
                try:
                    # Look for the first comma after the tool call start
                    partial_content = content_after_separator[scan_start_pos:scan_start_pos+100]  # Limit to avoid huge strings
                    comma_pos = partial_content.find(',')
                    if comma_pos > 0:
                        tool_name = partial_content[:comma_pos].strip()
                    else:
                        # If no comma, look for opening parenthesis or first whitespace
                        space_pos = partial_content.find(' ')
                        paren_pos = partial_content.find('(')
                        if space_pos > 0 and (paren_pos < 0 or space_pos < paren_pos):
                            tool_name = partial_content[:space_pos].strip()
                        elif paren_pos > 0:
                            tool_name = partial_content[:paren_pos].strip()
                except:
                    pass  # Silently fail if we can't extract the name
                
                # Malformed call: couldn't find matching ')' or the subsequent ']'
                self.io.tool_warning(f"Malformed tool call for '{tool_name}'. Missing closing parenthesis or bracket. Skipping.")
                # Append the start marker itself to processed content so it's not lost
                processed_content += start_marker
                last_index = scan_start_pos # Continue searching after the marker
                continue

            # Found a potential tool call
            # Adjust full_match_str and last_index based on the actual end marker ']' position
            full_match_str = content_after_separator[start_pos : actual_end_marker_start + 1] # End marker ']' is 1 char
            inner_content = content_after_separator[scan_start_pos:end_paren_pos].strip()
            last_index = actual_end_marker_start + 1 # Move past the processed call (including ']')


            call_count += 1
            if call_count > max_calls:
                self.io.tool_warning(f"Exceeded maximum tool calls ({max_calls}). Skipping remaining calls.")
                # Don't append the skipped call to processed_content
                continue # Skip processing this call

            tool_calls_found = True
            tool_name = None
            params = {}
            result_message = None

            # Mark that we found at least one tool call (assuming it passes validation)
            tool_calls_found = True

            try:
                # Wrap the inner content to make it parseable as a function call
                # Example: ToolName, key="value" becomes f(ToolName, key="value")
                parse_str = f"f({inner_content})"
                parsed_ast = ast.parse(parse_str)

                # Validate AST structure
                if not isinstance(parsed_ast, ast.Module) or not parsed_ast.body or not isinstance(parsed_ast.body[0], ast.Expr):
                    raise ValueError("Unexpected AST structure")
                call_node = parsed_ast.body[0].value
                if not isinstance(call_node, ast.Call):
                     raise ValueError("Expected a Call node")

                # Extract tool name (should be the first positional argument)
                if not call_node.args or not isinstance(call_node.args[0], ast.Name):
                    raise ValueError("Tool name not found or invalid")
                tool_name = call_node.args[0].id

                # Extract keyword arguments
                for keyword in call_node.keywords:
                    key = keyword.arg
                    value_node = keyword.value
                    # Extract value based on AST node type
                    if isinstance(value_node, ast.Constant):
                        value = value_node.value
                        # Check if this is a multiline string and trim whitespace
                        if isinstance(value, str) and '\n' in value:
                            # Get the source line(s) for this node to check if it's a triple-quoted string
                            lineno = value_node.lineno if hasattr(value_node, 'lineno') else 0
                            end_lineno = value_node.end_lineno if hasattr(value_node, 'end_lineno') else lineno
                            if end_lineno > lineno:  # It's a multiline string
                                # Trim exactly one leading and one trailing newline if present
                                if value.startswith('\n'):
                                    value = value[1:]
                                if value.endswith('\n'):
                                    value = value[:-1]
                    elif isinstance(value_node, ast.Name): # Handle unquoted values like True/False/None or variables (though variables are unlikely here)
                        value = value_node.id
                    # Add more types if needed (e.g., ast.List, ast.Dict)
                    else:
                        # Attempt to reconstruct the source for complex types, or raise error
                        try:
                            # Note: ast.unparse requires Python 3.9+
                            # If using older Python, might need a different approach or limit supported types
                            value = ast.unparse(value_node)
                        except AttributeError: # Handle case where ast.unparse is not available
                             raise ValueError(f"Unsupported argument type for key '{key}': {type(value_node)}")
                        except Exception as ue:
                             raise ValueError(f"Could not unparse value for key '{key}': {ue}")


                    # Check for suppressed values (e.g., "...")
                    suppressed_arg_values = ["..."]
                    if isinstance(value, str) and value in suppressed_arg_values:
                        self.io.tool_warning(f"Skipping suppressed argument value '{value}' for key '{key}' in tool '{tool_name}'")
                        continue

                    params[key] = value


            except (SyntaxError, ValueError) as e:
                result_message = f"Error parsing tool call '{inner_content}': {e}"
                self.io.tool_error(f"Failed to parse tool call: {full_match_str}\nError: {e}")
                # Don't append the malformed call to processed_content
                result_messages.append(f"[Result (Parse Error): {result_message}]")
                continue # Skip execution
            except Exception as e: # Catch any other unexpected parsing errors
                result_message = f"Unexpected error parsing tool call '{inner_content}': {e}"
                self.io.tool_error(f"Unexpected error during parsing: {full_match_str}\nError: {e}\n{traceback.format_exc()}")
                result_messages.append(f"[Result (Parse Error): {result_message}]")
                continue

            # Execute the tool based on its name
            try:
                # Normalize tool name for case-insensitive matching
                norm_tool_name = tool_name.lower()

                if norm_tool_name == 'viewfilesatglob':
                    pattern = params.get('pattern')
                    if pattern is not None:
                        # Call the imported function
                        result_message = execute_view_files_at_glob(self, pattern)
                    else:
                        result_message = "Error: Missing 'pattern' parameter for ViewFilesAtGlob"
                elif norm_tool_name == 'viewfilesmatching':
                    pattern = params.get('pattern')
                    file_pattern = params.get('file_pattern') # Optional
                    regex = params.get('regex', False) # Default to False if not provided
                    if pattern is not None:
                        result_message = execute_view_files_matching(self, pattern, file_pattern, regex)
                    else:
                        result_message = "Error: Missing 'pattern' parameter for ViewFilesMatching"
                elif norm_tool_name == 'ls':
                    directory = params.get('directory')
                    if directory is not None:
                        result_message = execute_ls(self, directory)
                    else:
                        result_message = "Error: Missing 'directory' parameter for Ls"
                elif norm_tool_name == 'view':
                    file_path = params.get('file_path')
                    if file_path is not None:
                        result_message = execute_view(self, file_path)
                    else:
                        result_message = "Error: Missing 'file_path' parameter for View"
                elif norm_tool_name == 'remove':
                    file_path = params.get('file_path')
                    if file_path is not None:
                        result_message = _execute_remove(self, file_path)
                    else:
                        result_message = "Error: Missing 'file_path' parameter for Remove"
                elif norm_tool_name == 'makeeditable':
                    file_path = params.get('file_path')
                    if file_path is not None:
                        result_message = _execute_make_editable(self, file_path)
                    else:
                        result_message = "Error: Missing 'file_path' parameter for MakeEditable"
                elif norm_tool_name == 'makereadonly':
                    file_path = params.get('file_path')
                    if file_path is not None:
                        result_message = _execute_make_readonly(self, file_path)
                    else:
                        result_message = "Error: Missing 'file_path' parameter for MakeReadonly"
                elif norm_tool_name == 'viewfileswithsymbol':
                    symbol = params.get('symbol')
                    if symbol is not None:
                        # Call the imported function from the tools directory
                        result_message = _execute_view_files_with_symbol(self, symbol)
                    else:
                        result_message = "Error: Missing 'symbol' parameter for ViewFilesWithSymbol"

                # Command tools
                elif norm_tool_name == 'command':
                    command_string = params.get('command_string')
                    if command_string is not None:
                        result_message = _execute_command(self, command_string)
                    else:
                        result_message = "Error: Missing 'command_string' parameter for Command"
                elif norm_tool_name == 'commandinteractive':
                    command_string = params.get('command_string')
                    if command_string is not None:
                        result_message = _execute_command_interactive(self, command_string)
                    else:
                        result_message = "Error: Missing 'command_string' parameter for CommandInteractive"

                # Grep tool
                elif norm_tool_name == 'grep':
                    pattern = params.get('pattern')
                    file_pattern = params.get('file_pattern', '*') # Default to all files
                    directory = params.get('directory', '.') # Default to current directory
                    use_regex = params.get('use_regex', False) # Default to literal search
                    case_insensitive = params.get('case_insensitive', False) # Default to case-sensitive
                    context_before = params.get('context_before', 5)
                    context_after = params.get('context_after', 5)


                    if pattern is not None:
                        # Import the function if not already imported (it should be)
                        from aider.tools.grep import _execute_grep
                        result_message = _execute_grep(self, pattern, file_pattern, directory, use_regex, case_insensitive, context_before, context_after)
                    else:
                        result_message = "Error: Missing required 'pattern' parameter for Grep"

                # Granular editing tools
                elif norm_tool_name == 'replacetext':
                    file_path = params.get('file_path')
                    find_text = params.get('find_text')
                    replace_text = params.get('replace_text')
                    near_context = params.get('near_context')
                    occurrence = params.get('occurrence', 1) # Default to first occurrence
                    change_id = params.get('change_id')
                    dry_run = params.get('dry_run', False) # Default to False

                    if file_path is not None and find_text is not None and replace_text is not None:
                        result_message = _execute_replace_text(
                            self, file_path, find_text, replace_text, near_context, occurrence, change_id, dry_run
                        )
                    else:
                        result_message = "Error: Missing required parameters for ReplaceText (file_path, find_text, replace_text)"
                
                elif norm_tool_name == 'replaceall':
                    file_path = params.get('file_path')
                    find_text = params.get('find_text')
                    replace_text = params.get('replace_text')
                    change_id = params.get('change_id')
                    dry_run = params.get('dry_run', False) # Default to False

                    if file_path is not None and find_text is not None and replace_text is not None:
                        result_message = _execute_replace_all(
                            self, file_path, find_text, replace_text, change_id, dry_run
                        )
                    else:
                        result_message = "Error: Missing required parameters for ReplaceAll (file_path, find_text, replace_text)"
                
                elif norm_tool_name == 'insertblock':
                    file_path = params.get('file_path')
                    content = params.get('content')
                    after_pattern = params.get('after_pattern')
                    before_pattern = params.get('before_pattern')
                    near_context = params.get('near_context') # New
                    occurrence = params.get('occurrence', 1) # New, default 1
                    change_id = params.get('change_id')
                    dry_run = params.get('dry_run', False) # New, default False

                    if file_path is not None and content is not None and (after_pattern is not None or before_pattern is not None):
                        result_message = _execute_insert_block(
                            self, file_path, content, after_pattern, before_pattern, near_context, occurrence, change_id, dry_run
                        )
                    else:
                        result_message = "Error: Missing required parameters for InsertBlock (file_path, content, and either after_pattern or before_pattern)"
                
                elif norm_tool_name == 'deleteblock':
                    file_path = params.get('file_path')
                    start_pattern = params.get('start_pattern')
                    end_pattern = params.get('end_pattern')
                    line_count = params.get('line_count')
                    near_context = params.get('near_context') # New
                    occurrence = params.get('occurrence', 1) # New, default 1
                    change_id = params.get('change_id')
                    dry_run = params.get('dry_run', False) # New, default False

                    if file_path is not None and start_pattern is not None:
                        result_message = _execute_delete_block(
                            self, file_path, start_pattern, end_pattern, line_count, near_context, occurrence, change_id, dry_run
                        )
                    else:
                        result_message = "Error: Missing required parameters for DeleteBlock (file_path, start_pattern)"
                
                elif norm_tool_name == 'replaceline':
                    file_path = params.get('file_path')
                    line_number = params.get('line_number')
                    new_content = params.get('new_content')
                    change_id = params.get('change_id')
                    dry_run = params.get('dry_run', False) # New, default False

                    if file_path is not None and line_number is not None and new_content is not None:
                        result_message = _execute_replace_line(
                            self, file_path, line_number, new_content, change_id, dry_run
                        )
                    else:
                        result_message = "Error: Missing required parameters for ReplaceLine (file_path, line_number, new_content)"
                
                elif norm_tool_name == 'replacelines':
                    file_path = params.get('file_path')
                    start_line = params.get('start_line')
                    end_line = params.get('end_line')
                    new_content = params.get('new_content')
                    change_id = params.get('change_id')
                    dry_run = params.get('dry_run', False) # New, default False

                    if file_path is not None and start_line is not None and end_line is not None and new_content is not None:
                        result_message = _execute_replace_lines(
                            self, file_path, start_line, end_line, new_content, change_id, dry_run
                        )
                    else:
                        result_message = "Error: Missing required parameters for ReplaceLines (file_path, start_line, end_line, new_content)"
                
                elif norm_tool_name == 'indentlines':
                    file_path = params.get('file_path')
                    start_pattern = params.get('start_pattern')
                    end_pattern = params.get('end_pattern')
                    line_count = params.get('line_count')
                    indent_levels = params.get('indent_levels', 1) # Default to indent 1 level
                    near_context = params.get('near_context') # New
                    occurrence = params.get('occurrence', 1) # New, default 1
                    change_id = params.get('change_id')
                    dry_run = params.get('dry_run', False) # New, default False

                    if file_path is not None and start_pattern is not None:
                        result_message = _execute_indent_lines(
                            self, file_path, start_pattern, end_pattern, line_count, indent_levels, near_context, occurrence, change_id, dry_run
                        )
                    else:
                        result_message = "Error: Missing required parameters for IndentLines (file_path, start_pattern)"

                elif norm_tool_name == 'deleteline':
                    file_path = params.get('file_path')
                    line_number = params.get('line_number')
                    change_id = params.get('change_id')
                    dry_run = params.get('dry_run', False)

                    if file_path is not None and line_number is not None:
                        result_message = _execute_delete_line(
                            self, file_path, line_number, change_id, dry_run
                        )
                    else:
                        result_message = "Error: Missing required parameters for DeleteLine (file_path, line_number)"

                elif norm_tool_name == 'deletelines':
                    file_path = params.get('file_path')
                    start_line = params.get('start_line')
                    end_line = params.get('end_line')
                    change_id = params.get('change_id')
                    dry_run = params.get('dry_run', False)

                    if file_path is not None and start_line is not None and end_line is not None:
                        result_message = _execute_delete_lines(
                            self, file_path, start_line, end_line, change_id, dry_run
                        )
                    else:
                        result_message = "Error: Missing required parameters for DeleteLines (file_path, start_line, end_line)"

                elif norm_tool_name == 'undochange':
                    change_id = params.get('change_id')
                    file_path = params.get('file_path')
                     
                    result_message = _execute_undo_change(self, change_id, file_path)
                 
                elif norm_tool_name == 'listchanges':
                    file_path = params.get('file_path')
                    limit = params.get('limit', 10)
                    
                    result_message = _execute_list_changes(self, file_path, limit)

                elif norm_tool_name == 'extractlines':
                    source_file_path = params.get('source_file_path')
                    target_file_path = params.get('target_file_path')
                    start_pattern = params.get('start_pattern')
                    end_pattern = params.get('end_pattern')
                    line_count = params.get('line_count')
                    near_context = params.get('near_context')
                    occurrence = params.get('occurrence', 1)
                    dry_run = params.get('dry_run', False)

                    if source_file_path and target_file_path and start_pattern:
                        result_message = _execute_extract_lines(
                            self, source_file_path, target_file_path, start_pattern, end_pattern,
                            line_count, near_context, occurrence, dry_run
                        )
                    else:
                        result_message = "Error: Missing required parameters for ExtractLines (source_file_path, target_file_path, start_pattern)"

                elif norm_tool_name == 'shownumberedcontext':
                    file_path = params.get('file_path')
                    pattern = params.get('pattern')
                    line_number = params.get('line_number')
                    context_lines = params.get('context_lines', 3) # Default context

                    if file_path is not None and (pattern is not None or line_number is not None):
                        result_message = execute_show_numbered_context(
                            self, file_path, pattern, line_number, context_lines
                        )
                    else:
                        result_message = "Error: Missing required parameters for ViewNumberedContext (file_path and either pattern or line_number)"

                else:
                    result_message = f"Error: Unknown tool name '{tool_name}'"

            except Exception as e:
                result_message = f"Error executing {tool_name}: {str(e)}"
                self.io.tool_error(f"Error during {tool_name} execution: {e}\n{traceback.format_exc()}")

            if result_message:
                result_messages.append(f"[Result ({tool_name}): {result_message}]")

            # Note: We don't add the tool call string back to processed_content

        # Update internal counter
        self.tool_call_count += call_count

        # Return the content with tool calls removed
        modified_content = processed_content

        # Update internal counter
        self.tool_call_count += call_count

        return modified_content, result_messages, tool_calls_found, content_before_separator

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





    def _add_file_to_context(self, file_path, explicit=False):
        """
        Helper method to add a file to context as read-only.

        Parameters:
        - file_path: Path to the file to add
        - explicit: Whether this was an explicit view command (vs. implicit through ViewFilesAtGlob/ViewFilesMatching)
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
                self.io.tool_output(f"📎 Viewed '{file_path}' (added to context as read-only)")
                return f"Viewed file (added to context as read-only)"
            else:
                # For implicit adds (from ViewFilesAtGlob/ViewFilesMatching), just return success
                return f"Added file to context as read-only"

        except Exception as e:
            self.io.tool_error(f"Error adding file '{file_path}' for viewing: {str(e)}")
            return f"Error adding file for viewing: {str(e)}"


    




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
        
        # In navigator mode, we *only* add files via explicit tool commands (`View`, `ViewFilesAtGlob`, etc.).
        # Do nothing here for implicit mentions.
        pass


    def check_for_file_mentions(self, content):
        """
        Override parent's method to use our own file processing logic.

        Override parent's method to disable implicit file mention handling in navigator mode.
        Files should only be added via explicit tool commands (`View`, `ViewFilesAtGlob`, `ViewFilesMatching`, `ViewFilesWithSymbol`).
        """
        # Do nothing - disable implicit file adds in navigator mode.
        pass
        
    def preproc_user_input(self, inp):
        """
        Override parent's method to wrap user input in a context block.
        This clearly delineates user input from other sections in the context window.
        """
        # First apply the parent's preprocessing
        inp = super().preproc_user_input(inp)
        
        # If we still have input after preprocessing, wrap it in a context block
        if inp and not inp.startswith("<context name=\"user_input\">"):
            inp = f"<context name=\"user_input\">\n{inp}\n</context>"
        
        return inp

    def get_directory_structure(self):
        """
        Generate a structured directory listing of the project file structure.
        Returns a formatted string representation of the directory tree.
        """
        if not self.use_enhanced_context:
            return None
            
        try:
            # Start with the header
            result = "<context name=\"directoryStructure\">\n"
            result += "## Project File Structure\n\n"
            result += "Below is a snapshot of this project's file structure at the current time. It skips over .gitignore patterns.\n\n"
            
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
        Generate a git status context block for repository information.
        Returns a formatted string with git branch, status, and recent commits.
        """
        if not self.use_enhanced_context or not self.repo:
            return None
            
        try:
            result = "<context name=\"gitStatus\">\n"
            result += "## Git Repository Status\n\n"
            result += "This is a snapshot of the git status at the current time.\n"
            
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
        

    def _find_occurrences(self, content, pattern, near_context=None):
        """Find all occurrences of pattern, optionally filtered by near_context."""
        occurrences = []
        start = 0
        while True:
            index = content.find(pattern, start)
            if index == -1:
                break
            
            if near_context:
                # Check if near_context is within a window around the match
                window_start = max(0, index - 200)
                window_end = min(len(content), index + len(pattern) + 200)
                window = content[window_start:window_end]
                if near_context in window:
                    occurrences.append(index)
            else:
                occurrences.append(index)
            
            start = index + 1 # Move past this occurrence's start
        return occurrences

    # ------------------- Helper for finding occurrences -------------------


    
    
            
            
             
            
    
    


