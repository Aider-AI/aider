# At the top of the file, add necessary imports
import itertools
import pathlib
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

# Keep existing imports like dump, Coder, PatchPrompts, DiffError, ActionType
from ..dump import dump  # noqa: F401
from .base_coder import Coder

# Import do_replace from editblock_coder
from .editblock_coder import do_replace
from .patch_prompts import PatchPrompts

# Remove original PatchCoder domain objects and helpers if they exist at the top.
# We will redefine or replace these as needed.


# --------------------------------------------------------------------------- #
#  Domain objects & Exceptions (Adapted for Flex Coder)
# --------------------------------------------------------------------------- #
class DiffError(ValueError):
    """Any problem detected while parsing or applying a patch."""


class ActionType(str, Enum):
    ADD = "Add"
    DELETE = "Delete"
    UPDATE = "Update"


@dataclass
class ParsedEdit:
    """Represents a single parsed action or change hunk."""

    path: str
    type: ActionType
    # For UPDATE hunks:
    search_text: Optional[str] = None
    replace_text: Optional[str] = None
    # For ADD:
    new_content: Optional[str] = None
    # For UPDATE (last hunk wins if multiple):
    move_path: Optional[str] = None
    # Original line number in the patch file where this hunk started (for error reporting)
    patch_line_num: int = 0


# --------------------------------------------------------------------------- #
#  Helper functions (Adapted for Flex Coder)
# --------------------------------------------------------------------------- #
def _norm(line: str) -> str:
    """Strip CR so comparisons work for both LF and CRLF input."""
    return line.rstrip("\r")


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


def _peek_change_hunk(
    lines: List[str], index: int
) -> Tuple[List[str], List[str], List[str], List[str], int, bool]:
    """
    Parses one change hunk (context-before, deleted, inserted, context-after)
    from an Update block.

    Returns: (context_before, del_lines, ins_lines, context_after, next_index, is_eof)
    """
    context_before: List[str] = []
    del_lines: List[str] = []
    ins_lines: List[str] = []
    context_after: List[str] = []

    mode = "context_before"  # States: context_before, delete, insert, context_after
    start_index = index

    while index < len(lines):
        line = lines[index]
        norm_line = _norm(line)

        # Check for section terminators
        if norm_line.startswith(
            (
                "@@",  # Start of a new scope/hunk marker
                "*** End Patch",
                "*** Update File:",
                "*** Delete File:",
                "*** Add File:",
                "*** End of File",
            )
        ):
            break
        if norm_line == "***":
            break
        if norm_line.startswith("***"):
            raise DiffError(f"Invalid patch line found in update section: {line}")

        current_line_index = index
        index += 1

        # Determine line type and content
        line_type = "unknown"
        line_content = ""
        if line.startswith("+"):
            line_type = "insert"
            line_content = line[1:]
        elif line.startswith("-"):
            line_type = "delete"
            line_content = line[1:]
        elif line.startswith(" "):
            line_type = "context"
            line_content = line[1:]
        elif line.strip() == "":
            line_type = "context"
            line_content = ""
        else:
            raise DiffError(f"Invalid line prefix in update section: {line}")

        # State machine logic
        if mode == "context_before":
            if line_type == "context":
                context_before.append(line_content)
            elif line_type == "delete":
                del_lines.append(line_content)
                mode = "delete"
            elif line_type == "insert":
                # Change starts with insertion (no deletion)
                ins_lines.append(line_content)
                mode = "insert"
            else:
                # Should not happen based on checks above
                raise DiffError(f"Unexpected line type '{line_type}' in mode '{mode}': {line}")

        elif mode == "delete":
            if line_type == "delete":
                del_lines.append(line_content)
            elif line_type == "insert":
                ins_lines.append(line_content)
                mode = "insert"
            elif line_type == "context":
                # Deletes finished, context after starts
                context_after.append(line_content)
                mode = "context_after"
            else:
                raise DiffError(f"Unexpected line type '{line_type}' in mode '{mode}': {line}")

        elif mode == "insert":
            if line_type == "insert":
                ins_lines.append(line_content)
            elif line_type == "context":
                # Inserts finished, context after starts
                context_after.append(line_content)
                mode = "context_after"
            elif line_type == "delete":
                # Interleaved +/- lines are not handled well by this simplified parser.
                # Treat as end of hunk for now.
                index = current_line_index  # Put the delete line back for the next hunk
                break
            else:
                raise DiffError(f"Unexpected line type '{line_type}' in mode '{mode}': {line}")

        elif mode == "context_after":
            if line_type == "context":
                context_after.append(line_content)
            else:
                # Any non-context line means this hunk's context_after is finished.
                # Put the line back for the next hunk/parser step.
                index = current_line_index
                break

    # Check for EOF marker
    is_eof = False
    if index < len(lines) and _norm(lines[index]) == "*** End of File":
        index += 1
        is_eof = True

    if index == start_index and not is_eof:
        raise DiffError("Empty patch section found.")

    # If the hunk ended immediately with context_after, the last context line
    # might belong to the *next* hunk's context_before. This is tricky.
    # For simplicity, we'll keep it here. flexible_search_replace might handle overlap.

    return context_before, del_lines, ins_lines, context_after, index, is_eof


