import pathlib
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from ..dump import dump  # noqa: F401
from .base_coder import Coder


# Adapted structures and types from apply_patch.py for parsing and applying
class ActionType(str, Enum):
    ADD = "Add"
    DELETE = "Delete"
    UPDATE = "Update"


@dataclass
class Chunk:
    orig_index: int = -1
    del_lines: List[str] = field(default_factory=list)
    ins_lines: List[str] = field(default_factory=list)
    context_before: List[str] = field(
        default_factory=list
    )  # Store context for validation/application


@dataclass
class PatchAction:
    type: ActionType
    path: str
    new_content: Optional[str] = None  # For Add
    chunks: List[Chunk] = field(default_factory=list)  # For Update
    move_path: Optional[str] = None  # For Update


class PatchCoder(Coder):
    """
    A coder that uses a custom patch format for code modifications,
    inspired by the format described in tmp.gpt41edits.txt.
    """

    edit_format = "patch"
    gpt_prompts = None  # Prompts to be added later

    def get_edits(self) -> List[PatchAction]:
        """
        Parses the LLM response content (containing the patch) into a list of PatchAction objects.
        """
        content = self.partial_response_content
        if not content or not content.strip():
            return []

        try:
            parsed_edits = self._parse_patch_content(content)
            return parsed_edits
        except Exception as e:
            raise ValueError(f"Error parsing patch content: {e}")

    def _parse_patch_content(self, content: str) -> List[PatchAction]:
        """
        Parses the patch content string into a list of PatchAction objects.
        This is a simplified parser based on the expected format. A more robust
        implementation would adapt the full parser logic from apply_patch.py,
        including context finding and validation against current file content.
        """
        edits = []
        lines = content.splitlines()
        i = 0
        in_patch = False
        current_action = None

        while i < len(lines):
            line = lines[i]
            i += 1

            if line.strip() == "*** Begin Patch":
                in_patch = True
                continue
            if not in_patch:
                continue
            if line.strip() == "*** End Patch":
                if current_action:
                    edits.append(current_action)
                in_patch = False
                break  # End of patch found

            # Match Action lines (Update, Add, Delete)
            match = re.match(r"\*\*\* (Update|Add|Delete) File: (.*)", line)
            if match:
                if current_action:
                    edits.append(current_action)  # Save previous action

                action_type_str, path = match.groups()
                action_type = ActionType(action_type_str)
                path = path.strip()
                current_action = PatchAction(type=action_type, path=path)

                # Check for optional Move to line immediately after Update
                if action_type == ActionType.UPDATE and i < len(lines):
                    move_match = re.match(r"\*\*\* Move to: (.*)", lines[i])
                    if move_match:
                        current_action.move_path = move_match.group(1).strip()
                        i += 1  # Consume the move line
                continue

            if not current_action:
                # Skip lines before the first action inside the patch
                continue

            # Handle content for Add action
            if current_action.type == ActionType.ADD:
                if current_action.new_content is None:
                    current_action.new_content = ""
                # Assuming ADD content starts immediately and uses '+' prefix
                if line.startswith("+"):
                    current_action.new_content += line[1:] + "\n"
                else:
                    # Or maybe ADD content is just raw lines until next ***?
                    # This part needs clarification based on exact format spec.
                    # Assuming '+' prefix for now. If not, adjust logic.
                    pass  # Ignore lines not starting with '+' in ADD? Or raise error?
                continue

            # Handle chunks for Update action
            if current_action.type == ActionType.UPDATE:
                # This simplified parser doesn't handle @@ context or chunk boundaries well.
                # It assumes a simple sequence of context, '-', '+' lines per chunk.
                # A real implementation needs the state machine from apply_patch.py's
                # peek_next_section.
                # Placeholder: treat consecutive -,+ blocks as single chunk for simplicity.
                if not current_action.chunks:
                    current_action.chunks.append(Chunk())  # Start first chunk

                chunk = current_action.chunks[-1]

                if line.startswith("-"):
                    chunk.del_lines.append(line[1:])
                elif line.startswith("+"):
                    chunk.ins_lines.append(line[1:])
                elif line.startswith("@@"):
                    # Context line - ignored by this simplified parser
                    pass
                elif line.strip() == "*** End of File":
                    # EOF marker - ignored by this simplified parser
                    pass
                else:
                    # Assume it's context line if not +/-/@@
                    # This simplified parser doesn't store context properly.
                    pass
                continue

        if in_patch and not current_action:
            # Started patch but no actions found before end?
            pass  # Or raise error?

        if in_patch and current_action:
            # Reached end of content without *** End Patch
            edits.append(current_action)  # Append the last action
            # Consider raising a warning or error about missing End Patch sentinel

        return edits

    def apply_edits(self, edits: List[PatchAction]):
        """
        Applies the parsed PatchActions to the corresponding files.
        """
        if not edits:
            return

        for action in edits:
            full_path = self.abs_root_path(action.path)
            path_obj = pathlib.Path(full_path)

            try:
                if action.type == ActionType.ADD:
                    if path_obj.exists():
                        # According to apply_patch.py, Add should fail if file exists.
                        # This check should ideally happen during parsing with file content access.
                        raise ValueError(f"ADD Error: File already exists: {action.path}")
                    if action.new_content is None:
                        raise ValueError(f"ADD change for {action.path} has no content")
                    # Ensure parent directory exists
                    path_obj.parent.mkdir(parents=True, exist_ok=True)
                    self.io.write_text(
                        full_path, action.new_content.rstrip("\n") + "\n"
                    )  # Ensure single trailing newline

                elif action.type == ActionType.DELETE:
                    if not path_obj.exists():
                        # Allow deleting non-existent files (idempotent)
                        pass
                    else:
                        path_obj.unlink()

                elif action.type == ActionType.UPDATE:
                    if not path_obj.exists():
                        # Update should fail if file doesn't exist
                        # (checked in apply_patch.py parser).
                        raise ValueError(f"UPDATE Error: File does not exist: {action.path}")

                    current_content = self.io.read_text(full_path)
                    if current_content is None:
                        raise ValueError(f"Could not read file for UPDATE: {action.path}")

                    # Apply the update logic using the parsed chunks
                    new_content = self._apply_update(current_content, action.chunks, action.path)

                    target_full_path = (
                        self.abs_root_path(action.move_path) if action.move_path else full_path
                    )
                    target_path_obj = pathlib.Path(target_full_path)

                    # Ensure parent directory exists for target
                    target_path_obj.parent.mkdir(parents=True, exist_ok=True)
                    self.io.write_text(target_full_path, new_content)

                    if action.move_path and full_path != target_full_path:
                        # Remove original file after successful write to new location
                        path_obj.unlink()

                else:
                    raise ValueError(f"Unknown action type encountered: {action.type}")

            except Exception as e:
                # Raise a ValueError to signal failure, consistent with other coders.
                raise ValueError(f"Error applying action '{action.type}' to {action.path}: {e}")

    def _apply_update(self, text: str, chunks: List[Chunk], path: str) -> str:
        """
        Applies UPDATE chunks to the given text content.
        Requires accurate chunk information (indices, lines) from a robust parser.
        This simplified version assumes chunks are sequential and indices are correct.
        """
        if not chunks:
            return text  # No changes specified

        orig_lines = text.splitlines()  # Use splitlines() to match apply_patch.py behavior
        dest_lines = []
        # last_orig_line_idx = -1 # Track the end of the last applied chunk in original lines

        # apply_patch.py finds context during parsing. Here we assume indices are pre-validated.
        # A robust implementation would re-validate context here or rely entirely on parser
        # validation.

        # Sort chunks? apply_patch.py implies they are processed in order found in patch.
        # Chunks need accurate `orig_index` relative to the start of their *context* block.
        # This simplified implementation lacks proper context handling and index calculation.
        # It assumes `orig_index` is the absolute line number from start of file, which is incorrect
        # based on apply_patch.py.
        # --> THIS METHOD NEEDS REWRITING BASED ON A CORRECT PARSER <--
        # For demonstration, let's process sequentially, assuming indices are somewhat meaningful.

        current_orig_line_num = 0
        for chunk in chunks:
            # Placeholder: Assume chunk application logic here.
            # This needs the sophisticated context matching and index handling from apply_patch.py.
            # The current simplified parser doesn't provide enough info (like validated indices).
            # Raising NotImplementedError until a proper parser/applier is integrated.
            raise NotImplementedError(
                "_apply_update requires a robust parser and context handling, similar to"
                " apply_patch.py"
            )

            # --- Hypothetical logic assuming correct indices ---
            # chunk_start_index = chunk.orig_index # Needs correct calculation based on context
            # if chunk_start_index < current_orig_line_num:
            #     raise ValueError(f"{path}: Overlapping or out-of-order chunk detected.")
            #
            # # Add lines between the last chunk and this one
            # dest_lines.extend(orig_lines[current_orig_line_num:chunk_start_index])
            #
            # # Verify deleted lines match (requires normalization)
            # num_del = len(chunk.del_lines)
            # actual_deleted = orig_lines[chunk_start_index : chunk_start_index + num_del]
            # # if normalized(actual_deleted) != normalized(chunk.del_lines):
            # #    raise ValueError(
            # #        f"{path}: Mismatch in deleted lines for chunk at index {chunk_start_index}"
            # #    )
            #
            # # Add inserted lines
            # dest_lines.extend(chunk.ins_lines)
            #
            # # Advance index past the deleted lines
            # current_orig_line_num = chunk_start_index + num_del
            # --- End Hypothetical ---

        # Add remaining lines after the last chunk
        dest_lines.extend(orig_lines[current_orig_line_num:])

        return "\n".join(dest_lines) + "\n"  # Ensure trailing newline
