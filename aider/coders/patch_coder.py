import pathlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from .base_coder import Coder
from .patch_prompts import PatchPrompts


# --------------------------------------------------------------------------- #
#  Domain objects & Exceptions (Adapted from apply_patch.py)
# --------------------------------------------------------------------------- #
class DiffError(ValueError):
    """Any problem detected while parsing or applying a patch."""


class ActionType(str, Enum):
    ADD = "Add"
    DELETE = "Delete"
    UPDATE = "Update"


@dataclass
class Chunk:
    orig_index: int = -1  # Line number in the *original* file block where the change starts
    del_lines: List[str] = field(default_factory=list)
    ins_lines: List[str] = field(default_factory=list)


@dataclass
class PatchAction:
    type: ActionType
    path: str
    # For ADD:
    new_content: Optional[str] = None
    # For UPDATE:
    chunks: List[Chunk] = field(default_factory=list)
    move_path: Optional[str] = None


# Type alias for the return type of get_edits
EditResult = Tuple[str, PatchAction]


@dataclass
class Patch:
    actions: Dict[str, PatchAction] = field(default_factory=dict)
    fuzz: int = 0  # Track fuzziness used during parsing


# --------------------------------------------------------------------------- #
#  Helper functions (Adapted from apply_patch.py)
# --------------------------------------------------------------------------- #
def _norm(line: str) -> str:
    """Strip CR so comparisons work for both LF and CRLF input."""
    return line.rstrip("\r")


def find_context_core(lines: List[str], context: List[str], start: int) -> Tuple[int, int]:
    """Finds context block, returns start index and fuzz level."""
    if not context:
        return start, 0

    # Exact match
    for i in range(start, len(lines) - len(context) + 1):
        if lines[i : i + len(context)] == context:
            return i, 0
    # Rstrip match
    norm_context = [s.rstrip() for s in context]
    for i in range(start, len(lines) - len(context) + 1):
        if [s.rstrip() for s in lines[i : i + len(context)]] == norm_context:
            return i, 1  # Fuzz level 1
    # Strip match
    norm_context_strip = [s.strip() for s in context]
    for i in range(start, len(lines) - len(context) + 1):
        if [s.strip() for s in lines[i : i + len(context)]] == norm_context_strip:
            return i, 100  # Fuzz level 100
    return -1, 0


def find_context(lines: List[str], context: List[str], start: int, eof: bool) -> Tuple[int, int]:
    """Finds context, handling EOF marker."""
    if eof:
        # If EOF marker, first try matching at the very end
        if len(lines) >= len(context):
            new_index, fuzz = find_context_core(lines, context, len(lines) - len(context))
            if new_index != -1:
                return new_index, fuzz
        # If not found at end, search from `start` as fallback
        new_index, fuzz = find_context_core(lines, context, start)
        return new_index, fuzz + 10_000  # Add large fuzz penalty if EOF wasn't at end
    # Normal case: search from `start`
    return find_context_core(lines, context, start)


