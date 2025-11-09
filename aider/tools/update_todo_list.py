from .tool_utils import (
    ToolError,
    format_tool_result,
    generate_unified_diff_snippet,
    handle_tool_error,
)

schema = {
    "type": "function",
    "function": {
        "name": "UpdateTodoList",
        "description": "Update the todo list with new items or modify existing ones.",
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The new content for the todo list.",
                },
                "append": {
                    "type": "boolean",
                    "description": (
                        "Whether to append to existing content instead of replacing it. Defaults to"
                        " False."
                    ),
                },
                "change_id": {
                    "type": "string",
                    "description": "Optional change ID for tracking.",
                },
                "dry_run": {
                    "type": "boolean",
                    "description": (
                        "Whether to perform a dry run without actually updating the file. Defaults"
                        " to False."
                    ),
                },
            },
            "required": ["content"],
        },
    },
}

# Normalized tool name for lookup
NORM_NAME = "updatetodolist"


def _execute_update_todo_list(coder, content, append=False, change_id=None, dry_run=False):
    """
    Update the todo list file (.aider.todo.txt) with new content.
    Can either replace the entire content or append to it.
    """
    tool_name = "UpdateTodoList"
    try:
        # Define the todo file path
        todo_file_path = ".aider.todo.txt"
        abs_path = coder.abs_root_path(todo_file_path)

        # Get existing content if appending
        existing_content = ""
        import os

        if os.path.isfile(abs_path):
            existing_content = coder.io.read_text(abs_path) or ""

        # Prepare new content
        if append:
            if existing_content and not existing_content.endswith("\n"):
                existing_content += "\n"
            new_content = existing_content + content
        else:
            new_content = content

        # Check if content exceeds 4096 characters and warn
        if len(new_content) > 4096:
            coder.io.tool_warning(
                "⚠️ Todo list content exceeds 4096 characters. Consider summarizing the plan before"
                " proceeding."
            )

        # Check if content actually changed
        if existing_content == new_content:
            coder.io.tool_warning("No changes made: new content is identical to existing")
            return "Warning: No changes made (content identical to existing)"

        # Generate diff for feedback
        diff_snippet = generate_unified_diff_snippet(existing_content, new_content, todo_file_path)

        # Handle dry run
        if dry_run:
            action = "append to" if append else "replace"
            dry_run_message = f"Dry run: Would {action} todo list in {todo_file_path}."
            return format_tool_result(
                coder,
                tool_name,
                "",
                dry_run=True,
                dry_run_message=dry_run_message,
                diff_snippet=diff_snippet,
            )

        # Apply change
        metadata = {
            "append": append,
            "existing_length": len(existing_content),
            "new_length": len(new_content),
        }

        # Write the file directly since it's a special file
        coder.io.write_text(abs_path, new_content)

        # Track the change
        final_change_id = coder.change_tracker.track_change(
            file_path=todo_file_path,
            change_type="updatetodolist",
            original_content=existing_content,
            new_content=new_content,
            metadata=metadata,
            change_id=change_id,
        )

        coder.aider_edited_files.add(todo_file_path)

        # Format and return result
        action = "appended to" if append else "updated"
        success_message = f"Successfully {action} todo list in {todo_file_path}"
        return format_tool_result(
            coder, tool_name, success_message, change_id=final_change_id, diff_snippet=diff_snippet
        )

    except ToolError as e:
        return handle_tool_error(coder, tool_name, e, add_traceback=False)
    except Exception as e:
        return handle_tool_error(coder, tool_name, e)


def process_response(coder, params):
    """
    Process the UpdateTodoList tool response.

    Args:
        coder: The Coder instance
        params: Dictionary of parameters

    Returns:
        str: Result message
    """
    content = params.get("content")
    append = params.get("append", False)
    change_id = params.get("change_id")
    dry_run = params.get("dry_run", False)

    if content is not None:
        return _execute_update_todo_list(coder, content, append, change_id, dry_run)
    else:
        return "Error: Missing required 'content' parameter for UpdateTodoList"
