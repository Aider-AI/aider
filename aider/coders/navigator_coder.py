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

from .base_coder import Coder
from .editblock_coder import find_original_update_blocks, do_replace, find_similar_lines
from .navigator_prompts import NavigatorPrompts
from aider.repo import ANY_GIT_ERROR
from aider import urls
# Import run_cmd for potentially interactive execution and run_cmd_subprocess for guaranteed non-interactive
from aider.run_cmd import run_cmd, run_cmd_subprocess
# Import the change tracker
from aider.change_tracker import ChangeTracker

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

    def format_chat_chunks(self):
        """
        Override parent's format_chat_chunks to include enhanced context blocks with a 
        cleaner, more hierarchical structure for better organization.
        """
        # First get the normal chat chunks from the parent method
        chunks = super().format_chat_chunks()
        
        # If enhanced context blocks are enabled, prepend them to the current messages
        if self.use_enhanced_context:
            # Create environment info context block
            env_context = self.get_environment_info()
            
            # Get directory structure
            dir_structure = self.get_directory_structure()
            
            # Get git status
            git_status = self.get_git_status()
            
            # Get current context summary
            context_summary = self.get_context_summary()
            
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
        
    def get_context_summary(self):
        """
        Generate a summary of the current file context, including editable and read-only files,
        along with token counts to encourage proactive context management.
        """
        if not self.use_enhanced_context:
            return None
            
        try:
            result = "<context name=\"context_summary\">\n"
            result += "## Current Context Overview\n\n"
            
            # Get model context limits
            max_input_tokens = self.main_model.info.get("max_input_tokens") or 0
            max_output_tokens = self.main_model.info.get("max_output_tokens") or 0
            if max_input_tokens:
                result += f"Model context limit: {max_input_tokens:,} tokens\n\n"
            
            # Calculate total tokens in context
            total_tokens = 0
            editable_tokens = 0
            readonly_tokens = 0
            
            # Track editable files
            if self.abs_fnames:
                result += "### Editable Files\n\n"
                editable_files = []
                
                for fname in sorted(self.abs_fnames):
                    rel_fname = self.get_rel_fname(fname)
                    content = self.io.read_text(fname)
                    if content is not None:
                        token_count = self.main_model.token_count(content)
                        total_tokens += token_count
                        editable_tokens += token_count
                        size_indicator = "🔴 Large" if token_count > 5000 else ("🟡 Medium" if token_count > 1000 else "🟢 Small")
                        editable_files.append(f"- {rel_fname}: {token_count:,} tokens ({size_indicator})")
                
                if editable_files:
                    result += "\n".join(editable_files) + "\n\n"
                    result += f"**Total editable: {len(editable_files)} files, {editable_tokens:,} tokens**\n\n"
                else:
                    result += "No editable files in context\n\n"
            
            # Track read-only files
            if self.abs_read_only_fnames:
                result += "### Read-Only Files\n\n"
                readonly_files = []
                
                for fname in sorted(self.abs_read_only_fnames):
                    rel_fname = self.get_rel_fname(fname)
                    content = self.io.read_text(fname)
                    if content is not None:
                        token_count = self.main_model.token_count(content)
                        total_tokens += token_count
                        readonly_tokens += token_count
                        size_indicator = "🔴 Large" if token_count > 5000 else ("🟡 Medium" if token_count > 1000 else "🟢 Small")
                        readonly_files.append(f"- {rel_fname}: {token_count:,} tokens ({size_indicator})")
                
                if readonly_files:
                    result += "\n".join(readonly_files) + "\n\n"
                    result += f"**Total read-only: {len(readonly_files)} files, {readonly_tokens:,} tokens**\n\n"
                else:
                    result += "No read-only files in context\n\n"
            
            # Summary and recommendations
            result += f"**Total context usage: {total_tokens:,} tokens**"
            
            if max_input_tokens:
                percentage = (total_tokens / max_input_tokens) * 100
                result += f" ({percentage:.1f}% of limit)"
                
                if percentage > 80:
                    result += "\n\n⚠️ **Context is getting full!** Consider removing files with:\n"
                    result += "- `[tool_call(Remove, file_path=\"path/to/large_file.ext\")]` for files no longer needed\n"
                    result += "- Focus on keeping only essential files in context for best results"
                
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

        # Process tool commands: returns content with tool calls removed, results, and flag if any tool calls were found
        processed_content, result_messages, tool_calls_found = self._process_tool_commands(content)

        # Since we are no longer suppressing, the partial_response_content IS the final content.
        # We might want to update it to the processed_content (without tool calls) if we don't
        # want the raw tool calls to remain in the final assistant message history.
        # Let's update it for cleaner history.
        self.partial_response_content = processed_content.strip()

        # Process implicit file mentions using the content *after* tool calls were removed
        self._process_file_mentions(processed_content)

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
        Returns processed content, result messages, and a flag indicating if any tool calls were found.
        """
        result_messages = []
        modified_content = content # Start with original content
        tool_calls_found = False
        call_count = 0
        max_calls = self.max_tool_calls

        # Find tool calls using a more robust method
        processed_content = ""
        last_index = 0
        start_marker = "[tool_call("
        end_marker = "]" # The parenthesis balancing finds the ')', we just need the final ']'

        while True:
            start_pos = content.find(start_marker, last_index)
            if start_pos == -1:
                processed_content += content[last_index:]
                break

            # Check for escaped tool call: \[tool_call(
            if start_pos > 0 and content[start_pos - 1] == '\\':
                # Append the content including the escaped marker
                # We append up to start_pos + len(start_marker) to include the marker itself.
                processed_content += content[last_index : start_pos + len(start_marker)]
                # Update last_index to search after this escaped marker
                last_index = start_pos + len(start_marker)
                continue # Continue searching for the next potential marker

            # Append content before the (non-escaped) tool call
            processed_content += content[last_index:start_pos]

            scan_start_pos = start_pos + len(start_marker)
            paren_level = 1
            in_single_quotes = False
            in_double_quotes = False
            escaped = False
            end_paren_pos = -1

            # Scan to find the matching closing parenthesis, respecting quotes
            for i in range(scan_start_pos, len(content)):
                char = content[i]

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
                for j in range(expected_end_marker_start, len(content)):
                    if not content[j].isspace():
                        actual_end_marker_start = j
                        # Check if the found character is the end marker ']'
                        if content[actual_end_marker_start] == end_marker:
                            end_marker_found = True
                        break # Stop searching after first non-whitespace char

            if not end_marker_found:
                # Malformed call: couldn't find matching ')' or the subsequent ']'
                self.io.tool_warning(f"Malformed tool call starting at index {start_pos}. Skipping (end_paren_pos={end_paren_pos}, end_marker_found={end_marker_found}).")
                # Append the start marker itself to processed content so it's not lost
                processed_content += start_marker
                last_index = scan_start_pos # Continue searching after the marker
                continue

            # Found a potential tool call
            # Adjust full_match_str and last_index based on the actual end marker ']' position
            full_match_str = content[start_pos : actual_end_marker_start + 1] # End marker ']' is 1 char
            inner_content = content[scan_start_pos:end_paren_pos].strip()
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
                        result_message = self._execute_view_files_at_glob(pattern)
                    else:
                        result_message = "Error: Missing 'pattern' parameter for ViewFilesAtGlob"
                elif norm_tool_name == 'viewfilesmatching':
                    pattern = params.get('pattern')
                    file_pattern = params.get('file_pattern') # Optional
                    if pattern is not None:
                        result_message = self._execute_view_files_matching(pattern, file_pattern)
                    else:
                        result_message = "Error: Missing 'pattern' parameter for ViewFilesMatching"
                elif norm_tool_name == 'ls':
                    directory = params.get('directory')
                    if directory is not None:
                        result_message = self._execute_ls(directory)
                    else:
                        result_message = "Error: Missing 'directory' parameter for Ls"
                elif norm_tool_name == 'view':
                    file_path = params.get('file_path')
                    if file_path is not None:
                        result_message = self._execute_view(file_path)
                    else:
                        result_message = "Error: Missing 'file_path' parameter for View"
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
                elif norm_tool_name == 'viewfileswithsymbol':
                    symbol = params.get('symbol')
                    if symbol is not None:
                        result_message = self._execute_view_files_with_symbol(symbol)
                    else:
                        result_message = "Error: Missing 'symbol' parameter for ViewFilesWithSymbol"
                elif norm_tool_name == 'command':
                    command_string = params.get('command_string')
                    if command_string is not None:
                        result_message = self._execute_command(command_string)
                    else:
                        result_message = "Error: Missing 'command_string' parameter for Command"
                elif norm_tool_name == 'commandinteractive':
                    command_string = params.get('command_string')
                    if command_string is not None:
                        result_message = self._execute_command_interactive(command_string)
                    else:
                        result_message = "Error: Missing 'command_string' parameter for CommandInteractive"

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
                        result_message = self._execute_replace_text(
                            file_path, find_text, replace_text, near_context, occurrence, change_id, dry_run
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
                        result_message = self._execute_replace_all(
                            file_path, find_text, replace_text, change_id, dry_run
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
                        result_message = self._execute_insert_block(
                            file_path, content, after_pattern, before_pattern, near_context, occurrence, change_id, dry_run
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
                        result_message = self._execute_delete_block(
                            file_path, start_pattern, end_pattern, line_count, near_context, occurrence, change_id, dry_run
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
                        result_message = self._execute_replace_line(
                            file_path, line_number, new_content, change_id, dry_run
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
                        result_message = self._execute_replace_lines(
                            file_path, start_line, end_line, new_content, change_id, dry_run
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
                        result_message = self._execute_indent_lines(
                            file_path, start_pattern, end_pattern, line_count, indent_levels, near_context, occurrence, change_id, dry_run
                        )
                    else:
                        result_message = "Error: Missing required parameters for IndentLines (file_path, start_pattern)"
                 
                elif norm_tool_name == 'undochange':
                    change_id = params.get('change_id')
                    file_path = params.get('file_path')
                     
                    result_message = self._execute_undo_change(change_id, file_path)
                 
                elif norm_tool_name == 'listchanges':
                    file_path = params.get('file_path')
                    limit = params.get('limit', 10)
                    
                    result_message = self._execute_list_changes(file_path, limit)

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
                        result_message = self._execute_extract_lines(
                            source_file_path, target_file_path, start_pattern, end_pattern,
                            line_count, near_context, occurrence, dry_run
                        )
                    else:
                        result_message = "Error: Missing required parameters for ExtractLines (source_file_path, target_file_path, start_pattern)"

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

        return modified_content, result_messages, tool_calls_found

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

    def _execute_view_files_at_glob(self, pattern):
        """
        Execute a glob pattern and add matching files to context as read-only.

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
            self.io.tool_error(f"Error in ViewFilesAtGlob: {str(e)}")
            return f"Error: {str(e)}"

    def _execute_view_files_matching(self, search_pattern, file_pattern=None):
        """
        Search for pattern in files and add matching files to context as read-only.

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
            self.io.tool_error(f"Error in ViewFilesMatching: {str(e)}")
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

    def _execute_view(self, file_path):
        """
        Explicitly add a file to context as read-only.

        This gives the LLM explicit control over what files to view,
        rather than relying on indirect mentions.
        """
        try:
            # Use the helper, marking it as an explicit view request
            return self._add_file_to_context(file_path, explicit=True)
        except Exception as e:
            self.io.tool_error(f"Error viewing file: {str(e)}")
            return f"Error: {str(e)}"

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
            
            # Check if file is already editable
            if abs_path in self.abs_fnames:
                self.io.tool_output(f"📝 File '{file_path}' is already editable")
                return f"File is already editable"

            # Check if file exists on disk
            if not os.path.isfile(abs_path):
                self.io.tool_output(f"⚠️ File '{file_path}' not found")
                return f"Error: File not found"

            # File exists, is not editable, might be read-only or not in context yet
            was_read_only = False
            if abs_path in self.abs_read_only_fnames:
                self.abs_read_only_fnames.remove(abs_path)
                was_read_only = True

            # Add to editable files
            self.abs_fnames.add(abs_path)

            if was_read_only:
                self.io.tool_output(f"📝 Moved '{file_path}' from read-only to editable")
                return f"File is now editable (moved from read-only)"
            else:
                # File was not previously in context at all
                self.io.tool_output(f"📝 Added '{file_path}' directly to editable context")
                # Track if added during exploration? Maybe not needed for direct MakeEditable.
                # self.files_added_in_exploration.add(rel_path) # Consider if needed
                return f"File is now editable (added directly)"
        except Exception as e:
            self.io.tool_error(f"Error in MakeEditable for '{file_path}': {str(e)}")
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

    def _execute_view_files_with_symbol(self, symbol):
        """
        Find files containing a specific symbol and add them to context as read-only.
        """
        try:
            if not self.repo_map:
                self.io.tool_output("⚠️ Repo map not available, cannot use ViewFilesWithSymbol tool.")
                return "Repo map not available"

            if not symbol:
                return "Error: Missing 'symbol' parameter for ViewFilesWithSymbol"

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
            self.io.tool_error(f"Error in ViewFilesWithSymbol: {str(e)}")
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

    def _execute_command_interactive(self, command_string):
        """
        Execute an interactive shell command using run_cmd (which uses pexpect/PTY).
        """
        try:
            self.io.tool_output(f"⚙️ Starting interactive shell command: {command_string}")
            self.io.tool_output(">>> You may need to interact with the command below <<<")

            # Use run_cmd which handles PTY logic
            exit_status, combined_output = run_cmd(
                command_string,
                verbose=self.verbose, # Pass verbose flag
                error_print=self.io.tool_error, # Use io for error printing
                cwd=self.root # Execute in the project root
            )

            self.io.tool_output(">>> Interactive command finished <<<")

            # Format the output for the result message, include more content
            output_content = combined_output or ""
            # Use the existing token threshold constant as the character limit for truncation
            output_limit = self.large_file_token_threshold
            if len(output_content) > output_limit:
                # Truncate and add a clear message using the constant value
                output_content = output_content[:output_limit] + f"\n... (output truncated at {output_limit} characters, based on large_file_token_threshold)"

            if exit_status == 0:
                return f"Interactive command finished successfully (exit code 0). Output:\n{output_content}"
            else:
                return f"Interactive command finished with exit code {exit_status}. Output:\n{output_content}"

        except Exception as e:
            self.io.tool_error(f"Error executing interactive shell command '{command_string}': {str(e)}")
            # Optionally include traceback for debugging if verbose
            # if self.verbose:
            #     self.io.tool_error(traceback.format_exc())
            return f"Error executing interactive command: {str(e)}"

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
        
    # ------------------- Helper for finding occurrences -------------------

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

    # ------------------- Granular Editing Tools -------------------
    
    def _execute_replace_text(self, file_path, find_text, replace_text, near_context=None, occurrence=1, change_id=None, dry_run=False):
        """
        Replace specific text with new text, optionally using nearby context for disambiguation.
        
        Parameters:
        - file_path: Path to the file to modify
        - find_text: Text to find and replace
        - replace_text: Text to replace it with
        - near_context: Optional text nearby to help locate the correct instance
        - occurrence: Which occurrence to replace (1-based index, or -1 for last)
        - change_id: Optional ID for tracking the change
        
        - change_id: Optional ID for tracking the change
        - dry_run: If True, simulate the change without modifying the file
         
        - change_id: Optional ID for tracking the change
        - dry_run: If True, simulate the change without modifying the file
         
        Returns a result message.
        """
        try:
            # Get absolute file path
            abs_path = self.abs_root_path(file_path)
            rel_path = self.get_rel_fname(abs_path)
            
            # Check if file exists
            if not os.path.isfile(abs_path):
                self.io.tool_error(f"File '{file_path}' not found")
                return f"Error: File not found"
                
            # Check if file is in editable context
            if abs_path not in self.abs_fnames:
                if abs_path in self.abs_read_only_fnames:
                    self.io.tool_error(f"File '{file_path}' is read-only. Use MakeEditable first.")
                    return f"Error: File is read-only. Use MakeEditable first."
                else:
                    self.io.tool_error(f"File '{file_path}' not in context")
                    return f"Error: File not in context"
             
            # Reread file content immediately before modification (Fixes Point 3: Stale Reads)
            content = self.io.read_text(abs_path)
            if content is None:
                # Provide more specific error (Improves Point 4)
                self.io.tool_error(f"Could not read file '{file_path}' before ReplaceText operation.")
                return f"Error: Could not read file '{file_path}'"
            # Find occurrences using helper function
            occurrences = self._find_occurrences(content, find_text, near_context)
             
            if not occurrences:
                err_msg = f"Text '{find_text}' not found"
                if near_context:
                    err_msg += f" near context '{near_context}'"
                err_msg += f" in file '{file_path}'."
                self.io.tool_error(err_msg)
                return f"Error: {err_msg}" # Improve Point 4

            # Select the occurrence (handle 1-based index and -1 for last)
            num_occurrences = len(occurrences)
            try:
                occurrence = int(occurrence) # Ensure occurrence is an integer
                if occurrence == -1:  # Last occurrence
                    target_idx = num_occurrences - 1
                elif occurrence > 0 and occurrence <= num_occurrences:
                    target_idx = occurrence - 1 # Convert 1-based to 0-based
                else:
                    err_msg = f"Occurrence number {occurrence} is out of range. Found {num_occurrences} occurrences of '{find_text}'"
                    if near_context: err_msg += f" near '{near_context}'"
                    err_msg += f" in '{file_path}'."
                    self.io.tool_error(err_msg)
                    return f"Error: {err_msg}" # Improve Point 4
            except ValueError:
                self.io.tool_error(f"Invalid occurrence value: '{occurrence}'. Must be an integer.")
                return f"Error: Invalid occurrence value '{occurrence}'"

            start_index = occurrences[target_idx]
            
            # Perform the replacement
            original_content = content
            new_content = content[:start_index] + replace_text + content[start_index + len(find_text):]
            
            if original_content == new_content:
                self.io.tool_warning(f"No changes made: replacement text is identical to original")
                return f"Warning: No changes made (replacement identical to original)"
             
            # Generate diff for feedback
            diff_example = self._generate_diff_snippet(original_content, start_index, len(find_text), replace_text)

            # Handle dry run (Implements Point 6)
            if dry_run:
                self.io.tool_output(f"Dry run: Would replace occurrence {occurrence} of '{find_text}' in {file_path}")
                return f"Dry run: Would replace text (occurrence {occurrence}). Diff snippet:\n{diff_example}"

            # --- Apply Change (Not dry run) ---
            self.io.write_text(abs_path, new_content)
             
            # Track the change
            try:
                metadata = {
                    'start_index': start_index,
                    'find_text': find_text,
                    'replace_text': replace_text,
                    'near_context': near_context,
                    'occurrence': occurrence
                }
                change_id = self.change_tracker.track_change(
                    file_path=rel_path,
                    change_type='replacetext',
                    original_content=original_content,
                    new_content=new_content,
                    metadata=metadata,
                    change_id=change_id
                )
            except Exception as track_e:
                self.io.tool_error(f"Error tracking change for ReplaceText: {track_e}")
                # Continue even if tracking fails, but warn
                change_id = "TRACKING_FAILED"

            self.aider_edited_files.add(rel_path)
             
            # Improve feedback (Point 5 & 6)
            occurrence_str = f"occurrence {occurrence}" if num_occurrences > 1 else "text"
            self.io.tool_output(f"✅ Replaced {occurrence_str} in {file_path} (change_id: {change_id})")
            return f"Successfully replaced {occurrence_str} (change_id: {change_id}). Diff snippet:\n{diff_example}"
                 
        except Exception as e:
            self.io.tool_error(f"Error in ReplaceText: {str(e)}\n{traceback.format_exc()}") # Add traceback
            return f"Error: {str(e)}"
    
    def _execute_replace_all(self, file_path, find_text, replace_text, change_id=None, dry_run=False):
        """
        Replace all occurrences of text in a file.
        
        Parameters:
        - file_path: Path to the file to modify
        - find_text: Text to find and replace
        - replace_text: Text to replace it with
        - change_id: Optional ID for tracking the change
        
        Returns a result message.
        """
        try:
            # Get absolute file path
            abs_path = self.abs_root_path(file_path)
            rel_path = self.get_rel_fname(abs_path)
            
            # Check if file exists
            if not os.path.isfile(abs_path):
                self.io.tool_error(f"File '{file_path}' not found")
                return f"Error: File not found"
                
            # Check if file is in editable context
            if abs_path not in self.abs_fnames:
                if abs_path in self.abs_read_only_fnames:
                    self.io.tool_error(f"File '{file_path}' is read-only. Use MakeEditable first.")
                    return f"Error: File is read-only. Use MakeEditable first."
                else:
                    self.io.tool_error(f"File '{file_path}' not in context")
                    return f"Error: File not in context"
             
            # Reread file content immediately before modification (Fixes Point 3: Stale Reads)
            content = self.io.read_text(abs_path)
            if content is None:
                # Provide more specific error (Improves Point 4)
                self.io.tool_error(f"Could not read file '{file_path}' before ReplaceAll operation.")
                return f"Error: Could not read file '{file_path}'"
            
            # Count occurrences
            count = content.count(find_text)
            if count == 0:
                self.io.tool_warning(f"Text '{find_text}' not found in file")
                return f"Warning: Text not found in file"
            
            # Perform the replacement
            original_content = content
            new_content = content.replace(find_text, replace_text)
            
            if original_content == new_content:
                self.io.tool_warning(f"No changes made: replacement text is identical to original")
                return f"Warning: No changes made (replacement identical to original)"
             
            # Generate diff for feedback (more comprehensive for ReplaceAll)
            diff_examples = self._generate_diff_chunks(original_content, find_text, replace_text)

            # Handle dry run (Implements Point 6)
            if dry_run:
                self.io.tool_output(f"Dry run: Would replace {count} occurrences of '{find_text}' in {file_path}")
                return f"Dry run: Would replace {count} occurrences. Diff examples:\n{diff_examples}"

            # --- Apply Change (Not dry run) ---
            self.io.write_text(abs_path, new_content)
             
            # Track the change
            try:
                metadata = {
                    'find_text': find_text,
                    'replace_text': replace_text,
                    'occurrences': count
                }
                change_id = self.change_tracker.track_change(
                    file_path=rel_path,
                    change_type='replaceall',
                    original_content=original_content,
                    new_content=new_content,
                    metadata=metadata,
                    change_id=change_id
                )
            except Exception as track_e:
                self.io.tool_error(f"Error tracking change for ReplaceAll: {track_e}")
                # Continue even if tracking fails, but warn
                change_id = "TRACKING_FAILED"

            self.aider_edited_files.add(rel_path)
             
            # Improve feedback (Point 6)
            self.io.tool_output(f"✅ Replaced {count} occurrences in {file_path} (change_id: {change_id})")
            return f"Successfully replaced {count} occurrences (change_id: {change_id}). Diff examples:\n{diff_examples}"
                 
        except Exception as e:
            self.io.tool_error(f"Error in ReplaceAll: {str(e)}\n{traceback.format_exc()}") # Add traceback
            return f"Error: {str(e)}"
            
    def _execute_insert_block(self, file_path, content, after_pattern=None, before_pattern=None, near_context=None, occurrence=1, change_id=None, dry_run=False):
        """
        Insert a block of text after or before a specified pattern.
        
        Parameters:
        - file_path: Path to the file to modify
        - content: Text block to insert
        - after_pattern: Pattern after which to insert the block (line containing this pattern) - specify one of after/before
        - before_pattern: Pattern before which to insert the block (line containing this pattern) - specify one of after/before
        - near_context: Optional text nearby to help locate the correct instance of the pattern
        - occurrence: Which occurrence of the pattern to use (1-based index, or -1 for last)
        - change_id: Optional ID for tracking the change
        - dry_run: If True, simulate the change without modifying the file
         
        Returns a result message.
        """
        try:
            # Get absolute file path
            abs_path = self.abs_root_path(file_path)
            rel_path = self.get_rel_fname(abs_path)
            
            # Check if file exists
            if not os.path.isfile(abs_path):
                self.io.tool_error(f"File '{file_path}' not found")
                return f"Error: File not found"
                
            # Check if file is in editable context
            if abs_path not in self.abs_fnames:
                if abs_path in self.abs_read_only_fnames:
                    self.io.tool_error(f"File '{file_path}' is read-only. Use MakeEditable first.")
                    return f"Error: File is read-only. Use MakeEditable first."
                else:
                    self.io.tool_error(f"File '{file_path}' not in context")
                    return f"Error: File not in context"
             
            # Reread file content immediately before modification (Fixes Point 3: Stale Reads)
            file_content = self.io.read_text(abs_path)
            if file_content is None:
                # Provide more specific error (Improves Point 4)
                self.io.tool_error(f"Could not read file '{file_path}' before InsertBlock operation.")
                return f"Error: Could not read file '{file_path}'"
            
            # Validate we have either after_pattern or before_pattern, but not both
            if after_pattern and before_pattern:
                self.io.tool_error("Cannot specify both after_pattern and before_pattern")
                return "Error: Cannot specify both after_pattern and before_pattern"
            if not after_pattern and not before_pattern:
                self.io.tool_error("Must specify either after_pattern or before_pattern")
                return "Error: Must specify either after_pattern or before_pattern"
            
            # Split into lines for easier handling
            lines = file_content.splitlines()
            original_content = file_content
             
            # Find occurrences of the pattern (either after_pattern or before_pattern)
            pattern = after_pattern if after_pattern else before_pattern
            pattern_type = "after" if after_pattern else "before"
             
            # Find line indices containing the pattern
            pattern_line_indices = []
            for i, line in enumerate(lines):
                if pattern in line:
                    # If near_context is provided, check if it's nearby
                    if near_context:
                        context_window_start = max(0, i - 5) # Check 5 lines before/after
                        context_window_end = min(len(lines), i + 6)
                        context_block = "\n".join(lines[context_window_start:context_window_end])
                        if near_context in context_block:
                            pattern_line_indices.append(i)
                    else:
                        pattern_line_indices.append(i)

            if not pattern_line_indices:
                err_msg = f"Pattern '{pattern}' not found"
                if near_context: err_msg += f" near context '{near_context}'"
                err_msg += f" in file '{file_path}'."
                self.io.tool_error(err_msg)
                return f"Error: {err_msg}" # Improve Point 4

            # Select the occurrence (Implements Point 5)
            num_occurrences = len(pattern_line_indices)
            try:
                occurrence = int(occurrence) # Ensure occurrence is an integer
                if occurrence == -1: # Last occurrence
                    target_idx = num_occurrences - 1
                elif occurrence > 0 and occurrence <= num_occurrences:
                    target_idx = occurrence - 1 # Convert 1-based to 0-based
                else:
                    err_msg = f"Occurrence number {occurrence} is out of range for pattern '{pattern}'. Found {num_occurrences} occurrences"
                    if near_context: err_msg += f" near '{near_context}'"
                    err_msg += f" in '{file_path}'."
                    self.io.tool_error(err_msg)
                    return f"Error: {err_msg}" # Improve Point 4
            except ValueError:
                self.io.tool_error(f"Invalid occurrence value: '{occurrence}'. Must be an integer.")
                return f"Error: Invalid occurrence value '{occurrence}'"

            # Determine the final insertion line index
            insertion_line_idx = pattern_line_indices[target_idx]
            if pattern_type == "after":
                insertion_line_idx += 1 # Insert on the line *after* the matched line
            # Prepare the content to insert
            content_lines = content.splitlines()
             
            # Create the new lines array
            new_lines = lines[:insertion_line_idx] + content_lines + lines[insertion_line_idx:]
            new_content = '\n'.join(new_lines) # Use '\n' to match io.write_text behavior
             
            if original_content == new_content:
                self.io.tool_warning(f"No changes made: insertion would not change file")
                return f"Warning: No changes made (insertion would not change file)"

            # Generate diff for feedback
            diff_snippet = self._generate_diff_snippet_insert(original_content, insertion_line_idx, content_lines)

            # Handle dry run (Implements Point 6)
            if dry_run:
                occurrence_str = f"occurrence {occurrence} of " if num_occurrences > 1 else ""
                self.io.tool_output(f"Dry run: Would insert block {pattern_type} {occurrence_str}pattern '{pattern}' in {file_path}")
                return f"Dry run: Would insert block. Diff snippet:\n{diff_snippet}"

            # --- Apply Change (Not dry run) ---
            self.io.write_text(abs_path, new_content)
             
            # Track the change
            try:
                metadata = {
                    'insertion_line_idx': insertion_line_idx,
                    'after_pattern': after_pattern,
                    'before_pattern': before_pattern,
                    'near_context': near_context,
                    'occurrence': occurrence,
                    'content': content
                }
                change_id = self.change_tracker.track_change(
                    file_path=rel_path,
                    change_type='insertblock',
                    original_content=original_content,
                    new_content=new_content,
                    metadata=metadata,
                    change_id=change_id
                )
            except Exception as track_e:
                self.io.tool_error(f"Error tracking change for InsertBlock: {track_e}")
                change_id = "TRACKING_FAILED"

            self.aider_edited_files.add(rel_path)
             
            # Improve feedback (Point 5 & 6)
            occurrence_str = f"occurrence {occurrence} of " if num_occurrences > 1 else ""
            self.io.tool_output(f"✅ Inserted block {pattern_type} {occurrence_str}pattern in {file_path} (change_id: {change_id})")
            return f"Successfully inserted block (change_id: {change_id}). Diff snippet:\n{diff_snippet}"
                 
        except Exception as e:
            self.io.tool_error(f"Error in InsertBlock: {str(e)}\n{traceback.format_exc()}") # Add traceback
            return f"Error: {str(e)}"
            
    def _execute_delete_block(self, file_path, start_pattern, end_pattern=None, line_count=None, near_context=None, occurrence=1, change_id=None, dry_run=False):
        """
        Delete a block of text between start_pattern and end_pattern (inclusive).
        
        Parameters:
        - file_path: Path to the file to modify
        - start_pattern: Pattern marking the start of the block to delete (line containing this pattern)
        - end_pattern: Optional pattern marking the end of the block (line containing this pattern)
        - line_count: Optional number of lines to delete (alternative to end_pattern)
        - near_context: Optional text nearby to help locate the correct instance of the start_pattern
        - occurrence: Which occurrence of the start_pattern to use (1-based index, or -1 for last)
        - change_id: Optional ID for tracking the change
        - dry_run: If True, simulate the change without modifying the file
         
        Returns a result message.
        """
        try:
            # Get absolute file path
            abs_path = self.abs_root_path(file_path)
            rel_path = self.get_rel_fname(abs_path)
            
            # Check if file exists
            if not os.path.isfile(abs_path):
                self.io.tool_error(f"File '{file_path}' not found")
                return f"Error: File not found"
                
            # Check if file is in editable context
            if abs_path not in self.abs_fnames:
                if abs_path in self.abs_read_only_fnames:
                    self.io.tool_error(f"File '{file_path}' is read-only. Use MakeEditable first.")
                    return f"Error: File is read-only. Use MakeEditable first."
                else:
                    self.io.tool_error(f"File '{file_path}' not in context")
                    return f"Error: File not in context"
             
            # Reread file content immediately before modification (Fixes Point 3: Stale Reads)
            file_content = self.io.read_text(abs_path)
            if file_content is None:
                # Provide more specific error (Improves Point 4)
                self.io.tool_error(f"Could not read file '{file_path}' before DeleteBlock operation.")
                return f"Error: Could not read file '{file_path}'"
            
            # Validate we have either end_pattern or line_count, but not both
            if end_pattern and line_count:
                self.io.tool_error("Cannot specify both end_pattern and line_count")
                return "Error: Cannot specify both end_pattern and line_count"
            
            # Split into lines for easier handling
            lines = file_content.splitlines()
            original_content = file_content
             
            # Find occurrences of the start_pattern (Implements Point 5)
            start_pattern_line_indices = []
            for i, line in enumerate(lines):
                if start_pattern in line:
                    # If near_context is provided, check if it's nearby
                    if near_context:
                        context_window_start = max(0, i - 5) # Check 5 lines before/after
                        context_window_end = min(len(lines), i + 6)
                        context_block = "\n".join(lines[context_window_start:context_window_end])
                        if near_context in context_block:
                            start_pattern_line_indices.append(i)
                    else:
                        start_pattern_line_indices.append(i)

            if not start_pattern_line_indices:
                err_msg = f"Start pattern '{start_pattern}' not found"
                if near_context: err_msg += f" near context '{near_context}'"
                err_msg += f" in file '{file_path}'."
                self.io.tool_error(err_msg)
                return f"Error: {err_msg}" # Improve Point 4

            # Select the occurrence for the start pattern
            num_occurrences = len(start_pattern_line_indices)
            try:
                occurrence = int(occurrence) # Ensure occurrence is an integer
                if occurrence == -1: # Last occurrence
                    target_idx = num_occurrences - 1
                elif occurrence > 0 and occurrence <= num_occurrences:
                    target_idx = occurrence - 1 # Convert 1-based to 0-based
                else:
                    err_msg = f"Occurrence number {occurrence} is out of range for start pattern '{start_pattern}'. Found {num_occurrences} occurrences"
                    if near_context: err_msg += f" near '{near_context}'"
                    err_msg += f" in '{file_path}'."
                    self.io.tool_error(err_msg)
                    return f"Error: {err_msg}" # Improve Point 4
            except ValueError:
                self.io.tool_error(f"Invalid occurrence value: '{occurrence}'. Must be an integer.")
                return f"Error: Invalid occurrence value '{occurrence}'"

            start_line = start_pattern_line_indices[target_idx]
            occurrence_str = f"occurrence {occurrence} of " if num_occurrences > 1 else "" # For messages
            # Find the end line based on end_pattern or line_count
            end_line = -1
            if end_pattern:
                # Search for end_pattern *after* the selected start_line
                for i in range(start_line, len(lines)): # Include start_line itself if start/end are same line
                    if end_pattern in lines[i]:
                        end_line = i
                        break
                 
                if end_line == -1:
                    # Improve error message (Point 4)
                    err_msg = f"End pattern '{end_pattern}' not found after {occurrence_str}start pattern '{start_pattern}' (line {start_line + 1}) in '{file_path}'."
                    self.io.tool_error(err_msg)
                    return f"Error: {err_msg}"
            elif line_count:
                try:
                    line_count = int(line_count)
                    if line_count <= 0:
                        raise ValueError("Line count must be positive")
                    # Calculate end line based on start line and line count
                    end_line = min(start_line + line_count - 1, len(lines) - 1)
                except ValueError:
                    self.io.tool_error(f"Invalid line_count value: '{line_count}'. Must be a positive integer.")
                    return f"Error: Invalid line_count value '{line_count}'"
            else:
                # If neither end_pattern nor line_count is specified, delete just the start line
                end_line = start_line
            # Prepare the deletion
            deleted_lines = lines[start_line:end_line+1]
            new_lines = lines[:start_line] + lines[end_line+1:]
            new_content = '\n'.join(new_lines) # Use '\n' to match io.write_text behavior
             
            if original_content == new_content:
                self.io.tool_warning(f"No changes made: deletion would not change file")
                return f"Warning: No changes made (deletion would not change file)"

            # Generate diff for feedback
            diff_snippet = self._generate_diff_snippet_delete(original_content, start_line, end_line)

            # Handle dry run (Implements Point 6)
            if dry_run:
                self.io.tool_output(f"Dry run: Would delete lines {start_line+1}-{end_line+1} (based on {occurrence_str}start pattern '{start_pattern}') in {file_path}")
                return f"Dry run: Would delete block. Diff snippet:\n{diff_snippet}"

            # --- Apply Change (Not dry run) ---
            self.io.write_text(abs_path, new_content)
             
            # Track the change
            try:
                metadata = {
                    'start_line': start_line + 1, # Store 1-based for consistency
                    'end_line': end_line + 1,   # Store 1-based
                    'start_pattern': start_pattern,
                    'end_pattern': end_pattern,
                    'line_count': line_count,
                    'near_context': near_context,
                    'occurrence': occurrence,
                    'deleted_content': '\n'.join(deleted_lines)
                }
                change_id = self.change_tracker.track_change(
                    file_path=rel_path,
                    change_type='deleteblock',
                    original_content=original_content,
                    new_content=new_content,
                    metadata=metadata,
                    change_id=change_id
                )
            except Exception as track_e:
                self.io.tool_error(f"Error tracking change for DeleteBlock: {track_e}")
                change_id = "TRACKING_FAILED"

            self.aider_edited_files.add(rel_path)
             
            # Improve feedback (Point 5 & 6)
            num_deleted = end_line - start_line + 1
            self.io.tool_output(f"✅ Deleted {num_deleted} lines (from {occurrence_str}start pattern) in {file_path} (change_id: {change_id})")
            return f"Successfully deleted {num_deleted} lines (change_id: {change_id}). Diff snippet:\n{diff_snippet}"
                 
        except Exception as e:
            self.io.tool_error(f"Error in DeleteBlock: {str(e)}\n{traceback.format_exc()}") # Add traceback
            return f"Error: {str(e)}"
             
    def _execute_undo_change(self, change_id=None, file_path=None): 
        """
        Undo a specific change by ID, or the last change to a file.
         
        Parameters:
        - change_id: ID of the change to undo
        - file_path: Path to file where the last change should be undone
         
          
        Returns a result message.
        """
        # Note: Undo does not have a dry_run parameter as it's inherently about reverting a previous action.
        try:
            # Validate parameters
            if change_id is None and file_path is None:
                self.io.tool_error("Must specify either change_id or file_path for UndoChange")
                return "Error: Must specify either change_id or file_path" # Improve Point 4
             
            # If file_path is specified, get the most recent change for that file
            if file_path: 
                abs_path = self.abs_root_path(file_path)
                rel_path = self.get_rel_fname(abs_path)
                  
                change_id = self.change_tracker.get_last_change(rel_path)
                if not change_id:
                    # Improve error message (Point 4)
                    self.io.tool_error(f"No tracked changes found for file '{file_path}' to undo.")
                    return f"Error: No changes found for file '{file_path}'"
            # Attempt to get undo information from the tracker
            success, message, change_info = self.change_tracker.undo_change(change_id)
              
            if not success:
                # Improve error message (Point 4) - message from tracker should be specific
                self.io.tool_error(f"Failed to undo change '{change_id}': {message}")
                return f"Error: {message}"
            
            # Apply the undo by restoring the original content
            if change_info:
                file_path = change_info['file_path']
                abs_path = self.abs_root_path(file_path)
                # Write the original content back to the file
                # No dry_run check here, as undo implies a real action
                self.io.write_text(abs_path, change_info['original'])
                self.aider_edited_files.add(file_path) # Track that the file was modified by the undo
                 
                change_type = change_info['type']
                # Improve feedback (Point 6)
                self.io.tool_output(f"✅ Undid {change_type} change '{change_id}' in {file_path}")
                return f"Successfully undid {change_type} change '{change_id}'."
            else:
                # This case should ideally not be reached if tracker returns success
                self.io.tool_error(f"Failed to undo change '{change_id}': Change info missing after successful tracker update.")
                return f"Error: Failed to undo change '{change_id}' (missing change info)"
                 
        except Exception as e:
            self.io.tool_error(f"Error in UndoChange: {str(e)}\n{traceback.format_exc()}") # Add traceback
            return f"Error: {str(e)}"
            
    def _execute_replace_line(self, file_path, line_number, new_content, change_id=None, dry_run=False):
        """
        Replace a specific line identified by line number.
        Useful for fixing errors identified by error messages or linters.
        
        Parameters:
        - file_path: Path to the file to modify
        - line_number: The line number to replace (1-based)
        - new_content: New content for the line
        - change_id: Optional ID for tracking the change
        - dry_run: If True, simulate the change without modifying the file
         
        Returns a result message.
        """
        try:
            # Get absolute file path
            abs_path = self.abs_root_path(file_path)
            rel_path = self.get_rel_fname(abs_path)
            
            # Check if file exists
            if not os.path.isfile(abs_path):
                self.io.tool_error(f"File '{file_path}' not found")
                return f"Error: File not found"
                
            # Check if file is in editable context
            if abs_path not in self.abs_fnames:
                if abs_path in self.abs_read_only_fnames:
                    self.io.tool_error(f"File '{file_path}' is read-only. Use MakeEditable first.")
                    return f"Error: File is read-only. Use MakeEditable first."
                else:
                    self.io.tool_error(f"File '{file_path}' not in context")
                    return f"Error: File not in context"
             
            # Reread file content immediately before modification (Fixes Point 3: Stale Reads)
            file_content = self.io.read_text(abs_path)
            if file_content is None:
                # Provide more specific error (Improves Point 4)
                self.io.tool_error(f"Could not read file '{file_path}' before ReplaceLine operation.")
                return f"Error: Could not read file '{file_path}'"
            
            # Split into lines
            lines = file_content.splitlines()
            
            # Validate line number
            if not isinstance(line_number, int):
                try:
                    line_number = int(line_number)
                except ValueError:
                    self.io.tool_error(f"Line number must be an integer, got '{line_number}'")
                    # Improve error message (Point 4)
                    self.io.tool_error(f"Invalid line_number value: '{line_number}'. Must be an integer.")
                    return f"Error: Invalid line_number value '{line_number}'"
             
            # Convert 1-based line number (what most editors and error messages use) to 0-based index
            idx = line_number - 1
             
            if idx < 0 or idx >= len(lines):
                # Improve error message (Point 4)
                self.io.tool_error(f"Line number {line_number} is out of range for file '{file_path}' (has {len(lines)} lines).")
                return f"Error: Line number {line_number} out of range"
            
            # Store original content for change tracking
            original_content = file_content
            original_line = lines[idx]
            
            # Replace the line
            lines[idx] = new_content
            
            # Join lines back into a string
            new_content_full = '\n'.join(lines)
            
            if original_content == new_content_full:
                self.io.tool_warning("No changes made: new line content is identical to original")
                return f"Warning: No changes made (new content identical to original)"
             
            # Create a readable diff for the line replacement
            diff = f"Line {line_number}:\n- {original_line}\n+ {new_content}"

            # Handle dry run (Implements Point 6)
            if dry_run:
                self.io.tool_output(f"Dry run: Would replace line {line_number} in {file_path}")
                return f"Dry run: Would replace line {line_number}. Diff:\n{diff}"

            # --- Apply Change (Not dry run) ---
            self.io.write_text(abs_path, new_content_full)
             
            # Track the change
            try:
                metadata = {
                    'line_number': line_number,
                    'original_line': original_line,
                    'new_line': new_content
                }
                change_id = self.change_tracker.track_change(
                    file_path=rel_path,
                    change_type='replaceline',
                    original_content=original_content,
                    new_content=new_content_full,
                    metadata=metadata,
                    change_id=change_id
                )
            except Exception as track_e:
                self.io.tool_error(f"Error tracking change for ReplaceLine: {track_e}")
                change_id = "TRACKING_FAILED"

            self.aider_edited_files.add(rel_path)
             
            # Improve feedback (Point 6)
            self.io.tool_output(f"✅ Replaced line {line_number} in {file_path} (change_id: {change_id})")
            return f"Successfully replaced line {line_number} (change_id: {change_id}). Diff:\n{diff}"
                 
        except Exception as e:
            self.io.tool_error(f"Error in ReplaceLine: {str(e)}\n{traceback.format_exc()}") # Add traceback
            return f"Error: {str(e)}"
    
    def _execute_replace_lines(self, file_path, start_line, end_line, new_content, change_id=None, dry_run=False):
        """
        Replace a range of lines identified by line numbers.
        Useful for fixing errors identified by error messages or linters.
        
        Parameters:
        - file_path: Path to the file to modify
        - start_line: The first line number to replace (1-based)
        - end_line: The last line number to replace (1-based)
        - new_content: New content for the lines (can be multi-line)
        - change_id: Optional ID for tracking the change
        - dry_run: If True, simulate the change without modifying the file
         
        Returns a result message.
        """
        try:
            # Get absolute file path
            abs_path = self.abs_root_path(file_path)
            rel_path = self.get_rel_fname(abs_path)
            
            # Check if file exists
            if not os.path.isfile(abs_path):
                self.io.tool_error(f"File '{file_path}' not found")
                return f"Error: File not found"
                
            # Check if file is in editable context
            if abs_path not in self.abs_fnames:
                if abs_path in self.abs_read_only_fnames:
                    self.io.tool_error(f"File '{file_path}' is read-only. Use MakeEditable first.")
                    return f"Error: File is read-only. Use MakeEditable first."
                else:
                    self.io.tool_error(f"File '{file_path}' not in context")
                    return f"Error: File not in context"
             
            # Reread file content immediately before modification (Fixes Point 3: Stale Reads)
            file_content = self.io.read_text(abs_path)
            if file_content is None:
                # Provide more specific error (Improves Point 4)
                self.io.tool_error(f"Could not read file '{file_path}' before ReplaceLines operation.")
                return f"Error: Could not read file '{file_path}'"
            
            # Convert line numbers to integers if needed
            if not isinstance(start_line, int):
                try:
                    start_line = int(start_line)
                except ValueError:
                    # Improve error message (Point 4)
                    self.io.tool_error(f"Invalid start_line value: '{start_line}'. Must be an integer.")
                    return f"Error: Invalid start_line value '{start_line}'"
            
            if not isinstance(end_line, int):
                try:
                    end_line = int(end_line)
                except ValueError:
                    # Improve error message (Point 4)
                    self.io.tool_error(f"Invalid end_line value: '{end_line}'. Must be an integer.")
                    return f"Error: Invalid end_line value '{end_line}'"
            
            # Split into lines
            lines = file_content.splitlines()
            
            # Convert 1-based line numbers to 0-based indices
            start_idx = start_line - 1
            end_idx = end_line - 1
            # Validate line numbers
            if start_idx < 0 or start_idx >= len(lines):
                # Improve error message (Point 4)
                self.io.tool_error(f"Start line {start_line} is out of range for file '{file_path}' (has {len(lines)} lines).")
                return f"Error: Start line {start_line} out of range"
             
            if end_idx < start_idx or end_idx >= len(lines):
                # Improve error message (Point 4)
                self.io.tool_error(f"End line {end_line} is out of range for file '{file_path}' (must be >= start line {start_line} and <= {len(lines)}).")
                return f"Error: End line {end_line} out of range"
            
            # Store original content for change tracking
            original_content = file_content
            replaced_lines = lines[start_idx:end_idx+1]
            
            # Split the new content into lines
            new_lines = new_content.splitlines()
            
            # Perform the replacement
            new_full_lines = lines[:start_idx] + new_lines + lines[end_idx+1:]
            new_content_full = '\n'.join(new_full_lines)
            
            if original_content == new_content_full:
                self.io.tool_warning("No changes made: new content is identical to original")
                return f"Warning: No changes made (new content identical to original)"
             
            # Create a readable diff for the lines replacement
            diff = f"Lines {start_line}-{end_line}:\n"
            # Add removed lines with - prefix
            for line in replaced_lines:
                diff += f"- {line}\n"
            # Add separator
            diff += "---\n"
            # Add new lines with + prefix
            for line in new_lines:
                diff += f"+ {line}\n"

            # Handle dry run (Implements Point 6)
            if dry_run:
                self.io.tool_output(f"Dry run: Would replace lines {start_line}-{end_line} in {file_path}")
                return f"Dry run: Would replace lines {start_line}-{end_line}. Diff:\n{diff}"

            # --- Apply Change (Not dry run) ---
            self.io.write_text(abs_path, new_content_full)
             
            # Track the change
            try:
                metadata = {
                    'start_line': start_line,
                    'end_line': end_line,
                    'replaced_lines': replaced_lines,
                    'new_lines': new_lines
                }
                change_id = self.change_tracker.track_change(
                    file_path=rel_path,
                    change_type='replacelines',
                    original_content=original_content,
                    new_content=new_content_full,
                    metadata=metadata,
                    change_id=change_id
                )
            except Exception as track_e:
                self.io.tool_error(f"Error tracking change for ReplaceLines: {track_e}")
                change_id = "TRACKING_FAILED"

            self.aider_edited_files.add(rel_path)
            replaced_count = end_line - start_line + 1
            new_count = len(new_lines)
             
            # Improve feedback (Point 6)
            self.io.tool_output(f"✅ Replaced lines {start_line}-{end_line} ({replaced_count} lines) with {new_count} new lines in {file_path} (change_id: {change_id})")
            return f"Successfully replaced lines {start_line}-{end_line} with {new_count} new lines (change_id: {change_id}). Diff:\n{diff}"
                 
        except Exception as e:
            self.io.tool_error(f"Error in ReplaceLines: {str(e)}\n{traceback.format_exc()}") # Add traceback
            return f"Error: {str(e)}"
    
    def _execute_indent_lines(self, file_path, start_pattern, end_pattern=None, line_count=None, indent_levels=1, near_context=None, occurrence=1, change_id=None, dry_run=False):
        """
        Indent or unindent a block of lines in a file.
        
        Parameters:
        - file_path: Path to the file to modify
        - start_pattern: Pattern marking the start of the block to indent (line containing this pattern)
        - end_pattern: Optional pattern marking the end of the block (line containing this pattern)
        - line_count: Optional number of lines to indent (alternative to end_pattern)
        - indent_levels: Number of levels to indent (positive) or unindent (negative)
        - near_context: Optional text nearby to help locate the correct instance of the start_pattern
        - occurrence: Which occurrence of the start_pattern to use (1-based index, or -1 for last)
        - change_id: Optional ID for tracking the change
        - dry_run: If True, simulate the change without modifying the file
         
        Returns a result message.
        """
        try:
            # Get absolute file path
            abs_path = self.abs_root_path(file_path)
            rel_path = self.get_rel_fname(abs_path)
            
            # Check if file exists
            if not os.path.isfile(abs_path):
                self.io.tool_error(f"File '{file_path}' not found")
                return f"Error: File not found"
                
            # Check if file is in editable context
            if abs_path not in self.abs_fnames:
                if abs_path in self.abs_read_only_fnames:
                    self.io.tool_error(f"File '{file_path}' is read-only. Use MakeEditable first.")
                    return f"Error: File is read-only. Use MakeEditable first."
                else:
                    self.io.tool_error(f"File '{file_path}' not in context")
                    return f"Error: File not in context"
             
            # Reread file content immediately before modification (Fixes Point 3: Stale Reads)
            file_content = self.io.read_text(abs_path)
            if file_content is None:
                # Provide more specific error (Improves Point 4)
                self.io.tool_error(f"Could not read file '{file_path}' before IndentLines operation.")
                return f"Error: Could not read file '{file_path}'"
            
            # Validate we have either end_pattern or line_count, but not both
            if end_pattern and line_count:
                self.io.tool_error("Cannot specify both end_pattern and line_count")
                return "Error: Cannot specify both end_pattern and line_count"
            
            # Split into lines for easier handling
            lines = file_content.splitlines()
            original_content = file_content
             
            # Find occurrences of the start_pattern (Implements Point 5)
            start_pattern_line_indices = []
            for i, line in enumerate(lines):
                if start_pattern in line:
                    # If near_context is provided, check if it's nearby
                    if near_context:
                        context_window_start = max(0, i - 5) # Check 5 lines before/after
                        context_window_end = min(len(lines), i + 6)
                        context_block = "\n".join(lines[context_window_start:context_window_end])
                        if near_context in context_block:
                            start_pattern_line_indices.append(i)
                    else:
                        start_pattern_line_indices.append(i)

            if not start_pattern_line_indices:
                err_msg = f"Start pattern '{start_pattern}' not found"
                if near_context: err_msg += f" near context '{near_context}'"
                err_msg += f" in file '{file_path}'."
                self.io.tool_error(err_msg)
                return f"Error: {err_msg}" # Improve Point 4

            # Select the occurrence for the start pattern
            num_occurrences = len(start_pattern_line_indices)
            try:
                occurrence = int(occurrence) # Ensure occurrence is an integer
                if occurrence == -1: # Last occurrence
                    target_idx = num_occurrences - 1
                elif occurrence > 0 and occurrence <= num_occurrences:
                    target_idx = occurrence - 1 # Convert 1-based to 0-based
                else:
                    err_msg = f"Occurrence number {occurrence} is out of range for start pattern '{start_pattern}'. Found {num_occurrences} occurrences"
                    if near_context: err_msg += f" near '{near_context}'"
                    err_msg += f" in '{file_path}'."
                    self.io.tool_error(err_msg)
                    return f"Error: {err_msg}" # Improve Point 4
            except ValueError:
                self.io.tool_error(f"Invalid occurrence value: '{occurrence}'. Must be an integer.")
                return f"Error: Invalid occurrence value '{occurrence}'"

            start_line = start_pattern_line_indices[target_idx]
            occurrence_str = f"occurrence {occurrence} of " if num_occurrences > 1 else "" # For messages
            # Find the end line based on end_pattern or line_count
            end_line = -1
            if end_pattern:
                # Search for end_pattern *after* the selected start_line
                for i in range(start_line, len(lines)): # Include start_line itself if start/end are same line
                    if end_pattern in lines[i]:
                        end_line = i
                        break
                 
                if end_line == -1:
                    # Improve error message (Point 4)
                    err_msg = f"End pattern '{end_pattern}' not found after {occurrence_str}start pattern '{start_pattern}' (line {start_line + 1}) in '{file_path}'."
                    self.io.tool_error(err_msg)
                    return f"Error: {err_msg}"
            elif line_count:
                try:
                    line_count = int(line_count)
                    if line_count <= 0:
                        raise ValueError("Line count must be positive")
                    # Calculate end line based on start line and line count
                    end_line = min(start_line + line_count - 1, len(lines) - 1)
                except ValueError:
                    self.io.tool_error(f"Invalid line_count value: '{line_count}'. Must be a positive integer.")
                    return f"Error: Invalid line_count value '{line_count}'"
            else:
                # If neither end_pattern nor line_count is specified, indent just the start line
                end_line = start_line
            # Determine indentation amount (using spaces for simplicity, could adapt based on file type later)
            try:
                indent_levels = int(indent_levels)
            except ValueError:
                self.io.tool_error(f"Invalid indent_levels value: '{indent_levels}'. Must be an integer.")
                return f"Error: Invalid indent_levels value '{indent_levels}'"
             
            indent_str = ' ' * 4 # Assume 4 spaces per level
             
            # Create a temporary copy to calculate the change
            modified_lines = list(lines) # Copy the list
             
            # Apply indentation to the temporary copy
            for i in range(start_line, end_line + 1):
                if indent_levels > 0:
                    # Add indentation
                    modified_lines[i] = (indent_str * indent_levels) + modified_lines[i]
                elif indent_levels < 0:
                    # Remove indentation, but do not remove more than exists
                    spaces_to_remove = abs(indent_levels) * len(indent_str)
                    current_leading_spaces = len(modified_lines[i]) - len(modified_lines[i].lstrip(' '))
                    actual_remove = min(spaces_to_remove, current_leading_spaces)
                    if actual_remove > 0:
                        modified_lines[i] = modified_lines[i][actual_remove:]
                # If indent_levels is 0, do nothing
             
            # Join lines back into a string
            new_content = '\n'.join(modified_lines) # Use '\n' to match io.write_text behavior
             
            if original_content == new_content:
                self.io.tool_warning(f"No changes made: indentation would not change file")
                return f"Warning: No changes made (indentation would not change file)"

            # Generate diff for feedback
            diff_snippet = self._generate_diff_snippet_indent(original_content, new_content, start_line, end_line)

            # Handle dry run (Implements Point 6)
            if dry_run:
                action = "indent" if indent_levels > 0 else "unindent"
                self.io.tool_output(f"Dry run: Would {action} lines {start_line+1}-{end_line+1} (based on {occurrence_str}start pattern '{start_pattern}') in {file_path}")
                return f"Dry run: Would {action} block. Diff snippet:\n{diff_snippet}"

            # --- Apply Change (Not dry run) ---
            self.io.write_text(abs_path, new_content)
             
            # Track the change
            try:
                metadata = {
                    'start_line': start_line + 1, # Store 1-based
                    'end_line': end_line + 1,   # Store 1-based
                    'start_pattern': start_pattern,
                    'end_pattern': end_pattern,
                    'line_count': line_count,
                    'indent_levels': indent_levels,
                    'near_context': near_context,
                    'occurrence': occurrence,
                }
                change_id = self.change_tracker.track_change(
                    file_path=rel_path,
                    change_type='indentlines',
                    original_content=original_content,
                    new_content=new_content,
                    metadata=metadata,
                    change_id=change_id
                )
            except Exception as track_e:
                self.io.tool_error(f"Error tracking change for IndentLines: {track_e}")
                change_id = "TRACKING_FAILED"

            self.aider_edited_files.add(rel_path)
             
            # Improve feedback (Point 5 & 6)
            action = "Indented" if indent_levels > 0 else "Unindented"
            levels = abs(indent_levels)
            level_text = "level" if levels == 1 else "levels"
            num_lines = end_line - start_line + 1
            self.io.tool_output(f"✅ {action} {num_lines} lines (from {occurrence_str}start pattern) by {levels} {level_text} in {file_path} (change_id: {change_id})")
            return f"Successfully {action.lower()} {num_lines} lines by {levels} {level_text} (change_id: {change_id}). Diff snippet:\n{diff_snippet}"
                 
        except Exception as e:
            self.io.tool_error(f"Error in IndentLines: {str(e)}\n{traceback.format_exc()}") # Add traceback
            return f"Error: {str(e)}"

    def _execute_list_changes(self, file_path=None, limit=10):
        """
        List recent changes made to files.
        
        Parameters:
        - file_path: Optional path to filter changes by file
        - limit: Maximum number of changes to list
        
        Returns a formatted list of changes.
        """
        try:
            # If file_path is specified, get the absolute path
            rel_file_path = None
            if file_path:
                abs_path = self.abs_root_path(file_path)
                rel_file_path = self.get_rel_fname(abs_path)
            
            # Get the list of changes
            changes = self.change_tracker.list_changes(rel_file_path, limit)
            
            if not changes:
                if file_path:
                    return f"No changes found for file '{file_path}'"
                else:
                    return "No changes have been made yet"
            
            # Format the changes into a readable list
            result = "Recent changes:\n"
            for i, change in enumerate(changes):
                change_time = datetime.fromtimestamp(change['timestamp']).strftime('%H:%M:%S')
                change_type = change['type']
                file_path = change['file_path']
                change_id = change['id']
                
                result += f"{i+1}. [{change_id}] {change_time} - {change_type.upper()} on {file_path}\n"
             
            self.io.tool_output(result) # Also print to console for user
            return result
                 
        except Exception as e:
            self.io.tool_error(f"Error in ListChanges: {str(e)}\n{traceback.format_exc()}") # Add traceback
            return f"Error: {str(e)}"

    def _execute_extract_lines(self, source_file_path, target_file_path, start_pattern, end_pattern=None, line_count=None, near_context=None, occurrence=1, dry_run=False):
        """
        Extract a range of lines from a source file and move them to a target file.

        Parameters:
        - source_file_path: Path to the file to extract lines from
        - target_file_path: Path to the file to append extracted lines to (will be created if needed)
        - start_pattern: Pattern marking the start of the block to extract
        - end_pattern: Optional pattern marking the end of the block
        - line_count: Optional number of lines to extract (alternative to end_pattern)
        - near_context: Optional text nearby to help locate the correct instance of the start_pattern
        - occurrence: Which occurrence of the start_pattern to use (1-based index, or -1 for last)
        - dry_run: If True, simulate the change without modifying files

        Returns a result message.
        """
        try:
            # --- Validate Source File ---
            abs_source_path = self.abs_root_path(source_file_path)
            rel_source_path = self.get_rel_fname(abs_source_path)

            if not os.path.isfile(abs_source_path):
                self.io.tool_error(f"Source file '{source_file_path}' not found")
                return f"Error: Source file not found"

            if abs_source_path not in self.abs_fnames:
                if abs_source_path in self.abs_read_only_fnames:
                    self.io.tool_error(f"Source file '{source_file_path}' is read-only. Use MakeEditable first.")
                    return f"Error: Source file is read-only. Use MakeEditable first."
                else:
                    self.io.tool_error(f"Source file '{source_file_path}' not in context")
                    return f"Error: Source file not in context"

            # --- Validate Target File ---
            abs_target_path = self.abs_root_path(target_file_path)
            rel_target_path = self.get_rel_fname(abs_target_path)
            target_exists = os.path.isfile(abs_target_path)
            target_is_editable = abs_target_path in self.abs_fnames
            target_is_readonly = abs_target_path in self.abs_read_only_fnames

            if target_exists and not target_is_editable:
                if target_is_readonly:
                    self.io.tool_error(f"Target file '{target_file_path}' exists but is read-only. Use MakeEditable first.")
                    return f"Error: Target file exists but is read-only. Use MakeEditable first."
                else:
                    # This case shouldn't happen if file exists, but handle defensively
                    self.io.tool_error(f"Target file '{target_file_path}' exists but is not in context. Add it first.")
                    return f"Error: Target file exists but is not in context."

            # --- Read Source Content ---
            source_content = self.io.read_text(abs_source_path)
            if source_content is None:
                self.io.tool_error(f"Could not read source file '{source_file_path}' before ExtractLines operation.")
                return f"Error: Could not read source file '{source_file_path}'"

            # --- Find Extraction Range ---
            if end_pattern and line_count:
                self.io.tool_error("Cannot specify both end_pattern and line_count")
                return "Error: Cannot specify both end_pattern and line_count"

            source_lines = source_content.splitlines()
            original_source_content = source_content

            start_pattern_line_indices = []
            for i, line in enumerate(source_lines):
                if start_pattern in line:
                    if near_context:
                        context_window_start = max(0, i - 5)
                        context_window_end = min(len(source_lines), i + 6)
                        context_block = "\n".join(source_lines[context_window_start:context_window_end])
                        if near_context in context_block:
                            start_pattern_line_indices.append(i)
                    else:
                        start_pattern_line_indices.append(i)

            if not start_pattern_line_indices:
                err_msg = f"Start pattern '{start_pattern}' not found"
                if near_context: err_msg += f" near context '{near_context}'"
                err_msg += f" in source file '{source_file_path}'."
                self.io.tool_error(err_msg)
                return f"Error: {err_msg}"

            num_occurrences = len(start_pattern_line_indices)
            try:
                occurrence = int(occurrence)
                if occurrence == -1:
                    target_idx = num_occurrences - 1
                elif occurrence > 0 and occurrence <= num_occurrences:
                    target_idx = occurrence - 1
                else:
                    err_msg = f"Occurrence number {occurrence} is out of range for start pattern '{start_pattern}'. Found {num_occurrences} occurrences"
                    if near_context: err_msg += f" near '{near_context}'"
                    err_msg += f" in '{source_file_path}'."
                    self.io.tool_error(err_msg)
                    return f"Error: {err_msg}"
            except ValueError:
                self.io.tool_error(f"Invalid occurrence value: '{occurrence}'. Must be an integer.")
                return f"Error: Invalid occurrence value '{occurrence}'"

            start_line = start_pattern_line_indices[target_idx]
            occurrence_str = f"occurrence {occurrence} of " if num_occurrences > 1 else ""

            end_line = -1
            if end_pattern:
                for i in range(start_line, len(source_lines)):
                    if end_pattern in source_lines[i]:
                        end_line = i
                        break
                if end_line == -1:
                    err_msg = f"End pattern '{end_pattern}' not found after {occurrence_str}start pattern '{start_pattern}' (line {start_line + 1}) in '{source_file_path}'."
                    self.io.tool_error(err_msg)
                    return f"Error: {err_msg}"
            elif line_count:
                try:
                    line_count = int(line_count)
                    if line_count <= 0: raise ValueError("Line count must be positive")
                    end_line = min(start_line + line_count - 1, len(source_lines) - 1)
                except ValueError:
                    self.io.tool_error(f"Invalid line_count value: '{line_count}'. Must be a positive integer.")
                    return f"Error: Invalid line_count value '{line_count}'"
            else:
                end_line = start_line # Extract just the start line if no end specified

            # --- Prepare Content Changes ---
            extracted_lines = source_lines[start_line:end_line+1]
            new_source_lines = source_lines[:start_line] + source_lines[end_line+1:]
            new_source_content = '\n'.join(new_source_lines)

            target_content = ""
            if target_exists:
                target_content = self.io.read_text(abs_target_path)
                if target_content is None:
                    self.io.tool_error(f"Could not read existing target file '{target_file_path}'.")
                    return f"Error: Could not read target file '{target_file_path}'"
            original_target_content = target_content # For tracking

            # Append extracted lines to target content, ensuring a newline if target wasn't empty
            extracted_block = '\n'.join(extracted_lines)
            if target_content and not target_content.endswith('\n'):
                 target_content += '\n' # Add newline before appending if needed
            new_target_content = target_content + extracted_block

            # --- Generate Diffs ---
            source_diff_snippet = self._generate_diff_snippet_delete(original_source_content, start_line, end_line)
            target_insertion_line = len(target_content.splitlines()) if target_content else 0
            target_diff_snippet = self._generate_diff_snippet_insert(original_target_content, target_insertion_line, extracted_lines)

            # --- Handle Dry Run ---
            if dry_run:
                num_extracted = end_line - start_line + 1
                target_action = "append to" if target_exists else "create"
                self.io.tool_output(f"Dry run: Would extract {num_extracted} lines (from {occurrence_str}start pattern '{start_pattern}') in {source_file_path} and {target_action} {target_file_path}")
                # Provide more informative dry run response with diffs
                return (
                    f"Dry run: Would extract {num_extracted} lines from {rel_source_path} and {target_action} {rel_target_path}.\n"
                    f"Source Diff (Deletion):\n{source_diff_snippet}\n"
                    f"Target Diff (Insertion):\n{target_diff_snippet}"
                )

            # --- Apply Changes (Not Dry Run) ---
            self.io.write_text(abs_source_path, new_source_content)
            self.io.write_text(abs_target_path, new_target_content)

            # --- Track Changes ---
            source_change_id = "TRACKING_FAILED"
            target_change_id = "TRACKING_FAILED"
            try:
                source_metadata = {
                    'start_line': start_line + 1, 'end_line': end_line + 1,
                    'start_pattern': start_pattern, 'end_pattern': end_pattern, 'line_count': line_count,
                    'near_context': near_context, 'occurrence': occurrence,
                    'extracted_content': extracted_block, 'target_file': rel_target_path
                }
                source_change_id = self.change_tracker.track_change(
                    file_path=rel_source_path, change_type='extractlines_source',
                    original_content=original_source_content, new_content=new_source_content,
                    metadata=source_metadata
                )
            except Exception as track_e:
                self.io.tool_error(f"Error tracking source change for ExtractLines: {track_e}")

            try:
                target_metadata = {
                    'insertion_line': target_insertion_line + 1,
                    'inserted_content': extracted_block, 'source_file': rel_source_path
                }
                target_change_id = self.change_tracker.track_change(
                    file_path=rel_target_path, change_type='extractlines_target',
                    original_content=original_target_content, new_content=new_target_content,
                    metadata=target_metadata
                )
            except Exception as track_e:
                self.io.tool_error(f"Error tracking target change for ExtractLines: {track_e}")

            # --- Update Context ---
            self.aider_edited_files.add(rel_source_path)
            self.aider_edited_files.add(rel_target_path)
            if not target_exists:
                # Add the newly created file to editable context
                self.abs_fnames.add(abs_target_path)
                self.io.tool_output(f"✨ Created and added '{target_file_path}' to editable context.")

            # --- Return Result ---
            num_extracted = end_line - start_line + 1
            target_action = "appended to" if target_exists else "created"
            self.io.tool_output(f"✅ Extracted {num_extracted} lines from {rel_source_path} (change_id: {source_change_id}) and {target_action} {rel_target_path} (change_id: {target_change_id})")
            # Provide more informative success response with change IDs and diffs
            return (
                f"Successfully extracted {num_extracted} lines from {rel_source_path} and {target_action} {rel_target_path}.\n"
                f"Source Change ID: {source_change_id}\nSource Diff (Deletion):\n{source_diff_snippet}\n"
                f"Target Change ID: {target_change_id}\nTarget Diff (Insertion):\n{target_diff_snippet}"
            )

        except Exception as e:
            self.io.tool_error(f"Error in ExtractLines: {str(e)}\n{traceback.format_exc()}")
            return f"Error: {str(e)}"


    # ------------------- Diff Generation Helpers -------------------

    def _generate_diff_snippet(self, original_content, start_index, replaced_len, replacement_text):
        """Generate a git-style diff snippet for a simple text replacement."""
        try:
            lines = original_content.splitlines()
            char_count = 0
            start_line_idx = -1
            start_char_idx_in_line = -1

            # Find the line and character index where the change starts
            for i, line in enumerate(lines):
                line_len_with_newline = len(line) + 1 # Account for newline character
                if char_count + line_len_with_newline > start_index:
                    start_line_idx = i
                    start_char_idx_in_line = start_index - char_count
                    break
                char_count += line_len_with_newline

            if start_line_idx == -1: return "[Diff generation error: start index out of bounds]"

            # Determine the end line and character index
            end_index = start_index + replaced_len
            char_count = 0
            end_line_idx = -1
            end_char_idx_in_line = -1
            for i, line in enumerate(lines):
                 line_len_with_newline = len(line) + 1
                 if char_count + line_len_with_newline > end_index:
                     end_line_idx = i
                     # End char index is relative to the start of *its* line
                     end_char_idx_in_line = end_index - char_count
                     break
                 char_count += line_len_with_newline
            # If end_index is exactly at the end of the content
            if end_line_idx == -1 and end_index == len(original_content):
                 end_line_idx = len(lines) - 1
                 end_char_idx_in_line = len(lines[end_line_idx])

            if end_line_idx == -1: return "[Diff generation error: end index out of bounds]"

            # Get context lines
            context = 3
            diff_start_line = max(0, start_line_idx - context)
            diff_end_line = min(len(lines) - 1, end_line_idx + context)

            diff_lines = [f"@@ line ~{start_line_idx + 1} @@"]
            for i in range(diff_start_line, diff_end_line + 1):
                if i >= start_line_idx and i <= end_line_idx:
                    # Line is part of the original replaced block
                    diff_lines.append(f"- {lines[i]}")
                else:
                    # Context line
                    diff_lines.append(f"  {lines[i]}")

            # Construct the new lines based on the replacement
            prefix = lines[start_line_idx][:start_char_idx_in_line]
            suffix = lines[end_line_idx][end_char_idx_in_line:]

            # Combine prefix, replacement, and suffix, then split into lines
            combined_new_content = prefix + replacement_text + suffix
            new_content_lines = combined_new_content.splitlines()

            # Add new lines to diff
            for new_line in new_content_lines:
                 diff_lines.append(f"+ {new_line}")
 
            return "\n".join(diff_lines)
        except Exception as e:
             return f"[Diff generation error: {e}]"
 
    def _generate_diff_chunks(self, original_content, find_text, replace_text):
        """Generate multiple git-style diff snippets for ReplaceAll."""
        try:
           lines = original_content.splitlines()
           new_lines_content = original_content.replace(find_text, replace_text)
           new_lines = new_lines_content.splitlines()

           # Use difflib for a more robust diff
           import difflib
           diff = list(difflib.unified_diff(lines, new_lines, lineterm='', n=3)) # n=3 lines of context

           if len(diff) <= 2: # Only header lines, no changes found by diff
               return "No significant changes detected by diff."

           # Process the diff output into readable chunks
           # Skip header lines (---, +++)
           processed_diff = "\n".join(diff[2:])

           # Limit the output size if it's too large
           max_diff_len = 2000 # Limit diff snippet size
           if len(processed_diff) > max_diff_len:
               processed_diff = processed_diff[:max_diff_len] + "\n... (diff truncated)"

           return processed_diff if processed_diff else "No changes detected."
        except Exception as e:
            return f"[Diff generation error: {e}]"
 
    def _generate_diff_snippet_insert(self, original_content, insertion_line_idx, content_lines_to_insert):
        """Generate a git-style diff snippet for an insertion."""
        try:
            lines = original_content.splitlines()
            context = 3

            # Determine context range
            start_context = max(0, insertion_line_idx - context)
            end_context = min(len(lines), insertion_line_idx + context) # End index is exclusive for slicing

            diff_lines = [f"@@ line ~{insertion_line_idx + 1} @@"] # Indicate insertion point

            # Add lines before insertion point
            for i in range(start_context, insertion_line_idx):
                diff_lines.append(f"  {lines[i]}")

            # Add inserted lines
            for line in content_lines_to_insert:
                diff_lines.append(f"+ {line}")

            # Add lines after insertion point
            for i in range(insertion_line_idx, end_context):
                 diff_lines.append(f"  {lines[i]}")
 
            return "\n".join(diff_lines)
        except Exception as e:
            return f"[Diff generation error: {e}]"
 
    def _generate_diff_snippet_delete(self, original_content, start_line, end_line):
        """Generate a git-style diff snippet for a deletion."""
        try:
            lines = original_content.splitlines()
            context = 3

            # Determine context range
            diff_start_line = max(0, start_line - context)
            diff_end_line = min(len(lines) - 1, end_line + context)

            diff_lines = [f"@@ line {start_line + 1},{end_line + 1} @@"] # Indicate deletion range

            for i in range(diff_start_line, diff_end_line + 1):
                if i >= start_line and i <= end_line:
                    # Line was deleted
                    diff_lines.append(f"- {lines[i]}")
                else:
                    # Context line
                    diff_lines.append(f"  {lines[i]}")
 
            return "\n".join(diff_lines)
        except Exception as e:
            return f"[Diff generation error: {e}]"
 
    def _generate_diff_snippet_indent(self, original_content, new_content, start_line, end_line):
        """Generate a git-style diff snippet for indentation changes."""
        try:
            original_lines = original_content.splitlines()
            new_lines = new_content.splitlines()
            context = 3

            # Determine context range
            diff_start_line = max(0, start_line - context)
            diff_end_line = min(len(original_lines) - 1, end_line + context)

            diff_lines_output = [f"@@ lines ~{start_line + 1}-{end_line + 1} @@"] # Indicate affected range

            for i in range(diff_start_line, diff_end_line + 1):
                 # Ensure index is valid for both lists (should be, as only indentation changes)
                 if i < len(original_lines) and i < len(new_lines):
                     if i >= start_line and i <= end_line:
                         # Line is within the indented/unindented block
                         if original_lines[i] != new_lines[i]: # Show only if changed
                             diff_lines_output.append(f"- {original_lines[i]}")
                             diff_lines_output.append(f"+ {new_lines[i]}")
                         else: # If somehow unchanged, show as context
                              diff_lines_output.append(f"  {original_lines[i]}")
                     else:
                         # Context line
                         diff_lines_output.append(f"  {original_lines[i]}")

            return "\n".join(diff_lines_output)
        except Exception as e:
            return f"[Diff generation error: {e}]"