def peek_next_section(lines: List[str], index: int) -> Tuple[List[str], List[Chunk], int, bool]:
    """
    Parses one section (context, -, + lines) of an Update block.
    Returns: (context_lines, chunks_in_section, next_index, is_eof)
    """
    context_lines: List[str] = []
    del_lines: List[str] = []
    ins_lines: List[str] = []
    chunks: List[Chunk] = []
    mode = "keep"  # Start by expecting context lines
    start_index = index

    while index < len(lines):
        line = lines[index]
        norm_line = _norm(line)

        # Check for section terminators
        if norm_line.startswith(
            (
                "@@",
                "*** End Patch",
                "*** Update File:",
                "*** Delete File:",
                "*** Add File:",
                "*** End of File",  # Special terminator
            )
        ):
            break
        if norm_line == "***":  # Legacy/alternative terminator? Handle just in case.
            break
        if norm_line.startswith("***"):  # Invalid line
            raise DiffError(f"Invalid patch line found in update section: {line}")

        index += 1
        last_mode = mode

        # Determine line type and strip prefix
        if line.startswith("+"):
            mode = "add"
            line_content = line[1:]
        elif line.startswith("-"):
            mode = "delete"
            line_content = line[1:]
        elif line.startswith(" "):
            mode = "keep"
            line_content = line[1:]
        elif line.strip() == "":  # Treat blank lines in patch as context ' '
            mode = "keep"
            line_content = ""  # Keep it as a blank line
        else:
            # Assume lines without prefix are context if format is loose,
            # but strict format requires ' '. Raise error for strictness.
            raise DiffError(f"Invalid line prefix in update section: {line}")

        # If mode changes from add/delete back to keep, finalize the previous chunk
        if mode == "keep" and last_mode != "keep":
            if del_lines or ins_lines:
                chunks.append(
                    Chunk(
                        # orig_index is relative to the start of the *context* block found
                        orig_index=len(context_lines) - len(del_lines),
                        del_lines=del_lines,
                        ins_lines=ins_lines,
                    )
                )
            del_lines, ins_lines = [], []

        # Collect lines based on mode
        if mode == "delete":
            del_lines.append(line_content)
            context_lines.append(line_content)  # Deleted lines are part of the original context
        elif mode == "add":
            ins_lines.append(line_content)
        elif mode == "keep":
            context_lines.append(line_content)

    # Finalize any pending chunk at the end of the section
    if del_lines or ins_lines:
        chunks.append(
            Chunk(
                orig_index=len(context_lines) - len(del_lines),
                del_lines=del_lines,
                ins_lines=ins_lines,
            )
        )

    # Check for EOF marker
    is_eof = False
    if index < len(lines) and _norm(lines[index]) == "*** End of File":
        index += 1
        is_eof = True

    if index == start_index and not is_eof:  # Should not happen if patch is well-formed
        raise DiffError("Empty patch section found.")

    return context_lines, chunks, index, is_eof


def identify_files_needed(text: str) -> List[str]:
    """Extracts file paths from Update and Delete actions."""
    lines = text.splitlines()
    paths = set()
    for line in lines:
        norm_line = _norm(line)
        if norm_line.startswith("*** Update File: "):
            paths.add(norm_line[len("*** Update File: ") :].strip())
        elif norm_line.startswith("*** Delete File: "):
            paths.add(norm_line[len("*** Delete File: ") :].strip())
    return list(paths)


