import os
import traceback
from .tool_utils import generate_unified_diff_snippet

def _execute_extract_lines(coder, source_file_path, target_file_path, start_pattern, end_pattern=None, line_count=None, near_context=None, occurrence=1, dry_run=False):
    """
    Extract a range of lines from a source file and move them to a target file.

    Parameters:
    - coder: The Coder instance
    - source_file_path: Path to the file to extract lines from
    - target_file_path: Path to the file to append extracted lines to (will be created if needed)
    - start_pattern: Pattern marking the start of the block to extract
    - end_pattern: Optional pattern marking the end of the block
    - line_count: Optional number of lines to extract (alternative to end_pattern)
    - near_context: Optional text nearby to help locate the correct instance of the start_pattern
    - occurrence: Which occurrence of the start_pattern to use (1-based index, or -1 for last)
    - dry_run: If True, simulate the change without modifying files

    Returns a result message.
    """
    try:
        # --- Validate Source File ---
        abs_source_path = coder.abs_root_path(source_file_path)
        rel_source_path = coder.get_rel_fname(abs_source_path)

        if not os.path.isfile(abs_source_path):
            coder.io.tool_error(f"Source file '{source_file_path}' not found")
            return f"Error: Source file not found"

        if abs_source_path not in coder.abs_fnames:
            if abs_source_path in coder.abs_read_only_fnames:
                coder.io.tool_error(f"Source file '{source_file_path}' is read-only. Use MakeEditable first.")
                return f"Error: Source file is read-only. Use MakeEditable first."
            else:
                coder.io.tool_error(f"Source file '{source_file_path}' not in context")
                return f"Error: Source file not in context"

        # --- Validate Target File ---
        abs_target_path = coder.abs_root_path(target_file_path)
        rel_target_path = coder.get_rel_fname(abs_target_path)
        target_exists = os.path.isfile(abs_target_path)
        target_is_editable = abs_target_path in coder.abs_fnames
        target_is_readonly = abs_target_path in coder.abs_read_only_fnames

        if target_exists and not target_is_editable:
            if target_is_readonly:
                coder.io.tool_error(f"Target file '{target_file_path}' exists but is read-only. Use MakeEditable first.")
                return f"Error: Target file exists but is read-only. Use MakeEditable first."
            else:
                # This case shouldn't happen if file exists, but handle defensively
                coder.io.tool_error(f"Target file '{target_file_path}' exists but is not in context. Add it first.")
                return f"Error: Target file exists but is not in context."

        # --- Read Source Content ---
        source_content = coder.io.read_text(abs_source_path)
        if source_content is None:
            coder.io.tool_error(f"Could not read source file '{source_file_path}' before ExtractLines operation.")
            return f"Error: Could not read source file '{source_file_path}'"

        # --- Find Extraction Range ---
        if end_pattern and line_count:
            coder.io.tool_error("Cannot specify both end_pattern and line_count")
            return "Error: Cannot specify both end_pattern and line_count"

        source_lines = source_content.splitlines()
        original_source_content = source_content

        start_pattern_line_indices = []
        for i, line in enumerate(source_lines):
            if start_pattern in line:
                if near_context:
                    context_window_start = max(0, i - 5)
                    context_window_end = min(len(source_lines), i + 6)
                    context_block = "\n".join(source_lines[context_window_start:context_window_end])
                    if near_context in context_block:
                        start_pattern_line_indices.append(i)
                else:
                    start_pattern_line_indices.append(i)

        if not start_pattern_line_indices:
            err_msg = f"Start pattern '{start_pattern}' not found"
            if near_context: err_msg += f" near context '{near_context}'"
            err_msg += f" in source file '{source_file_path}'."
            coder.io.tool_error(err_msg)
            return f"Error: {err_msg}"

        num_occurrences = len(start_pattern_line_indices)
        try:
            occurrence = int(occurrence)
            if occurrence == -1:
                target_idx = num_occurrences - 1
            elif occurrence > 0 and occurrence <= num_occurrences:
                target_idx = occurrence - 1
            else:
                err_msg = f"Occurrence number {occurrence} is out of range for start pattern '{start_pattern}'. Found {num_occurrences} occurrences"
                if near_context: err_msg += f" near '{near_context}'"
                err_msg += f" in '{source_file_path}'."
                coder.io.tool_error(err_msg)
                return f"Error: {err_msg}"
        except ValueError:
            coder.io.tool_error(f"Invalid occurrence value: '{occurrence}'. Must be an integer.")
            return f"Error: Invalid occurrence value '{occurrence}'"

        start_line = start_pattern_line_indices[target_idx]
        occurrence_str = f"occurrence {occurrence} of " if num_occurrences > 1 else ""

        end_line = -1
        if end_pattern:
            for i in range(start_line, len(source_lines)):
                if end_pattern in source_lines[i]:
                    end_line = i
                    break
            if end_line == -1:
                err_msg = f"End pattern '{end_pattern}' not found after {occurrence_str}start pattern '{start_pattern}' (line {start_line + 1}) in '{source_file_path}'."
                coder.io.tool_error(err_msg)
                return f"Error: {err_msg}"
        elif line_count:
            try:
                line_count = int(line_count)
                if line_count <= 0: raise ValueError("Line count must be positive")
                end_line = min(start_line + line_count - 1, len(source_lines) - 1)
            except ValueError:
                coder.io.tool_error(f"Invalid line_count value: '{line_count}'. Must be a positive integer.")
                return f"Error: Invalid line_count value '{line_count}'"
        else:
            end_line = start_line # Extract just the start line if no end specified

        # --- Prepare Content Changes ---
        extracted_lines = source_lines[start_line:end_line+1]
        new_source_lines = source_lines[:start_line] + source_lines[end_line+1:]
        new_source_content = '\n'.join(new_source_lines)

        target_content = ""
        if target_exists:
            target_content = coder.io.read_text(abs_target_path)
            if target_content is None:
                coder.io.tool_error(f"Could not read existing target file '{target_file_path}'.")
                return f"Error: Could not read target file '{target_file_path}'"
        original_target_content = target_content # For tracking

        # Append extracted lines to target content, ensuring a newline if target wasn't empty
        extracted_block = '\n'.join(extracted_lines)
        if target_content and not target_content.endswith('\n'):
             target_content += '\n' # Add newline before appending if needed
        new_target_content = target_content + extracted_block

        # --- Generate Diffs ---
        source_diff_snippet = generate_unified_diff_snippet(original_source_content, new_source_content, rel_source_path)
        target_insertion_line = len(target_content.splitlines()) if target_content else 0
        target_diff_snippet = generate_unified_diff_snippet(original_target_content, new_target_content, rel_target_path)

        # --- Handle Dry Run ---
        if dry_run:
            num_extracted = end_line - start_line + 1
            target_action = "append to" if target_exists else "create"
            coder.io.tool_output(f"Dry run: Would extract {num_extracted} lines (from {occurrence_str}start pattern '{start_pattern}') in {source_file_path} and {target_action} {target_file_path}")
            # Provide more informative dry run response with diffs
            return (
                f"Dry run: Would extract {num_extracted} lines from {rel_source_path} and {target_action} {rel_target_path}.\n"
                f"Source Diff (Deletion):\n{source_diff_snippet}\n"
                f"Target Diff (Insertion):\n{target_diff_snippet}"
            )

        # --- Apply Changes (Not Dry Run) ---
        coder.io.write_text(abs_source_path, new_source_content)
        coder.io.write_text(abs_target_path, new_target_content)

        # --- Track Changes ---
        source_change_id = "TRACKING_FAILED"
        target_change_id = "TRACKING_FAILED"
        try:
            source_metadata = {
                'start_line': start_line + 1, 'end_line': end_line + 1,
                'start_pattern': start_pattern, 'end_pattern': end_pattern, 'line_count': line_count,
                'near_context': near_context, 'occurrence': occurrence,
                'extracted_content': extracted_block, 'target_file': rel_target_path
            }
            source_change_id = coder.change_tracker.track_change(
                file_path=rel_source_path, change_type='extractlines_source',
                original_content=original_source_content, new_content=new_source_content,
                metadata=source_metadata
            )
        except Exception as track_e:
            coder.io.tool_error(f"Error tracking source change for ExtractLines: {track_e}")

        try:
            target_metadata = {
                'insertion_line': target_insertion_line + 1,
                'inserted_content': extracted_block, 'source_file': rel_source_path
            }
            target_change_id = coder.change_tracker.track_change(
                file_path=rel_target_path, change_type='extractlines_target',
                original_content=original_target_content, new_content=new_target_content,
                metadata=target_metadata
            )
        except Exception as track_e:
            coder.io.tool_error(f"Error tracking target change for ExtractLines: {track_e}")

        # --- Update Context ---
        coder.aider_edited_files.add(rel_source_path)
        coder.aider_edited_files.add(rel_target_path)
        if not target_exists:
            # Add the newly created file to editable context
            coder.abs_fnames.add(abs_target_path)
            coder.io.tool_output(f"✨ Created and added '{target_file_path}' to editable context.")

        # --- Return Result ---
        num_extracted = end_line - start_line + 1
        target_action = "appended to" if target_exists else "created"
        coder.io.tool_output(f"✅ Extracted {num_extracted} lines from {rel_source_path} (change_id: {source_change_id}) and {target_action} {rel_target_path} (change_id: {target_change_id})")
        # Provide more informative success response with change IDs and diffs
        return (
            f"Successfully extracted {num_extracted} lines from {rel_source_path} and {target_action} {rel_target_path}.\n"
            f"Source Change ID: {source_change_id}\nSource Diff (Deletion):\n{source_diff_snippet}\n"
            f"Target Change ID: {target_change_id}\nTarget Diff (Insertion):\n{target_diff_snippet}"
        )

    except Exception as e:
        coder.io.tool_error(f"Error in ExtractLines: {str(e)}\n{traceback.format_exc()}")
        return f"Error: {str(e)}"