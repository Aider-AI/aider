import traceback
from .tool_utils import (
    ToolError,
    validate_file_for_edit,
    find_pattern_indices,
    select_occurrence_index,
    determine_line_range,
    apply_change,
    handle_tool_error,
    format_tool_result,
    generate_unified_diff_snippet,
)

def _execute_delete_block(coder, file_path, start_pattern, end_pattern=None, line_count=None, near_context=None, occurrence=1, change_id=None, dry_run=False):
    """
    Delete a block of text between start_pattern and end_pattern (inclusive).
    Uses utility functions for validation, finding lines, and applying changes.
    """
    tool_name = "DeleteBlock"
    try:
        # 1. Validate file and get content
        abs_path, rel_path, original_content = validate_file_for_edit(coder, file_path)
        lines = original_content.splitlines()

        # 2. Find the start line
        pattern_desc = f"Start pattern '{start_pattern}'"
        if near_context:
            pattern_desc += f" near context '{near_context}'"
        start_pattern_indices = find_pattern_indices(lines, start_pattern, near_context)
        start_line_idx = select_occurrence_index(start_pattern_indices, occurrence, pattern_desc)

        # 3. Determine the end line, passing pattern_desc for better error messages
        start_line, end_line = determine_line_range(
            coder=coder,
            file_path=rel_path,
            lines=lines,
            start_pattern_line_index=start_line_idx,
            end_pattern=end_pattern,
            line_count=line_count,
            target_symbol=None, # DeleteBlock uses patterns, not symbols
            pattern_desc=pattern_desc
        )

        # 4. Prepare the deletion
        deleted_lines = lines[start_line:end_line+1]
        new_lines = lines[:start_line] + lines[end_line+1:]
        new_content = '\n'.join(new_lines)

        if original_content == new_content:
            coder.io.tool_warning(f"No changes made: deletion would not change file")
            return f"Warning: No changes made (deletion would not change file)"

        # 5. Generate diff for feedback
        diff_snippet = generate_unified_diff_snippet(original_content, new_content, rel_path)
        num_deleted = end_line - start_line + 1
        num_occurrences = len(start_pattern_indices)
        occurrence_str = f"occurrence {occurrence} of " if num_occurrences > 1 else ""

        # 6. Handle dry run
        if dry_run:
            dry_run_message = f"Dry run: Would delete {num_deleted} lines ({start_line+1}-{end_line+1}) based on {occurrence_str}start pattern '{start_pattern}' in {file_path}."
            return format_tool_result(coder, tool_name, "", dry_run=True, dry_run_message=dry_run_message, diff_snippet=diff_snippet)

        # 7. Apply Change (Not dry run)
        metadata = {
            'start_line': start_line + 1,
            'end_line': end_line + 1,
            'start_pattern': start_pattern,
            'end_pattern': end_pattern,
            'line_count': line_count,
            'near_context': near_context,
            'occurrence': occurrence,
            'deleted_content': '\n'.join(deleted_lines)
        }
        final_change_id = apply_change(
            coder, abs_path, rel_path, original_content, new_content, 'deleteblock', metadata, change_id
        )

        # 8. Format and return result, adding line range to success message
        success_message = f"Deleted {num_deleted} lines ({start_line+1}-{end_line+1}) (from {occurrence_str}start pattern) in {file_path}"
        return format_tool_result(
            coder, tool_name, success_message, change_id=final_change_id, diff_snippet=diff_snippet
        )

    except ToolError as e:
        # Handle errors raised by utility functions (expected errors)
        return handle_tool_error(coder, tool_name, e, add_traceback=False)
    except Exception as e:
        # Handle unexpected errors
        return handle_tool_error(coder, tool_name, e)