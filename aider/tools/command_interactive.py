# Import necessary functions
import asyncio

from aider.run_cmd import run_cmd

schema = {
    "type": "function",
    "function": {
        "name": "CommandInteractive",
        "description": "Execute a shell command interactively.",
        "parameters": {
            "type": "object",
            "properties": {
                "command_string": {
                    "type": "string",
                    "description": "The interactive shell command to execute.",
                },
            },
            "required": ["command_string"],
        },
    },
}

# Normalized tool name for lookup
NORM_NAME = "commandinteractive"


async def _execute_command_interactive(coder, command_string):
    """
    Execute an interactive shell command using run_cmd (which uses pexpect/PTY).
    """
    try:
        confirmed = (
            True
            if coder.skip_cli_confirmations
            else await coder.io.confirm_ask(
                "Allow execution of this command?",
                subject=command_string,
                explicit_yes_required=True,  # Require explicit 'yes' or 'always'
                allow_never=True,  # Enable the 'Always' option
                group_response="Command Interactive Tool",
            )
        )

        if not confirmed:
            # This happens if the user explicitly says 'no' this time.
            # If 'Always' was chosen previously, confirm_ask returns True directly.
            coder.io.tool_output(f"Skipped execution of shell command: {command_string}")
            return "Shell command execution skipped by user."

        coder.io.tool_output(f"⚙️ Starting interactive shell command: {command_string}")
        coder.io.tool_output(">>> You may need to interact with the command below <<<")
        coder.io.tool_output(" \n")

        await coder.io.cancel_input_task()
        await asyncio.sleep(1)

        # Use run_cmd which handles PTY logic
        exit_status, combined_output = run_cmd(
            command_string,
            verbose=coder.verbose,  # Pass verbose flag
            error_print=coder.io.tool_error,  # Use io for error printing
            cwd=coder.root,  # Execute in the project root
        )

        await asyncio.sleep(1)

        coder.io.tool_output(" \n")
        coder.io.tool_output(" \n")
        coder.io.tool_output(">>> Interactive command finished <<<")

        await coder.io.recreate_input()

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
            return (
                "Interactive command finished successfully (exit code 0)."
                f" Output:\n{output_content}"
            )
        else:
            return (
                f"Interactive command finished with exit code {exit_status}."
                f" Output:\n{output_content}"
            )

    except Exception as e:
        coder.io.tool_error(
            f"Error executing interactive shell command '{command_string}': {str(e)}"
        )
        # Optionally include traceback for debugging if verbose
        # if coder.verbose:
        #     coder.io.tool_error(traceback.format_exc())
        return f"Error executing interactive command: {str(e)}"


async def process_response(coder, params):
    """
    Process the CommandInteractive tool response.

    Args:
        coder: The Coder instance
        params: Dictionary of parameters

    Returns:
        str: Result message
    """
    command_string = params.get("command_string")
    if command_string is not None:
        return await _execute_command_interactive(coder, command_string)
    else:
        return "Error: Missing 'command_string' parameter for CommandInteractive"
