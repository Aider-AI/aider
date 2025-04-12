import os

def execute_view_numbered_context(coder, file_path, pattern=None, line_number=None, context_lines=3):
    """
    Displays numbered lines from file_path centered around a target location
    (pattern or line_number), without adding the file to context.
    """
    error_message = None
    if not (pattern is None) ^ (line_number is None):
        error_message = "Provide exactly one of 'pattern' or 'line_number'."
        coder.io.tool_error(error_message)
        return f"Error: {error_message}"

    abs_path = coder.abs_root_path(file_path)
    if not os.path.exists(abs_path):
        error_message = f"File not found: {file_path}"
        coder.io.tool_error(error_message)
        return f"Error: {error_message}"

    try:
        content = coder.io.read_text(abs_path)
        if content is None:
            error_message = f"Could not read file: {file_path}"
            coder.io.tool_error(error_message)
            return f"Error: {error_message}"
        lines = content.splitlines()
        num_lines = len(lines)

        center_line_idx = -1
        found_by = ""

        if line_number is not None:
            try:
                line_number_int = int(line_number)
                if 1 <= line_number_int <= num_lines:
                    center_line_idx = line_number_int - 1 # Convert to 0-based index
                    found_by = f"line {line_number_int}"
                else:
                    error_message = f"Line number {line_number_int} is out of range (1-{num_lines}) for {file_path}."
                    coder.io.tool_error(error_message)
                    return f"Error: {error_message}"
            except ValueError:
                error_message = f"Invalid line number '{line_number}'. Must be an integer."
                coder.io.tool_error(error_message)
                return f"Error: {error_message}"

        elif pattern is not None:
            first_match_line_idx = -1
            for i, line in enumerate(lines):
                if pattern in line:
                    first_match_line_idx = i
                    break
            
            if first_match_line_idx != -1:
                center_line_idx = first_match_line_idx
                found_by = f"pattern '{pattern}' on line {center_line_idx + 1}"
            else:
                error_message = f"Pattern '{pattern}' not found in {file_path}."
                coder.io.tool_error(error_message)
                return f"Error: {error_message}"

        if center_line_idx == -1:
             # Should not happen if logic above is correct, but as a safeguard
             error_message = "Could not determine center line."
             coder.io.tool_error(error_message)
             return f"Error: {error_message}"

        # Calculate context window
        try:
            context_lines_int = int(context_lines)
        except ValueError:
            coder.io.tool_warning(f"Invalid context_lines value '{context_lines}', using default 3.")
            context_lines_int = 3
            
        start_line_idx = max(0, center_line_idx - context_lines_int)
        end_line_idx = min(num_lines - 1, center_line_idx + context_lines_int)

        # Format output
        output_lines = [f"Displaying context around {found_by} in {file_path}:"]
        max_line_num_width = len(str(end_line_idx + 1)) # Width for padding

        for i in range(start_line_idx, end_line_idx + 1):
            line_num_str = str(i + 1).rjust(max_line_num_width)
            output_lines.append(f"{line_num_str} | {lines[i]}")

        return "\n".join(output_lines)

    except Exception as e:
        error_message = f"Error processing {file_path}: {e}"
        coder.io.tool_error(error_message)
        return f"Error: {error_message}"
