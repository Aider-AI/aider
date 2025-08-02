import os
from .tool_utils import ToolError, resolve_paths, handle_tool_error

def execute_show_numbered_context(coder, file_path, pattern=None, line_number=None, context_lines=3):
    """
    Displays numbered lines from file_path centered around a target location
    (pattern or line_number), without adding the file to context.
    Uses utility functions for path resolution and error handling.
    """
    tool_name = "ShowNumberedContext"
    try:
        # 1. Validate arguments
        if not (pattern is None) ^ (line_number is None):
            raise ToolError("Provide exactly one of 'pattern' or 'line_number'.")

        # 2. Resolve path
        abs_path, rel_path = resolve_paths(coder, file_path)
        if not os.path.exists(abs_path):
            # Check existence after resolving, as resolve_paths doesn't guarantee existence
            raise ToolError(f"File not found: {file_path}")

        # 3. Read file content
        content = coder.io.read_text(abs_path)
        if content is None:
            raise ToolError(f"Could not read file: {file_path}")
        lines = content.splitlines()
        num_lines = len(lines)

        # 4. Determine center line index
        center_line_idx = -1
        found_by = ""

        if line_number is not None:
            try:
                line_number_int = int(line_number)
                if 1 <= line_number_int <= num_lines:
                    center_line_idx = line_number_int - 1 # Convert to 0-based index
                    found_by = f"line {line_number_int}"
                else:
                    raise ToolError(f"Line number {line_number_int} is out of range (1-{num_lines}) for {file_path}.")
            except ValueError:
                raise ToolError(f"Invalid line number '{line_number}'. Must be an integer.")

        elif pattern is not None:
            # TODO: Update this section for multiline pattern support later
            first_match_line_idx = -1
            for i, line in enumerate(lines):
                if pattern in line:
                    first_match_line_idx = i
                    break
            
            if first_match_line_idx != -1:
                center_line_idx = first_match_line_idx
                found_by = f"pattern '{pattern}' on line {center_line_idx + 1}"
            else:
                raise ToolError(f"Pattern '{pattern}' not found in {file_path}.")

        if center_line_idx == -1:
             # Should not happen if logic above is correct, but as a safeguard
             raise ToolError("Internal error: Could not determine center line.")

        # 5. Calculate context window
        try:
            context_lines_int = int(context_lines)
            if context_lines_int < 0:
                 raise ValueError("Context lines must be non-negative")
        except ValueError:
            coder.io.tool_warning(f"Invalid context_lines value '{context_lines}', using default 3.")
            context_lines_int = 3
            
        start_line_idx = max(0, center_line_idx - context_lines_int)
        end_line_idx = min(num_lines - 1, center_line_idx + context_lines_int)

        # 6. Format output
        # Use rel_path for user-facing messages
        output_lines = [f"Displaying context around {found_by} in {rel_path}:"]
        max_line_num_width = len(str(end_line_idx + 1)) # Width for padding

        for i in range(start_line_idx, end_line_idx + 1):
            line_num_str = str(i + 1).rjust(max_line_num_width)
            output_lines.append(f"{line_num_str} | {lines[i]}")

        # Log success and return the formatted context directly
        coder.io.tool_output(f"Successfully retrieved context for {rel_path}")
        return "\n".join(output_lines)

    except ToolError as e:
        # Handle expected errors raised by utility functions or validation
        return handle_tool_error(coder, tool_name, e, add_traceback=False)
    except Exception as e:
        # Handle unexpected errors during processing
        return handle_tool_error(coder, tool_name, e)
