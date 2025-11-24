from aider.tools.utils.base_tool import BaseTool
from aider.tools.utils.helpers import (
    ToolError,
    apply_change,
    format_tool_result,
    generate_unified_diff_snippet,
    handle_tool_error,
    validate_file_for_edit,
)
from aider.tools.utils.output import tool_body_unwrapped, tool_footer, tool_header


class Tool(BaseTool):
    NORM_NAME = "replacelines"
    SCHEMA = {
        "type": "function",
        "function": {
            "name": "ReplaceLines",
            "description": "Replace a range of lines in a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "start_line": {"type": "integer"},
                    "end_line": {"type": "integer"},
                    "new_content": {"type": "string"},
                    "change_id": {"type": "string"},
                    "dry_run": {"type": "boolean", "default": False},
                },
                "required": ["file_path", "start_line", "end_line", "new_content"],
            },
        },
    }

    @classmethod
    def execute(
        cls, coder, file_path, start_line, end_line, new_content, change_id=None, dry_run=False
    ):
        """
        Replace a range of lines identified by line numbers.
        Useful for fixing errors identified by error messages or linters.

        Parameters:
        - file_path: Path to the file to modify
        - start_line: The first line number to replace (1-based)
        - end_line: The last line number to replace (1-based)
        - new_content: New content for the lines (can be multi-line)
        - change_id: Optional ID for tracking the change
        - dry_run: If True, simulate the change without modifying the file

        Returns a result message.
        """
        tool_name = "ReplaceLines"
        try:
            # 1. Validate file and get content
            abs_path, rel_path, original_content = validate_file_for_edit(coder, file_path)

            # Convert line numbers to integers if needed
            try:
                start_line = int(start_line)
            except ValueError:
                raise ToolError(f"Invalid start_line value: '{start_line}'. Must be an integer.")

            try:
                end_line = int(end_line)
            except ValueError:
                raise ToolError(f"Invalid end_line value: '{end_line}'. Must be an integer.")

            # Split into lines
            lines = original_content.splitlines()

            # Convert 1-based line numbers to 0-based indices
            start_idx = start_line - 1
            end_idx = end_line - 1

            # Validate line numbers
            if start_idx < 0 or start_idx >= len(lines):
                raise ToolError(
                    f"Start line {start_line} is out of range for file '{file_path}' (has"
                    f" {len(lines)} lines)."
                )

            if end_idx < start_idx or end_idx >= len(lines):
                raise ToolError(
                    f"End line {end_line} is out of range for file '{file_path}' (must be >= start"
                    f" line {start_line} and <= {len(lines)})."
                )

            # Store original content for change tracking
            replaced_lines = lines[start_idx : end_idx + 1]

            # Split the new content into lines
            new_lines = new_content.splitlines()

            # Perform the replacement
            new_full_lines = lines[:start_idx] + new_lines + lines[end_idx + 1 :]
            new_content_full = "\n".join(new_full_lines)

            if original_content == new_content_full:
                coder.io.tool_warning("No changes made: new content is identical to original")
                return "Warning: No changes made (new content identical to original)"

            # Generate diff snippet
            diff_snippet = generate_unified_diff_snippet(
                original_content, new_content_full, rel_path
            )

            # Create a readable diff for the lines replacement
            diff = f"Lines {start_line}-{end_line}:\n"
            # Add removed lines with - prefix
            for line in replaced_lines:
                diff += f"- {line}\n"
            # Add separator
            diff += "---\n"
            # Add new lines with + prefix
            for line in new_lines:
                diff += f"+ {line}\n"

            # Handle dry run
            if dry_run:
                dry_run_message = (
                    f"Dry run: Would replace lines {start_line}-{end_line} in {file_path}"
                )
                return format_tool_result(
                    coder,
                    tool_name,
                    "",
                    dry_run=True,
                    dry_run_message=dry_run_message,
                    diff_snippet=diff_snippet,
                )

            # --- Apply Change (Not dry run) ---
            metadata = {
                "start_line": start_line,
                "end_line": end_line,
                "replaced_lines": replaced_lines,
                "new_lines": new_lines,
            }

            final_change_id = apply_change(
                coder,
                abs_path,
                rel_path,
                original_content,
                new_content_full,
                "replacelines",
                metadata,
                change_id,
            )

            coder.files_edited_by_tools.add(rel_path)
            replaced_count = end_line - start_line + 1
            new_count = len(new_lines)

            # Format and return result
            success_message = (
                f"Replaced lines {start_line}-{end_line} ({replaced_count} lines) with {new_count}"
                f" new lines in {file_path}"
            )
            return format_tool_result(
                coder,
                tool_name,
                success_message,
                change_id=final_change_id,
                diff_snippet=diff_snippet,
            )

        except ToolError as e:
            # Handle errors raised by utility functions (expected errors)
            return handle_tool_error(coder, tool_name, e, add_traceback=False)
        except Exception as e:
            # Handle unexpected errors
            return handle_tool_error(coder, tool_name, e)

    @classmethod
    def format_output(cls, coder, mcp_server, tool_response):
        tool_header(coder=coder, mcp_server=mcp_server, tool_response=tool_response)
        tool_body_unwrapped(coder=coder, tool_response=tool_response)
        tool_footer(coder=coder, tool_response=tool_response)
