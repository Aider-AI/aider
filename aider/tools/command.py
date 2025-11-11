# Import necessary functions
from aider.run_cmd import run_cmd_subprocess

schema = {
    "type": "function",
    "function": {
        "name": "Command",
        "description": "Execute a shell command.",
        "parameters": {
            "type": "object",
            "properties": {
                "command_string": {
                    "type": "string",
                    "description": "The shell command to execute.",
                },
            },
            "required": ["command_string"],
        },
    },
}

# Normalized tool name for lookup
NORM_NAME = "command"


async def _execute_command(coder, command_string):
    """
    Execute a non-interactive shell command after user confirmation.
    """
    try:
        # Ask for confirmation before executing.
        # allow_never=True enables the 'Always' option.
        # confirm_ask handles remembering the 'Always' choice based on the subject.

        confirmed = (
            True
            if coder.skip_cli_confirmations
            else await coder.io.confirm_ask(
                "Allow execution of this command?",
                subject=command_string,
                explicit_yes_required=True,  # Require explicit 'yes' or 'always'
                allow_never=True,  # Enable the 'Always' option
                group_response="Command Tool",
            )
        )

        await coder.io.recreate_input()

        if not confirmed:
            # This happens if the user explicitly says 'no' this time.
            # If 'Always' was chosen previously, confirm_ask returns True directly.
            coder.io.tool_output(f"Skipped execution of shell command: {command_string}")
            return "Shell command execution skipped by user."

        # Proceed with execution if confirmed is True
        coder.io.tool_output(f"⚙️ Executing non-interactive shell command: {command_string}")

        # Use run_cmd_subprocess for non-interactive execution
        exit_status, combined_output = run_cmd_subprocess(
            command_string, verbose=coder.verbose, cwd=coder.root  # Execute in the project root
        )

        # Format the output for the result message, include more content
        output_content = combined_output or ""
        # Use the existing token threshold constant as the character limit for truncation
        output_limit = coder.large_file_token_threshold
        if len(output_content) > output_limit:
            # Truncate and add a clear message using the constant value
            output_content = (
                output_content[:output_limit]
                + f"\n... (output truncated at {output_limit} characters, based on"
                " large_file_token_threshold)"
            )

        if exit_status == 0:
            return f"Shell command executed successfully (exit code 0). Output:\n{output_content}"
        else:
            return f"Shell command failed with exit code {exit_status}. Output:\n{output_content}"

    except Exception as e:
        coder.io.tool_error(
            f"Error executing non-interactive shell command '{command_string}': {str(e)}"
        )
        # Optionally include traceback for debugging if verbose
        # if coder.verbose:
        #     coder.io.tool_error(traceback.format_exc())
        return f"Error executing command: {str(e)}"


async def process_response(coder, params):
    """
    Process the Command tool response.

    Args:
        coder: The Coder instance
        params: Dictionary of parameters

    Returns:
        str: Result message
    """
    command_string = params.get("command_string")
    if command_string is not None:
        return await _execute_command(coder, command_string)
    else:
        return "Error: Missing 'command_string' parameter for Command"
