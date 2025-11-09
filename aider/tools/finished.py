schema = {
    "type": "function",
    "function": {
        "name": "Finished",
        "description": (
            "Declare that we are done with every single sub goal and no further work is needed."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}

# Normalized tool name for lookup
NORM_NAME = "finished"


def _execute_finished(coder):
    """
    Mark that the current generation task needs no further effort.

    This gives the LLM explicit control over when it can stop looping
    """

    if coder:
        coder.agent_finished = True
        # coder.io.tool_output("Task Finished!")
        return "Task Finished!"

    # coder.io.tool_Error("Error: Could not mark agent task as finished")
    return "Error: Could not mark agent task as finished"


def process_response(coder, params):
    """
    Process the Finished tool response.

    Args:
        coder: The Coder instance
        params: Dictionary of parameters (should be empty for Finished)

    Returns:
        str: Result message
    """
    # Finished tool has no parameters to validate
    return _execute_finished(coder)
