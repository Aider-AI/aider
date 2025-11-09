from .tool_utils import (
    ToolError,
    apply_change,
    format_tool_result,
    generate_unified_diff_snippet,
    handle_tool_error,
    validate_file_for_edit,
)

schema = {
    "type": "function",
    "function": {
        "name": "ReplaceAll",
        "description": "Replace all occurrences of text in a file.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "find_text": {"type": "string"},
                "replace_text": {"type": "string"},
                "change_id": {"type": "string"},
                "dry_run": {"type": "boolean", "default": False},
            },
            "required": ["file_path", "find_text", "replace_text"],
        },
    },
}

# Normalized tool name for lookup
NORM_NAME = "replaceall"


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
            return "Warning: Text not found in file"

        # 3. Perform the replacement
        new_content = original_content.replace(find_text, replace_text)

        if original_content == new_content:
            coder.io.tool_warning("No changes made: replacement text is identical to original")
            return "Warning: No changes made (replacement identical to original)"

        # 4. Generate diff for feedback
        diff_examples = generate_unified_diff_snippet(original_content, new_content, rel_path)

        # 5. Handle dry run
        if dry_run:
            dry_run_message = (
                f"Dry run: Would replace {count} occurrences of '{find_text}' in {file_path}."
            )
            return format_tool_result(
                coder,
                tool_name,
                "",
                dry_run=True,
                dry_run_message=dry_run_message,
                diff_snippet=diff_examples,
            )

        # 6. Apply Change (Not dry run)
        metadata = {"find_text": find_text, "replace_text": replace_text, "occurrences": count}
        final_change_id = apply_change(
            coder,
            abs_path,
            rel_path,
            original_content,
            new_content,
            "replaceall",
            metadata,
            change_id,
        )

        coder.files_edited_by_tools.add(rel_path)

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


def process_response(coder, params):
    """
    Process the ReplaceAll tool response.

    Args:
        coder: The Coder instance
        params: Dictionary of parameters

    Returns:
        str: Result message
    """
    file_path = params.get("file_path")
    find_text = params.get("find_text")
    replace_text = params.get("replace_text")
    change_id = params.get("change_id")
    dry_run = params.get("dry_run", False)

    if file_path is not None and find_text is not None and replace_text is not None:
        return _execute_replace_all(coder, file_path, find_text, replace_text, change_id, dry_run)
    else:
        return (
            "Error: Missing required parameters for ReplaceAll (file_path, find_text, replace_text)"
        )
