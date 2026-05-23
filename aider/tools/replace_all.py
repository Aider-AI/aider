import traceback
from .tool_utils import (
    ToolError,
    validate_file_for_edit,
    apply_change,
    handle_tool_error,
    generate_unified_diff_snippet,
    format_tool_result,
)

def _execute_replace_all(coder, file_path, find_text, replace_text, change_id=None, dry_run=False):
    """
    Replace all occurrences of text in a file using utility functions.
    """
    # Get absolute file path
    abs_path = coder.abs_root_path(file_path)
    rel_path = coder.get_rel_fname(abs_path)
    tool_name = "ReplaceAll"
    try:
        # 1. Validate file and get content
        abs_path, rel_path, original_content = validate_file_for_edit(coder, file_path)

        # 2. Count occurrences
        count = original_content.count(find_text)
        if count == 0:
            coder.io.tool_warning(f"Text '{find_text}' not found in file '{file_path}'")
            return f"Warning: Text not found in file"

        # 3. Perform the replacement
        new_content = original_content.replace(find_text, replace_text)

        if original_content == new_content:
            coder.io.tool_warning(f"No changes made: replacement text is identical to original")
            return f"Warning: No changes made (replacement identical to original)"

        # 4. Generate diff for feedback
        diff_examples = generate_unified_diff_snippet(original_content, new_content, rel_path)

        # 5. Handle dry run
        if dry_run:
            dry_run_message = f"Dry run: Would replace {count} occurrences of '{find_text}' in {file_path}."
            return format_tool_result(coder, tool_name, "", dry_run=True, dry_run_message=dry_run_message, diff_snippet=diff_examples)

        # 6. Apply Change (Not dry run)
        metadata = {
            'find_text': find_text,
            'replace_text': replace_text,
            'occurrences': count
        }
        final_change_id = apply_change(
            coder, abs_path, rel_path, original_content, new_content, 'replaceall', metadata, change_id
        )

        # 7. Format and return result
        success_message = f"Replaced {count} occurrences in {file_path}"
        return format_tool_result(
            coder, tool_name, success_message, change_id=final_change_id, diff_snippet=diff_examples
        )

    except ToolError as e:
        # Handle errors raised by utility functions
        return handle_tool_error(coder, tool_name, e, add_traceback=False)
    except Exception as e:
        # Handle unexpected errors
        return handle_tool_error(coder, tool_name, e)