from .tool_utils import ToolError, format_tool_result, handle_tool_error

view_todo_list_schema = {
    "type": "function",
    "function": {
        "name": "ViewTodoList",
        "description": "View the current todo list for tracking conversation steps and progress.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}


def _execute_view_todo_list(coder):
    """
    View the current todo list from .aider.todo.txt file.
    Returns the todo list content or creates an empty one if it doesn't exist.
    """
    tool_name = "ViewTodoList"
    try:
        # Define the todo file path
        todo_file_path = ".aider.todo.txt"
        abs_path = coder.abs_root_path(todo_file_path)

        # Check if file exists
        import os

        if os.path.isfile(abs_path):
            # Read existing todo list
            content = coder.io.read_text(abs_path)
            if content is None:
                raise ToolError(f"Could not read todo list file: {todo_file_path}")

            # Check if content exceeds 4096 characters and warn
            if len(content) > 4096:
                coder.io.tool_warning(
                    "⚠️ Todo list content exceeds 4096 characters. Consider summarizing the plan"
                    " before proceeding."
                )

            if content.strip():
                result_message = f"Current todo list:\n```\n{content}\n```"
            else:
                result_message = "Todo list is empty. Use UpdateTodoList to add items."
        else:
            # Create empty todo list
            result_message = "Todo list is empty. Use UpdateTodoList to add items."

        return format_tool_result(coder, tool_name, result_message)

    except ToolError as e:
        return handle_tool_error(coder, tool_name, e, add_traceback=False)
    except Exception as e:
        return handle_tool_error(coder, tool_name, e)
