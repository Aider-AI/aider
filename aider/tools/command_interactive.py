# Import necessary functions
from aider.run_cmd import run_cmd

def _execute_command_interactive(coder, command_string):
    """
    Execute an interactive shell command using run_cmd (which uses pexpect/PTY).
    """
    try:
        coder.io.tool_output(f"⚙️ Starting interactive shell command: {command_string}")
        coder.io.tool_output(">>> You may need to interact with the command below <<<")

        # Use run_cmd which handles PTY logic
        exit_status, combined_output = run_cmd(
            command_string,
            verbose=coder.verbose, # Pass verbose flag
            error_print=coder.io.tool_error, # Use io for error printing
            cwd=coder.root # Execute in the project root
        )

        coder.io.tool_output(">>> Interactive command finished <<<")

        # Format the output for the result message, include more content
        output_content = combined_output or ""
        # Use the existing token threshold constant as the character limit for truncation
        output_limit = coder.large_file_token_threshold
        if len(output_content) > output_limit:
            # Truncate and add a clear message using the constant value
            output_content = output_content[:output_limit] + f"\n... (output truncated at {output_limit} characters, based on large_file_token_threshold)"

        if exit_status == 0:
            return f"Interactive command finished successfully (exit code 0). Output:\n{output_content}"
        else:
            return f"Interactive command finished with exit code {exit_status}. Output:\n{output_content}"

    except Exception as e:
        coder.io.tool_error(f"Error executing interactive shell command '{command_string}': {str(e)}")
        # Optionally include traceback for debugging if verbose
        # if coder.verbose:
        #     coder.io.tool_error(traceback.format_exc())
        return f"Error executing interactive command: {str(e)}"
