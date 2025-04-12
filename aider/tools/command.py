# Import necessary functions
from aider.run_cmd import run_cmd_subprocess

def _execute_command(coder, command_string):
    """
    Execute a non-interactive shell command after user confirmation.
    """
    try:
        # Ask for confirmation before executing, allowing 'Always'
        # Use the command string itself as the group key to remember preference per command
        if not coder.io.confirm_ask(
            "Allow execution of this command?",
            subject=command_string,
            explicit_yes_required=True, # Require explicit 'yes' or 'always'
            allow_never=True           # Enable the 'Don't ask again' option
        ):
            # Check if the reason for returning False was *not* because it's remembered
            # (confirm_ask returns False if 'n' or 'no' is chosen, even if remembered)
            # We only want to skip if the user actively said no *this time* or if it's
            # remembered as 'never' (which shouldn't happen with allow_never=True,
            # but checking io.never_ask_group is robust).
            # If the command is in never_ask_group with a True value (meaning Always),
            # confirm_ask would have returned True directly.
            # So, if confirm_ask returns False here, it means the user chose No this time.
            coder.io.tool_output(f"Skipped execution of shell command: {command_string}")
            return "Shell command execution skipped by user."

        coder.io.tool_output(f"⚙️ Executing non-interactive shell command: {command_string}")

        # Use run_cmd_subprocess for non-interactive execution
        exit_status, combined_output = run_cmd_subprocess(
            command_string,
            verbose=coder.verbose,
            cwd=coder.root # Execute in the project root
        )

        # Format the output for the result message, include more content
        output_content = combined_output or ""
        # Use the existing token threshold constant as the character limit for truncation
        output_limit = coder.large_file_token_threshold
        if len(output_content) > output_limit:
            # Truncate and add a clear message using the constant value
            output_content = output_content[:output_limit] + f"\n... (output truncated at {output_limit} characters, based on large_file_token_threshold)"

        if exit_status == 0:
            return f"Shell command executed successfully (exit code 0). Output:\n{output_content}"
        else:
            return f"Shell command failed with exit code {exit_status}. Output:\n{output_content}"

    except Exception as e:
        coder.io.tool_error(f"Error executing non-interactive shell command '{command_string}': {str(e)}")
        # Optionally include traceback for debugging if verbose
        # if coder.verbose:
        #     coder.io.tool_error(traceback.format_exc())
        return f"Error executing command: {str(e)}"
