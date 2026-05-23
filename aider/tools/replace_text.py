import traceback
from .tool_utils import (
    ToolError,
    validate_file_for_edit,
    apply_change,
    handle_tool_error,
    format_tool_result,
    generate_unified_diff_snippet,
)

def _execute_replace_text(coder, file_path, find_text, replace_text, near_context=None, occurrence=1, change_id=None, dry_run=False):
    """
    Replace specific text with new text, optionally using nearby context for disambiguation.
    Uses utility functions for validation, finding occurrences, and applying changes.
    """
    tool_name = "ReplaceText"
    try:
        # 1. Validate file and get content
        abs_path, rel_path, original_content = validate_file_for_edit(coder, file_path)

        # 2. Find occurrences using helper function
        # Note: _find_occurrences is currently on the Coder class, not in tool_utils
        occurrences = coder._find_occurrences(original_content, find_text, near_context)

        if not occurrences:
            err_msg = f"Text '{find_text}' not found"
            if near_context:
                err_msg += f" near context '{near_context}'"
            err_msg += f" in file '{file_path}'."
            raise ToolError(err_msg)

        # 3. Select the occurrence index
        num_occurrences = len(occurrences)
        try:
            occurrence = int(occurrence)
            if occurrence == -1:
                if num_occurrences == 0:
                    raise ToolError(f"Text '{find_text}' not found, cannot select last occurrence.")
                target_idx = num_occurrences - 1
            elif 1 <= occurrence <= num_occurrences:
                target_idx = occurrence - 1 # Convert 1-based to 0-based
            else:
                err_msg = f"Occurrence number {occurrence} is out of range. Found {num_occurrences} occurrences of '{find_text}'"
                if near_context: err_msg += f" near '{near_context}'"
                err_msg += f" in '{file_path}'."
                raise ToolError(err_msg)
        except ValueError:
            raise ToolError(f"Invalid occurrence value: '{occurrence}'. Must be an integer.")

        start_index = occurrences[target_idx]

        # 4. Perform the replacement
        new_content = original_content[:start_index] + replace_text + original_content[start_index + len(find_text):]

        if original_content == new_content:
            coder.io.tool_warning(f"No changes made: replacement text is identical to original")
            return f"Warning: No changes made (replacement identical to original)"

        # 5. Generate diff for feedback
        # Note: _generate_diff_snippet is currently on the Coder class
        diff_snippet = generate_unified_diff_snippet(original_content, new_content, rel_path)
        occurrence_str = f"occurrence {occurrence}" if num_occurrences > 1 else "text"

        # 6. Handle dry run
        if dry_run:
            dry_run_message = f"Dry run: Would replace {occurrence_str} of '{find_text}' in {file_path}."
            return format_tool_result(coder, tool_name, "", dry_run=True, dry_run_message=dry_run_message, diff_snippet=diff_snippet)

        # 7. Apply Change (Not dry run)
        metadata = {
            'start_index': start_index,
            'find_text': find_text,
            'replace_text': replace_text,
            'near_context': near_context,
            'occurrence': occurrence
        }
        final_change_id = apply_change(
            coder, abs_path, rel_path, original_content, new_content, 'replacetext', metadata, change_id
        )

        # 8. Format and return result
        success_message = f"Replaced {occurrence_str} in {file_path}"
        return format_tool_result(
            coder, tool_name, success_message, change_id=final_change_id, diff_snippet=diff_snippet
        )

    except ToolError as e:
        # Handle errors raised by utility functions or explicitly raised here
        return handle_tool_error(coder, tool_name, e, add_traceback=False)
    except Exception as e:
        # Handle unexpected errors
        return handle_tool_error(coder, tool_name, e)