# --------------------------------------------------------------------------- #
#  PatchFlexCoder Class Implementation
# --------------------------------------------------------------------------- #
class PatchFlexCoder(Coder):  # Rename class
    """
    A coder that uses the patch format for LLM output, but applies changes
    using flexible search-and-replace logic for UPDATE actions, ignoring @@ hints
    and precise line numbers during application.
    """

    edit_format = "patch-flex"  # Give it a distinct name
    gpt_prompts = PatchPrompts()  # Use the same prompts as PatchCoder

    def get_edits(self) -> List[Tuple[Optional[str], ParsedEdit]]:  # Return type changed
        """
        Parses the LLM response content (containing the patch) into a list of
        ParsedEdit objects, extracting search/replace blocks for UPDATEs.
        """
        content = self.partial_response_content
        if not content or not content.strip():
            return []

        lines = content.splitlines()
        start_index = 0
        if len(lines) >= 2 and _norm(lines[0]).startswith("*** Begin Patch"):
            start_index = 1
        else:
            # Tolerate missing sentinels if content looks like a patch action
            is_patch_like = any(
                _norm(line).startswith(
                    ("@@", "*** Update File:", "*** Add File:", "*** Delete File:")
                )
                for line in lines
            )
            if not is_patch_like:
                self.io.tool_warning("Response does not appear to be in patch format.")
                return []
            self.io.tool_warning("Patch format warning: Missing '*** Begin Patch' sentinel.")

        # Identify files needed for context lookups (only for DELETE check)
        needed_paths = identify_files_needed(content)
        # Unlike PatchCoder, we don't strictly need file content during parsing,
        # but it's useful to check if DELETE targets exist.
        # We read content dynamically in apply_edits.
        known_files = set(self.get_inchat_relative_files()) | set(needed_paths)

        try:
            # Parse the patch text into ParsedEdit objects
            parsed_edits = self._parse_patch_text(lines, start_index, known_files)
            return parsed_edits
        except DiffError as e:
            raise ValueError(f"Error parsing patch content: {e}")
        except Exception as e:
            raise ValueError(f"Unexpected error parsing patch: {e}")

    def _parse_patch_text(
        self, lines: List[str], start_index: int, known_files: set[str]
    ) -> List[Tuple[Optional[str], ParsedEdit]]: # Return type changed
        """
        Parses patch content lines into a list of ParsedEdit objects.
        """
        parsed_edits: List[Tuple[Optional[str], ParsedEdit]] = [] # List type changed
        index = start_index
        current_file_path = None
        current_move_path = None

        while index < len(lines):
            line = lines[index]
            norm_line = _norm(line)
            line_num = index + 1  # 1-based for reporting

            if norm_line == "*** End Patch":
                index += 1
                break

            # ---------- UPDATE ---------- #
            if norm_line.startswith("*** Update File: "):
                path = norm_line[len("*** Update File: ") :].strip()
                index += 1
                if not path:
                    raise DiffError(f"Update File action missing path (line {line_num}).")
                # Don't check for duplicates; multiple UPDATEs for the same file
                # are processed sequentially.
                # if path not in known_files:
                #     self.io.tool_warning(f"Update target '{path}' not in chat context.")

                current_file_path = path
                current_move_path = None  # Reset move path for new file

                # Check for optional Move to immediately after
                if index < len(lines) and _norm(lines[index]).startswith("*** Move to: "):
                    move_to = _norm(lines[index])[len("*** Move to: ") :].strip()
                    index += 1
                    if not move_to:
                        raise DiffError(f"Move to action missing path (line {index}).")
                    current_move_path = move_to
                continue  # Continue to parse hunks for this file

            # ---------- DELETE ---------- #
            elif norm_line.startswith("*** Delete File: "):
                path = norm_line[len("*** Delete File: ") :].strip()
                index += 1
                if not path:
                    raise DiffError(f"Delete File action missing path (line {line_num}).")
                if path not in known_files:
                    # Check against known files before adding delete action
                    self.io.tool_warning(f"Delete File target '{path}' not found in chat context.")

                parsed_edits.append(
                    (path, ParsedEdit(path=path, type=ActionType.DELETE, patch_line_num=line_num)) # Wrap in tuple
                )
                current_file_path = None  # Reset current file context
                current_move_path = None
                continue

            # ---------- ADD ---------- #
            elif norm_line.startswith("*** Add File: "):
                path = norm_line[len("*** Add File: ") :].strip()
                index += 1
                if not path:
                    raise DiffError(f"Add File action missing path (line {line_num}).")
                # if path in known_files: # Check if file might already exist
                #     self.io.tool_warning(f"Add File target '{path}' may already exist.")

                action, index = self._parse_add_file_content(lines, index)
                action.path = path
                action.patch_line_num = line_num
                parsed_edits.append((path, action)) # Wrap in tuple
                current_file_path = None  # Reset current file context
                current_move_path = None
                continue

            # ---------- Hunks within UPDATE ---------- #
            elif current_file_path:
                # Skip @@ lines, they are ignored by this coder's application logic
                if norm_line.startswith("@@"):
                    index += 1
                    continue

                # Parse the next change hunk for the current file
                hunk_start_index = index
                try:
                    (
                        context_before,
                        del_lines,
                        ins_lines,
                        context_after,
                        next_index,
                        _is_eof,  # EOF marker not strictly needed for search/replace logic
                    ) = _peek_change_hunk(lines, index)
                except DiffError as e:
                    raise DiffError(f"{e} (near line {line_num} in patch)")

                if not del_lines and not ins_lines:
                    # Skip hunks that contain only context - they don't represent a change
                    index = next_index
                    continue

                # Construct search and replace text based on user request
                # Search = context_before + deleted_lines
                # Replace = inserted_lines + context_after
                search_text = "\n".join(context_before + del_lines)
                replace_text = "\n".join(ins_lines + context_after)

                # Add trailing newline if original content likely had one
                # (This helps match blocks ending at EOF)
                # Heuristic: if context_after is empty AND there were deleted lines,
                # the original block likely ended with the last deleted line.
                # Or if context_before/del/ins are all empty, it's just context.
                if not context_after and (del_lines or ins_lines):
                    search_text += "\n"
                    # Replace text already includes context_after, so only add if that was empty too
                    if not ins_lines:
                        replace_text += "\n"
                elif context_after or context_before or del_lines or ins_lines:
                    # If there's any content, ensure trailing newline for consistency
                    search_text += "\n"
                    replace_text += "\n"

                parsed_edits.append(
                    (current_file_path, # Add path to tuple
                     ParsedEdit(
                        path=current_file_path,
                        type=ActionType.UPDATE,
                        search_text=search_text,
                        replace_text=replace_text,
                        move_path=current_move_path,  # Carry over move path for this hunk
                        patch_line_num=hunk_start_index + 1,
                    ))
                )
                index = next_index
                continue

            # If we are here, the line is unexpected or misplaced
            if not norm_line.strip():  # Allow blank lines between actions/files
                index += 1
                continue

            raise DiffError(
                f"Unknown or misplaced line while parsing patch (line {line_num}): {line}"
            )

        return parsed_edits

    def _parse_add_file_content(self, lines: List[str], index: int) -> Tuple[ParsedEdit, int]:
        """Parses the content (+) lines for an Add File action."""
        added_lines: List[str] = []
        start_line_num = index + 1
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

            if not line.startswith("+"):
                if norm_line.strip() == "":
                    added_lines.append("")  # Treat blank line as adding a blank line
                else:
                    raise DiffError(
                        f"Invalid Add File line (missing '+') (line {index + 1}): {line}"
                    )
            else:
                added_lines.append(line[1:])

            index += 1

        action = ParsedEdit(
            path="",  # Path set by caller
            type=ActionType.ADD,
            new_content="\n".join(added_lines),
            patch_line_num=start_line_num,
        )
        return action, index

    def apply_edits(self, edits: List[Tuple[Optional[str], ParsedEdit]]): # Argument type changed
        """
        Applies the parsed edits. Uses flexible search-and-replace for UPDATEs.
        """
        if not edits:
            self.io.tool_output("No edits to apply.")
            return

        # Group edits by file path to process them sequentially
        edits_by_path = itertools.groupby(edits, key=lambda edit: edit[0]) # Group by path in tuple

        for path, path_edits_iter in edits_by_path:
            path_edits = list(path_edits_iter) # path_edits is now a list of tuples
            full_path = self.abs_root_path(path)
            path_obj = pathlib.Path(full_path)
            current_content = None
            edit_failed = False
            final_move_path = None  # Track the last move destination for this file

            # Check for simple ADD/DELETE first (should ideally be only one per file)
            if len(path_edits) == 1 and path_edits[0][1].type in [ActionType.ADD, ActionType.DELETE]:
                _path, edit = path_edits[0] # Unpack tuple
                try:
                    if edit.type == ActionType.ADD:
                        if path_obj.exists():
                            # Allow overwrite on ADD? Or error? Let's warn and overwrite.
                            self.io.tool_warning(
                                f"ADD Warning: File '{path}' already exists, overwriting."
                            )
                            # raise DiffError(f"ADD Error: File already exists: {path}")
                        if edit.new_content is None:
                            raise DiffError(f"ADD change for {path} has no content")

                        self.io.tool_output(f"Adding {path}")
                        path_obj.parent.mkdir(parents=True, exist_ok=True)
                        content_to_write = edit.new_content
                        if not content_to_write.endswith("\n"):
                            content_to_write += "\n"
                        self.io.write_text(full_path, content_to_write)

                    elif edit.type == ActionType.DELETE:
                        self.io.tool_output(f"Deleting {path}")
                        if not path_obj.exists():
                            self.io.tool_warning(
                                f"DELETE Warning: File not found, skipping: {path}"
                            )
                        else:
                            path_obj.unlink()
                except (DiffError, FileNotFoundError, IOError, OSError) as e:
                    raise ValueError(f"Error applying action '{edit.type}' to {path}: {e}")
                except Exception as e:
                    raise ValueError(
                        f"Unexpected error applying action '{edit.type}' to {path}: {e}"
                    )
                continue  # Move to the next file path

            # --- Handle UPDATE actions sequentially ---
            self.io.tool_output(f"Updating {path}...")
            try:
                if not path_obj.exists():
                    raise DiffError(f"UPDATE Error: File does not exist: {path}")
                current_content = self.io.read_text(full_path)
                if current_content is None:
                    raise DiffError(f"Could not read file for UPDATE: {path}")

                for i, item in enumerate(path_edits): # Iterate through items (tuples)
                    _path, edit = item # Unpack tuple
                    if edit.type != ActionType.UPDATE:
                        raise DiffError(
                            f"Unexpected action type '{edit.type}' mixed with UPDATE for {path}"
                        )
                    if edit.search_text is None or edit.replace_text is None:
                        raise DiffError(f"UPDATE action for {path} is missing search/replace text")

                    final_move_path = edit.move_path  # Last move path specified wins

                    self.io.tool_output(
                        f"  Applying hunk {i + 1} (from patch line {edit.patch_line_num})..."
                    )

                    # Replace the call to flexible_search_and_replace with do_replace
                    new_content = do_replace(
                        full_path,  # Pass the full path as fname
                        current_content,
                        edit.search_text,
                        edit.replace_text,
                        self.fence,  # Use the coder's fence attribute
                    )

                    if new_content is None:
                        edit_failed = True
                        # Provide more context on failure
                        err_msg = (
                            f"Failed to apply update hunk {i + 1} (from patch line"
                            f" {edit.patch_line_num}) for file {path}. The search block may not"
                            " have been found or the change conflicted.\nSearch"
                            f" block:\n```\n{edit.search_text}```\nReplace"
                            f" block:\n```\n{edit.replace_text}```"
                        )
                        # Raise immediately to stop processing this file
                        raise ValueError(err_msg)

                    # Update content for the next iteration
                    current_content = new_content

                # After processing all hunks for this file:
                if not edit_failed and current_content is not None:
                    target_full_path = (
                        self.abs_root_path(final_move_path) if final_move_path else full_path
                    )
                    target_path_obj = pathlib.Path(target_full_path)

                    if final_move_path:
                        self.io.tool_output(f"Moving updated file to {final_move_path}")
                        if target_path_obj.exists() and full_path != target_full_path:
                            self.io.tool_warning(
                                "UPDATE Warning: Target file for move already exists, overwriting:"
                                f" {final_move_path}"
                            )

                    # Ensure parent directory exists for target
                    target_path_obj.parent.mkdir(parents=True, exist_ok=True)
                    # Ensure trailing newline
                    if not current_content.endswith("\n") and current_content != "":
                        current_content += "\n"
                    self.io.write_text(target_full_path, current_content)

                    # Remove original file *after* successful write if moved
                    if final_move_path and full_path != target_full_path:
                        path_obj.unlink()

            except (DiffError, FileNotFoundError, IOError, OSError) as e:
                # Raise a ValueError to signal failure
                raise ValueError(f"Error applying UPDATE to {path}: {e}")
            except Exception as e:
                # Catch unexpected errors during application
                raise ValueError(f"Unexpected error applying UPDATE to {path}: {e}")

    # Remove the _apply_update method as it's replaced by flexible_search_and_replace logic
    # def _apply_update(self, text: str, action: PatchAction, path: str) -> str:
    #    ...
