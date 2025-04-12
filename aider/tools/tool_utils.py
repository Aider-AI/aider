import difflib
import os
import traceback

class ToolError(Exception):
    """Custom exception for tool-specific errors that should be reported to the LLM."""
    pass

def resolve_paths(coder, file_path):
    """Resolves absolute and relative paths for a given file path."""
    try:
        abs_path = coder.abs_root_path(file_path)
        rel_path = coder.get_rel_fname(abs_path)
        return abs_path, rel_path
    except Exception as e:
        # Wrap unexpected errors during path resolution
        raise ToolError(f"Error resolving path '{file_path}': {e}")

def validate_file_for_edit(coder, file_path):
    """
    Validates if a file exists, is in context, and is editable.
    Reads and returns original content if valid.
    Raises ToolError on failure.

    Returns:
        tuple: (absolute_path, relative_path, original_content)
    """
    abs_path, rel_path = resolve_paths(coder, file_path)

    if not os.path.isfile(abs_path):
        raise ToolError(f"File '{file_path}' not found")

    if abs_path not in coder.abs_fnames:
        if abs_path in coder.abs_read_only_fnames:
            raise ToolError(f"File '{file_path}' is read-only. Use MakeEditable first.")
        else:
            # File exists but is not in context at all
            raise ToolError(f"File '{file_path}' not in context. Use View or MakeEditable first.")

    # Reread content immediately before potential modification
    content = coder.io.read_text(abs_path)
    if content is None:
        # This indicates an issue reading a file we know exists and is in context
        coder.io.tool_error(f"Internal error: Could not read file '{file_path}' which should be accessible.")
        raise ToolError(f"Could not read file '{file_path}'")

    return abs_path, rel_path, content

def find_pattern_indices(lines, pattern, near_context=None):
    """Finds all line indices matching a pattern, optionally filtered by context."""
    indices = []
    for i, line in enumerate(lines):
        if pattern in line:
            if near_context:
                # Check if near_context is within a window around the match
                context_window_start = max(0, i - 5) # Check 5 lines before/after
                context_window_end = min(len(lines), i + 6)
                context_block = "\n".join(lines[context_window_start:context_window_end])
                if near_context in context_block:
                    indices.append(i)
            else:
                indices.append(i)
    return indices

def select_occurrence_index(indices, occurrence, pattern_desc="Pattern"):
    """
    Selects the target 0-based index from a list of indices based on the 1-based occurrence parameter.
    Raises ToolError if the pattern wasn't found or the occurrence is invalid.
    """
    num_occurrences = len(indices)
    if not indices:
        raise ToolError(f"{pattern_desc} not found")

    try:
        occurrence = int(occurrence) # Ensure occurrence is an integer
        if occurrence == -1: # Last occurrence
            if num_occurrences == 0:
                 raise ToolError(f"{pattern_desc} not found, cannot select last occurrence.")
            target_idx = num_occurrences - 1
        elif 1 <= occurrence <= num_occurrences:
            target_idx = occurrence - 1 # Convert 1-based to 0-based
        else:
            raise ToolError(f"Occurrence number {occurrence} is out of range for {pattern_desc}. Found {num_occurrences} occurrences.")
    except ValueError:
        raise ToolError(f"Invalid occurrence value: '{occurrence}'. Must be an integer.")

    return indices[target_idx]

def determine_line_range(
    coder,
    file_path,
    lines,
    start_pattern_line_index=None, # Made optional
    end_pattern=None,
    line_count=None,
    target_symbol=None,
    pattern_desc="Block",
):
    """
    Determines the end line index based on end_pattern or line_count.
    Raises ToolError if end_pattern is not found or line_count is invalid.
    """
    # Parameter validation: Ensure only one targeting method is used
    targeting_methods = [
        target_symbol is not None,
        start_pattern_line_index is not None,
        # Note: line_count and end_pattern depend on start_pattern_line_index
    ]
    if sum(targeting_methods) > 1:
        raise ToolError("Cannot specify target_symbol along with start_pattern.")
    if sum(targeting_methods) == 0:
         raise ToolError("Must specify either target_symbol or start_pattern.") # Or line numbers for line-based tools, handled elsewhere

    if target_symbol:
        if end_pattern or line_count:
             raise ToolError("Cannot specify end_pattern or line_count when using target_symbol.")
        try:
            # Use repo_map to find the symbol's definition range
            start_line, end_line = coder.repo_map.get_symbol_definition_location(file_path, target_symbol)
            return start_line, end_line
        except AttributeError: # Use specific exception
             # Check if repo_map exists and is initialized before accessing methods
             if not hasattr(coder, 'repo_map') or coder.repo_map is None:
                 raise ToolError("RepoMap is not available or not initialized.")
             # If repo_map exists, the error might be from get_symbol_definition_location itself
             # Re-raise ToolErrors directly
             raise
        except ToolError as e:
             # Propagate specific ToolErrors from repo_map (not found, ambiguous, etc.)
             raise e
        except Exception as e:
             # Catch other unexpected errors during symbol lookup
             raise ToolError(f"Unexpected error looking up symbol '{target_symbol}': {e}")

    # --- Existing logic for pattern/line_count based targeting ---
    # Ensure start_pattern_line_index is provided if not using target_symbol
    if start_pattern_line_index is None:
         raise ToolError("Internal error: start_pattern_line_index is required when not using target_symbol.")

    # Assign start_line here for the pattern-based logic path
    start_line = start_pattern_line_index # Start of existing logic
    start_line = start_pattern_line_index
    end_line = -1

    if end_pattern and line_count:
        raise ToolError("Cannot specify both end_pattern and line_count")

    if end_pattern:
        found_end = False
        # Search from the start_line onwards for the end_pattern
        for i in range(start_line, len(lines)):
            if end_pattern in lines[i]:
                end_line = i
                found_end = True
                break
        if not found_end:
            raise ToolError(f"End pattern '{end_pattern}' not found after start pattern on line {start_line + 1}")
    elif line_count:
        try:
            line_count = int(line_count)
            if line_count <= 0:
                raise ValueError("Line count must be positive")
            # Calculate end line index, ensuring it doesn't exceed file bounds
            end_line = min(start_line + line_count - 1, len(lines) - 1)
        except ValueError:
            raise ToolError(f"Invalid line_count value: '{line_count}'. Must be a positive integer.")
    else:
        # If neither end_pattern nor line_count is given, the range is just the start line
        end_line = start_line

    return start_line, end_line