# --------------------------------------------------------------------------- #
#  PatchCoder Class Implementation
# --------------------------------------------------------------------------- #
class PatchCoder(Coder):
    """
    A coder that uses a custom patch format for code modifications,
    inspired by the format described in tmp.gpt41edits.txt.
    Applies patches using logic adapted from the reference apply_patch.py script.
    """

    edit_format = "patch"
    gpt_prompts = PatchPrompts()

    def get_edits(self) -> List[EditResult]:
        """
        Parses the LLM response content (containing the patch) into a list of
        tuples, where each tuple contains the file path and the PatchAction object.
        """
        content = self.partial_response_content
        if not content or not content.strip():
            return []

        # Check for patch sentinels
        lines = content.splitlines()
        if (
            len(lines) < 2
            or not _norm(lines[0]).startswith("*** Begin Patch")
            # Allow flexible end, might be EOF or just end of stream
            # or _norm(lines[-1]) != "*** End Patch"
        ):
            # Tolerate missing sentinels if content looks like a patch action
            is_patch_like = any(
                _norm(line).startswith(
                    ("@@", "*** Update File:", "*** Add File:", "*** Delete File:")
                )
                for line in lines
            )
            if not is_patch_like:
                # If it doesn't even look like a patch, return empty
                self.io.tool_warning("Response does not appear to be in patch format.")
                return []
            # If it looks like a patch but lacks sentinels, try parsing anyway but warn.
            self.io.tool_warning(
                "Patch format warning: Missing '*** Begin Patch'/'*** End Patch' sentinels."
            )
            start_index = 0
        else:
            start_index = 1  # Skip "*** Begin Patch"

        # Identify files needed for context lookups during parsing
        needed_paths = identify_files_needed(content)
        current_files: Dict[str, str] = {}
        for rel_path in needed_paths:
            abs_path = self.abs_root_path(rel_path)
            try:
                # Use io.read_text to handle potential errors/encodings
                file_content = self.io.read_text(abs_path)
                if file_content is None:
                    raise DiffError(
                        f"File referenced in patch not found or could not be read: {rel_path}"
                    )
                current_files[rel_path] = file_content
            except FileNotFoundError:
                raise DiffError(f"File referenced in patch not found: {rel_path}")
            except IOError as e:
                raise DiffError(f"Error reading file {rel_path}: {e}")

        try:
            # Parse the patch text using adapted logic
            patch_obj = self._parse_patch_text(lines, start_index, current_files)
            # Convert Patch object actions dict to a list of tuples (path, action)
            # for compatibility with the base Coder's prepare_to_edit method.
            results = []
            for path, action in patch_obj.actions.items():
                results.append((path, action))
            return results
        except DiffError as e:
            # Raise as ValueError for consistency with other coders' error handling
            raise ValueError(f"Error parsing patch content: {e}")
        except Exception as e:
            # Catch unexpected errors during parsing
            raise ValueError(f"Unexpected error parsing patch: {e}")

    def _parse_patch_text(
        self, lines: List[str], start_index: int, current_files: Dict[str, str]
    ) -> Patch:
        """
        Parses patch content lines into a Patch object.
        Adapted from the Parser class in apply_patch.py.
        """
        patch = Patch()
        index = start_index
        fuzz_accumulator = 0

        while index < len(lines):
            line = lines[index]
            norm_line = _norm(line)

            if norm_line == "*** End Patch":
                index += 1
                break  # Successfully reached end

            # ---------- UPDATE ---------- #
            if norm_line.startswith("*** Update File: "):
                path = norm_line[len("*** Update File: ") :].strip()
                index += 1
                if not path:
                    raise DiffError("Update File action missing path.")

                # Optional move target
                move_to = None
                if index < len(lines) and _norm(lines[index]).startswith("*** Move to: "):
                    move_to = _norm(lines[index])[len("*** Move to: ") :].strip()
                    index += 1
                    if not move_to:
                        raise DiffError("Move to action missing path.")

                if path not in current_files:
                    raise DiffError(f"Update File Error - missing file content for: {path}")

                file_content = current_files[path]

                existing_action = patch.actions.get(path)
                if existing_action is not None:
                    # Merge additional UPDATE block into the existing one
                    if existing_action.type != ActionType.UPDATE:
                        raise DiffError(f"Conflicting actions for file: {path}")

                    new_action, index, fuzz = self._parse_update_file_sections(
                        lines, index, file_content
                    )
                    existing_action.chunks.extend(new_action.chunks)

                    if move_to:
                        if existing_action.move_path and existing_action.move_path != move_to:
                            raise DiffError(f"Conflicting move targets for file: {path}")
                        existing_action.move_path = move_to
                    fuzz_accumulator += fuzz
                else:
                    # First UPDATE block for this file
                    action, index, fuzz = self._parse_update_file_sections(
                        lines, index, file_content
                    )
                    action.path = path
                    action.move_path = move_to
                    patch.actions[path] = action
                    fuzz_accumulator += fuzz
                continue

            # ---------- DELETE ---------- #
            elif norm_line.startswith("*** Delete File: "):
                path = norm_line[len("*** Delete File: ") :].strip()
                index += 1
                if not path:
                    raise DiffError("Delete File action missing path.")
                existing_action = patch.actions.get(path)
                if existing_action:
                    if existing_action.type == ActionType.DELETE:
                        # Duplicate delete – ignore the extra block
                        self.io.tool_warning(f"Duplicate delete action for file: {path} ignored.")
                        continue
                    else:
                        raise DiffError(f"Conflicting actions for file: {path}")
                if path not in current_files:
                    raise DiffError(
                        f"Delete File Error - file not found: {path}"
                    )  # Check against known files

                patch.actions[path] = PatchAction(type=ActionType.DELETE, path=path)
                continue

            # ---------- ADD ---------- #
            elif norm_line.startswith("*** Add File: "):
                path = norm_line[len("*** Add File: ") :].strip()
                index += 1
                if not path:
                    raise DiffError("Add File action missing path.")
                if path in patch.actions:
                    raise DiffError(f"Duplicate action for file: {path}")
                # Check if file exists in the context provided (should not for Add).
                # Note: We only have needed files, a full check requires FS access.
                # if path in current_files:
                #     raise DiffError(f"Add File Error - file already exists: {path}")

                action, index = self._parse_add_file_content(lines, index)
                action.path = path  # Ensure path is set
                patch.actions[path] = action
                continue

            # If we are here, the line is unexpected
            # Allow blank lines between actions
            if not norm_line.strip():
                index += 1
                continue

            raise DiffError(f"Unknown or misplaced line while parsing patch: {line}")

        # Check if we consumed the whole input or stopped early
        # Tolerate missing "*** End Patch" if we processed actions
        # if index < len(lines) and _norm(lines[index-1]) != "*** End Patch":
        #    raise DiffError("Patch parsing finished unexpectedly before end of input.")

        patch.fuzz = fuzz_accumulator
        return patch

    def _parse_update_file_sections(
        self, lines: List[str], index: int, file_content: str
    ) -> Tuple[PatchAction, int, int]:
        """Parses all sections (@@, context, -, +) for a single Update File action."""
        action = PatchAction(type=ActionType.UPDATE, path="")  # Path set by caller
        orig_lines = file_content.splitlines()  # Use splitlines for consistency
        current_file_index = 0  # Track position in original file content
        total_fuzz = 0

        while index < len(lines):
            norm_line = _norm(lines[index])
            # Check for terminators for *this* file update
            if norm_line.startswith(
                (
                    "*** End Patch",
                    "*** Update File:",
                    "*** Delete File:",
                    "*** Add File:",
                )
            ):
                break  # End of this file's update section

            # Handle @@ scope lines (optional)
            scope_lines = []
            while index < len(lines) and _norm(lines[index]).startswith("@@"):
                scope_line_content = lines[index][len("@@") :].strip()
                if scope_line_content:  # Ignore empty @@ lines?
                    scope_lines.append(scope_line_content)
                index += 1

            # Find the scope in the original file if specified
            if scope_lines:
                # Simple scope finding: search from current position
                # A more robust finder could handle nested scopes like the reference @@ @@
                found_scope = False
                temp_index = current_file_index
                while temp_index < len(orig_lines):
                    # Check if all scope lines match sequentially from temp_index
                    match = True
                    for i, scope in enumerate(scope_lines):
                        if (
                            temp_index + i >= len(orig_lines)
                            or _norm(orig_lines[temp_index + i]).strip() != scope
                        ):
                            match = False
                            break
                    if match:
                        current_file_index = temp_index + len(scope_lines)
                        found_scope = True
                        break
                    temp_index += 1

                if not found_scope:
                    # Try fuzzy scope matching (strip whitespace)
                    temp_index = current_file_index
                    while temp_index < len(orig_lines):
                        match = True
                        for i, scope in enumerate(scope_lines):
                            if (
                                temp_index + i >= len(orig_lines)
                                or _norm(orig_lines[temp_index + i]).strip() != scope.strip()
                            ):
                                match = False
                                break
                        if match:
                            current_file_index = temp_index + len(scope_lines)
                            found_scope = True
                            total_fuzz += 1  # Add fuzz for scope match difference
                            break
                        temp_index += 1

                if not found_scope:
                    scope_txt = "\n".join(scope_lines)
                    raise DiffError(f"Could not find scope context:\n{scope_txt}")

            # Peek and parse the next context/change section
            context_block, chunks_in_section, next_index, is_eof = peek_next_section(lines, index)

            # Find where this context block appears in the original file
            found_index, fuzz = find_context(orig_lines, context_block, current_file_index, is_eof)
            total_fuzz += fuzz

            if found_index == -1:
                ctx_txt = "\n".join(context_block)
                marker = "*** End of File" if is_eof else ""
                raise DiffError(
                    f"Could not find patch context {marker} starting near line"
                    f" {current_file_index}:\n{ctx_txt}"
                )

            # Adjust chunk original indices to be absolute within the file
            for chunk in chunks_in_section:
                # chunk.orig_index from peek is relative to context_block start
                # We need it relative to the file start
                chunk.orig_index += found_index
                action.chunks.append(chunk)

            # Advance file index past the matched context block
            current_file_index = found_index + len(context_block)
            # Advance line index past the processed section in the patch
            index = next_index

        return action, index, total_fuzz

    def _parse_add_file_content(self, lines: List[str], index: int) -> Tuple[PatchAction, int]:
        """Parses the content (+) lines for an Add File action."""
        added_lines: List[str] = []
        while index < len(lines):
            line = lines[index]
            norm_line = _norm(line)
            # Stop if we hit another action or end marker
            if norm_line.startswith(
                (
                    "*** End Patch",
                    "*** Update File:",
                    "*** Delete File:",
                    "*** Add File:",
                )
            ):
                break

            # Expect lines to start with '+'
            if not line.startswith("+"):
                # Tolerate blank lines? Or require '+'? Reference implies '+' required.
                if norm_line.strip() == "":
                    # Treat blank line as adding a blank line
                    added_lines.append("")
                else:
                    raise DiffError(f"Invalid Add File line (missing '+'): {line}")
            else:
                added_lines.append(line[1:])  # Strip leading '+'

            index += 1

        action = PatchAction(type=ActionType.ADD, path="", new_content="\n".join(added_lines))
        return action, index

    def apply_edits(self, edits: List[PatchAction]):
        """
        Applies the parsed PatchActions to the corresponding files.
        """
        if not edits:
            return

        # Group edits by original path? Not strictly needed if processed sequentially.

        # Edits are now List[Tuple[str, PatchAction]]
        for _path_tuple_element, action in edits:
            # action is the PatchAction object
            # action.path is the canonical path within the action logic
            full_path = self.abs_root_path(action.path)
            path_obj = pathlib.Path(full_path)

            try:
                if action.type == ActionType.ADD:
                    # Check existence *before* writing
                    if path_obj.exists():
                        raise DiffError(f"ADD Error: File already exists: {action.path}")
                    if action.new_content is None:
                        # Parser should ensure this doesn't happen
                        raise DiffError(f"ADD change for {action.path} has no content")

                    self.io.tool_output(f"Adding {action.path}")
                    path_obj.parent.mkdir(parents=True, exist_ok=True)
                    # Ensure single trailing newline, matching reference behavior
                    content_to_write = action.new_content
                    if not content_to_write.endswith("\n"):
                        content_to_write += "\n"
                    self.io.write_text(full_path, content_to_write)

                elif action.type == ActionType.DELETE:
                    self.io.tool_output(f"Deleting {action.path}")
                    if not path_obj.exists():
                        self.io.tool_warning(
                            f"DELETE Warning: File not found, skipping: {action.path}"
                        )
                    else:
                        path_obj.unlink()

                elif action.type == ActionType.UPDATE:
                    if not path_obj.exists():
                        raise DiffError(f"UPDATE Error: File does not exist: {action.path}")

                    current_content = self.io.read_text(full_path)
                    if current_content is None:
                        # Should have been caught during parsing if file was needed
                        raise DiffError(f"Could not read file for UPDATE: {action.path}")

                    # Apply the update logic using the parsed chunks
                    new_content = self._apply_update(current_content, action, action.path)

                    target_full_path = (
                        self.abs_root_path(action.move_path) if action.move_path else full_path
                    )
                    target_path_obj = pathlib.Path(target_full_path)

                    if action.move_path:
                        self.io.tool_output(
                            f"Updating and moving {action.path} to {action.move_path}"
                        )
                        # Check if target exists before overwriting/moving
                        if target_path_obj.exists() and full_path != target_full_path:
                            self.io.tool_warning(
                                "UPDATE Warning: Target file for move already exists, overwriting:"
                                f" {action.move_path}"
                            )
                    else:
                        self.io.tool_output(f"Updating {action.path}")

                    # Ensure parent directory exists for target
                    target_path_obj.parent.mkdir(parents=True, exist_ok=True)
                    self.io.write_text(target_full_path, new_content)

                    # Remove original file *after* successful write to new location if moved
                    if action.move_path and full_path != target_full_path:
                        path_obj.unlink()

                else:
                    # Should not happen
                    raise DiffError(f"Unknown action type encountered: {action.type}")

            except (DiffError, FileNotFoundError, IOError, OSError) as e:
                # Raise a ValueError to signal failure, consistent with other coders.
                raise ValueError(f"Error applying action '{action.type}' to {action.path}: {e}")
            except Exception as e:
                # Catch unexpected errors during application
                raise ValueError(
                    f"Unexpected error applying action '{action.type}' to {action.path}: {e}"
                )

    def _apply_update(self, text: str, action: PatchAction, path: str) -> str:
        """
        Applies UPDATE chunks to the given text content.
        Adapted from _get_updated_file in apply_patch.py.
        """
        if action.type is not ActionType.UPDATE:
            # Should not be called otherwise, but check for safety
            raise DiffError("_apply_update called with non-update action")

        orig_lines = text.splitlines()  # Use splitlines to handle endings consistently
        dest_lines: List[str] = []
        current_orig_line_idx = 0  # Tracks index in orig_lines processed so far

        # Sort chunks by their original index to apply them sequentially
        sorted_chunks = sorted(action.chunks, key=lambda c: c.orig_index)

        for chunk in sorted_chunks:
            # chunk.orig_index is the absolute line number where the change starts
            # (where the first deleted line was, or where inserted lines go if no deletes)
            chunk_start_index = chunk.orig_index

            if chunk_start_index < current_orig_line_idx:
                # This indicates overlapping chunks or incorrect indices from parsing
                raise DiffError(
                    f"{path}: Overlapping or out-of-order chunk detected."
                    f" Current index {current_orig_line_idx}, chunk starts at {chunk_start_index}."
                )

            # Add lines from original file between the last chunk and this one
            dest_lines.extend(orig_lines[current_orig_line_idx:chunk_start_index])

            # Verify that the lines to be deleted actually match the original file content
            # (The parser should have used find_context, but double-check here)
            num_del = len(chunk.del_lines)
            actual_deleted_lines = orig_lines[chunk_start_index : chunk_start_index + num_del]

            # Use the same normalization as find_context_core for comparison robustness
            norm_chunk_del = [_norm(s).strip() for s in chunk.del_lines]
            norm_actual_del = [_norm(s).strip() for s in actual_deleted_lines]

            if norm_chunk_del != norm_actual_del:
                # This indicates the context matching failed or the file changed since parsing
                # Provide detailed error message
                expected_str = "\n".join(f"- {s}" for s in chunk.del_lines)
                actual_str = "\n".join(f"  {s}" for s in actual_deleted_lines)
                raise DiffError(
                    f"{path}: Mismatch applying patch near line {chunk_start_index + 1}.\n"
                    f"Expected lines to remove:\n{expected_str}\n"
                    f"Found lines in file:\n{actual_str}"
                )

            # Add the inserted lines from the chunk
            dest_lines.extend(chunk.ins_lines)

            # Advance the original line index past the lines processed (deleted lines)
            current_orig_line_idx = chunk_start_index + num_del

        # Add any remaining lines from the original file after the last chunk
        dest_lines.extend(orig_lines[current_orig_line_idx:])

        # Join lines and ensure a single trailing newline
        result = "\n".join(dest_lines)
        if result or orig_lines:  # Add newline unless result is empty and original was empty
            result += "\n"
        return result
