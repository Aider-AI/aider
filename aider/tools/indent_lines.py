import os
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

def _execute_indent_lines(coder, file_path, start_pattern, end_pattern=None, line_count=None, indent_levels=1, near_context=None, occurrence=1, change_id=None, dry_run=False):
    """
    Indent or unindent a block of lines in a file using utility functions.

    Parameters:
    - coder: The Coder instance
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
    tool_name = "IndentLines"
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

        # 3. Determine the end line
        start_line, end_line = determine_line_range(
            coder=coder,
            file_path=rel_path,
            lines=lines,
            start_pattern_line_index=start_line_idx,
            end_pattern=end_pattern,
            line_count=line_count,
            target_symbol=None, # IndentLines uses patterns, not symbols
            pattern_desc=pattern_desc
        )

        # 4. Validate and prepare indentation
        try:
            indent_levels = int(indent_levels)
        except ValueError:
            raise ToolError(f"Invalid indent_levels value: '{indent_levels}'. Must be an integer.")

        indent_str = ' ' * 4 # Assume 4 spaces per level
        modified_lines = list(lines)

        # Apply indentation logic (core logic remains)
        for i in range(start_line, end_line + 1):
            if indent_levels > 0:
                modified_lines[i] = (indent_str * indent_levels) + modified_lines[i]
            elif indent_levels < 0:
                spaces_to_remove = abs(indent_levels) * len(indent_str)
                current_leading_spaces = len(modified_lines[i]) - len(modified_lines[i].lstrip(' '))
                actual_remove = min(spaces_to_remove, current_leading_spaces)
                if actual_remove > 0:
                    modified_lines[i] = modified_lines[i][actual_remove:]

        new_content = '\n'.join(modified_lines)

        if original_content == new_content:
            coder.io.tool_warning(f"No changes made: indentation would not change file")
            return f"Warning: No changes made (indentation would not change file)"

        # 5. Generate diff for feedback
        diff_snippet = generate_unified_diff_snippet(original_content, new_content, rel_path)
        num_occurrences = len(start_pattern_indices)
        occurrence_str = f"occurrence {occurrence} of " if num_occurrences > 1 else ""
        action = "indent" if indent_levels > 0 else "unindent"
        levels = abs(indent_levels)
        level_text = "level" if levels == 1 else "levels"
        num_lines = end_line - start_line + 1

        # 6. Handle dry run
        if dry_run:
            dry_run_message = f"Dry run: Would {action} {num_lines} lines ({start_line+1}-{end_line+1}) by {levels} {level_text} (based on {occurrence_str}start pattern '{start_pattern}') in {file_path}."
            return format_tool_result(coder, tool_name, "", dry_run=True, dry_run_message=dry_run_message, diff_snippet=diff_snippet)

        # 7. Apply Change (Not dry run)
        metadata = {
            'start_line': start_line + 1,
            'end_line': end_line + 1,
            'start_pattern': start_pattern,
            'end_pattern': end_pattern,
            'line_count': line_count,
            'indent_levels': indent_levels,
            'near_context': near_context,
            'occurrence': occurrence,
        }
        final_change_id = apply_change(
            coder, abs_path, rel_path, original_content, new_content, 'indentlines', metadata, change_id
        )

        # 8. Format and return result
        action_past = "Indented" if indent_levels > 0 else "Unindented"
        success_message = f"{action_past} {num_lines} lines by {levels} {level_text} (from {occurrence_str}start pattern) in {file_path}"
        return format_tool_result(
            coder, tool_name, success_message, change_id=final_change_id, diff_snippet=diff_snippet
        )
    except ToolError as e:
        # Handle errors raised by utility functions (expected errors)
        return handle_tool_error(coder, tool_name, e, add_traceback=False)
    except Exception as e:
        # Handle unexpected errors
        return handle_tool_error(coder, tool_name, e)