def generate_unified_diff_snippet(original_content, new_content, file_path, context_lines=3):
    """
    Generates a unified diff snippet between original and new content.

    Args:
        original_content (str): The original file content.
        new_content (str): The modified file content.
        file_path (str): The relative path to the file (for display in diff header).
        context_lines (int): Number of context lines to show around changes.

    Returns:
        str: A formatted unified diff snippet, or an empty string if no changes.
    """
    if original_content == new_content:
        return ""

    original_lines = original_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)

    diff = difflib.unified_diff(
        original_lines,
        new_lines,
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
        n=context_lines, # Number of context lines
    )

    # Join the diff lines, potentially skipping the header if desired,
    # but let's keep it for standard format.
    diff_snippet = "".join(diff)

    # Ensure snippet ends with a newline for cleaner formatting in results
    if diff_snippet and not diff_snippet.endswith('\n'):
        diff_snippet += '\n'

    return diff_snippet
def apply_change(coder, abs_path, rel_path, original_content, new_content, change_type, metadata, change_id=None):
    """
    Writes the new content, tracks the change, and updates coder state.
    Returns the final change ID. Raises ToolError on tracking failure.
    """
    coder.io.write_text(abs_path, new_content)
    try:
        final_change_id = coder.change_tracker.track_change(
            file_path=rel_path,
            change_type=change_type,
            original_content=original_content,
            new_content=new_content,
            metadata=metadata,
            change_id=change_id
        )
    except Exception as track_e:
        # Log the error but also raise ToolError to inform the LLM
        coder.io.tool_error(f"Error tracking change for {change_type}: {track_e}")
        raise ToolError(f"Failed to track change: {track_e}")

    coder.aider_edited_files.add(rel_path)
    return final_change_id


def handle_tool_error(coder, tool_name, e, add_traceback=True):
    """Logs tool errors and returns a formatted error message for the LLM."""
    error_message = f"Error in {tool_name}: {str(e)}"
    if add_traceback:
        error_message += f"\n{traceback.format_exc()}"
    coder.io.tool_error(error_message)
    # Return only the core error message to the LLM for brevity
    return f"Error: {str(e)}"

def format_tool_result(coder, tool_name, success_message, change_id=None, diff_snippet=None, dry_run=False, dry_run_message=None):
    """Formats the result message for tool execution."""
    if dry_run:
        full_message = dry_run_message or f"Dry run: Would execute {tool_name}."
        if diff_snippet:
            full_message += f" Diff snippet:\n{diff_snippet}"
        coder.io.tool_output(full_message) # Log the dry run action
        return full_message
    else:
        # Use the provided success message, potentially adding change_id and diff
        full_message = f"✅ {success_message}"
        if change_id:
            full_message += f" (change_id: {change_id})"
        coder.io.tool_output(full_message) # Log the success action

        result_for_llm = f"Successfully executed {tool_name}."
        if change_id:
             result_for_llm += f" Change ID: {change_id}."
        if diff_snippet:
            result_for_llm += f" Diff snippet:\n{diff_snippet}"
        return result_for_llm

# Example usage within a hypothetical tool:
# try:
#     abs_path, rel_path, original_content = validate_file_for_edit(coder, file_path)
#     # ... tool specific logic to determine new_content and metadata ...
#     if dry_run:
#         return format_tool_result(coder, "MyTool", "", dry_run=True, diff_snippet=diff)
#
#     change_id = apply_change(coder, abs_path, rel_path, original_content, new_content, 'mytool', metadata)
#     return format_tool_result(coder, "MyTool", f"Applied change to {file_path}", change_id=change_id, diff_snippet=diff)
# except ToolError as e:
#     return handle_tool_error(coder, "MyTool", e, add_traceback=False) # Don't need traceback for ToolErrors
# except Exception as e:
#     return handle_tool_error(coder, "MyTool", e)
