import os
import traceback
from .tool_utils import (
    ToolError,
    validate_file_for_edit,
    find_pattern_indices,
    select_occurrence_index,
    apply_change,
    handle_tool_error,
    format_tool_result,
    generate_unified_diff_snippet,
)

def _execute_insert_block(coder, file_path, content, after_pattern=None, before_pattern=None, near_context=None, occurrence=1, change_id=None, dry_run=False):
    """
    Insert a block of text after or before a specified pattern using utility functions.
    """
    tool_name = "InsertBlock"
    try:
        # 1. Validate parameters
        if after_pattern and before_pattern:
            raise ToolError("Cannot specify both after_pattern and before_pattern")
        if not after_pattern and not before_pattern:
            raise ToolError("Must specify either after_pattern or before_pattern")

        # 2. Validate file and get content
        abs_path, rel_path, original_content = validate_file_for_edit(coder, file_path)
        lines = original_content.splitlines()

        # 3. Find the target line index
        pattern = after_pattern if after_pattern else before_pattern
        pattern_type = "after" if after_pattern else "before"
        pattern_desc = f"Pattern '{pattern}'"
        if near_context:
            pattern_desc += f" near context '{near_context}'"

        pattern_line_indices = find_pattern_indices(lines, pattern, near_context)
        target_line_idx = select_occurrence_index(pattern_line_indices, occurrence, pattern_desc)

        # Determine the final insertion line index
        insertion_line_idx = target_line_idx
        if pattern_type == "after":
            insertion_line_idx += 1 # Insert on the line *after* the matched line

        # 4. Prepare the insertion
        content_lines = content.splitlines()
        new_lines = lines[:insertion_line_idx] + content_lines + lines[insertion_line_idx:]
        new_content = '\n'.join(new_lines)

        if original_content == new_content:
            coder.io.tool_warning(f"No changes made: insertion would not change file")
            return f"Warning: No changes made (insertion would not change file)"

        # 5. Generate diff for feedback
        diff_snippet = generate_unified_diff_snippet(original_content, new_content, rel_path)
        num_occurrences = len(pattern_line_indices)
        occurrence_str = f"occurrence {occurrence} of " if num_occurrences > 1 else ""

        # 6. Handle dry run
        if dry_run:
            dry_run_message = f"Dry run: Would insert block {pattern_type} {occurrence_str}pattern '{pattern}' in {file_path} at line {insertion_line_idx + 1}."
            return format_tool_result(coder, tool_name, "", dry_run=True, dry_run_message=dry_run_message, diff_snippet=diff_snippet)

        # 7. Apply Change (Not dry run)
        metadata = {
            'insertion_line_idx': insertion_line_idx,
            'after_pattern': after_pattern,
            'before_pattern': before_pattern,
            'near_context': near_context,
            'occurrence': occurrence,
            'content': content
        }
        final_change_id = apply_change(
            coder, abs_path, rel_path, original_content, new_content, 'insertblock', metadata, change_id
        )

        # 8. Format and return result
        success_message = f"Inserted block {pattern_type} {occurrence_str}pattern in {file_path} at line {insertion_line_idx + 1}"
        return format_tool_result(
            coder, tool_name, success_message, change_id=final_change_id, diff_snippet=diff_snippet
        )

    except ToolError as e:
        # Handle errors raised by utility functions (expected errors)
        return handle_tool_error(coder, tool_name, e, add_traceback=False)
             
    except Exception as e:
        coder.io.tool_error(f"Error in InsertBlock: {str(e)}\n{traceback.format_exc()}") # Add traceback
        return f"Error: {str(e)}"