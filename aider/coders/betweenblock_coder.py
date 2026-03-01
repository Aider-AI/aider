# flake8: noqa: E501
import os
import re
from dataclasses import dataclass, field, fields
from pathlib import Path

from aider.utils import format_content, format_messages
from aider.waiting import WaitingSpinner

from .base_coder import Coder
from .betweenblock_prompts import BetweenBlockPrompts

missing_filename_err = "No filename provided before {fence[0]} in file listing."

no_tag_err = "Always begin each code block with one of the following tags: {allowed_tags_list}."

invalid_tag_err = (
    "Tag {tag} is unknown. Use only the following tags to define location of code to change:"
    " {allowed_tags_list}."
)

bad_between_tag_err = """Always write @BETWEEN@ line in following format:
@BETWEEN@ "[existing line]" AND "[existing line]\""""

allowed_tags = ["@BETWEEN@", "@WHOLE FILE@"]
new_file_tags = {"@WHOLE FILE@"}

file_not_found_err = (
    "File {fname} does not exists. Check file name and path if you editing an existing file. Or if"
    " you want to create a new file use @WHOLE FILE@ tag."
)

existing_line_not_found_err = """Line "{not_found_line}" does not exist in the file "{fname}".
Every [existing line] in tags must *EXACTLY MATCH* to one of the lines in the file, character for character, including all spaces.
Also this error may be caused by a confused file name in beginning of the code block. In this case, write down the correct file path where the changes should be made."""

lines_not_unique_err = (
    'Lines "{lines[0]}" and "{lines[1]}" occurs in file {fname} more than once. Rewrite the code'
    " block with @BETWEEN@ line using more unique existing lines."
)

range_too_bin_err = """Chunk between "{lines[0]}" and "{lines[1]}" is too big. You must keep locations where changes should be made concise.
Point more precise location in @BETWEEN@ line.
Or, if needed, split the code block into several parts."""

bad_merge_response_err = """Output only the updated code, enclosed within <updated-code> and </updated-code> tags.
Updated code must be enclosed in <updated-code> and </updated-code>!
Just reply with fixed version of updated code within <updated-code> and </updated-code> tags."""

merge_model_failed_err = (
    "Less intelligent model failed to merge the code block. Rewrite it so that model can understand"
    " the code block."
)

merge_not_between_err = """Merge the <update> snippet between lines "{lines[0]}" and "{lines[1]}", not at end!
Do not change other lines in <code> block!
Just reply with fixed version of updated code within <updated-code> and </updated-code> tags."""

cannot_insert_between_err = """This code cannot be inserted between lines "{lines[0]}" and "{lines[1]}".
Be very precise when pointing lines between which the changes need to be made."""


@dataclass
class LocationTag:
    tag: str = field()
    tag_line: str = field()
    is_bad: bool = field(default=False, kw_only=True)


@dataclass
class BetweenTag(LocationTag):
    lines: tuple[str, str] = field()


@dataclass
class BetweenCoderEdit:
    path: str = field()
    tag: LocationTag = field()
    snippet: str = field()

    def __getitem__(self, key):
        "Wrapper for tuple interface used by other coders"
        return getattr(self, fields(self)[key].name)


class BetweenBlockCoder(Coder):
    """A coder that uses snippets with @BETWEEN@ tags for code modifications."""

    edit_format = "between"
    gpt_prompts = BetweenBlockPrompts()

    tag_pattern = re.compile(r"^\s*(@[A-Z0-9\s_-]+@)(.*)$")
    between_args_pattern = re.compile(r'^\s+"(.+?)"?\s+AND\s+"(.+?)(:?"\s*)?$')

    def get_edits(self, mode="update"):
        chat_files = self.get_inchat_relative_files()
        content = self.get_multi_response_content_in_progress()
        lines = content.splitlines(keepends=True)

        edits = list()

        in_code_block = False
        block_filename = None
        loc_tag = None
        new_lines = []

        def add_edit():
            nonlocal block_filename, loc_tag, new_lines
            if len(new_lines) > 0:
                if (
                    loc_tag.tag not in new_file_tags
                    and not Path(self.abs_root_path(block_filename)).exists()
                ):
                    raise ValueError(file_not_found_err.format(fname=block_filename))
                edits.append(BetweenCoderEdit(block_filename, loc_tag, "".join(new_lines)))
            loc_tag = None
            new_lines = []

        for i, line in enumerate(lines):
            if line.startswith(self.fence[0]) or line.startswith(self.fence[1]):
                if not in_code_block:
                    # opening fence
                    in_code_block = True
                    block_filename = None
                    new_lines = []
                    if i > 0:
                        fname = lines[i - 1].strip()
                        fname = fname.strip("*")  # handle **filename.py**
                        fname = fname.rstrip(":")
                        fname = fname.strip("`")
                        fname = fname.lstrip("#")
                        fname = fname.strip()
                        if len(fname) > 250:
                            fname = ""
                        if fname and fname not in chat_files and Path(fname).name in chat_files:
                            fname = Path(fname).name
                        block_filename = fname
                    if not block_filename:
                        raise ValueError(missing_filename_err.format(fence=self.fence))
                else:
                    # closing fence
                    add_edit()
                    in_code_block = False
                    block_filename = None
            elif in_code_block:
                tag_match = self.tag_pattern.match(line)
                if tag_match:
                    if loc_tag:
                        # multiple tags in one Markdown code block
                        if len(new_lines) > 0 and not new_lines[-1].strip():
                            # removing empty line before tag from previous snippet
                            new_lines.pop()
                        add_edit()
                    tag = tag_match[1]
                    tag_args = tag_match[2]
                    if tag == "@BETWEEN@":
                        args_match = self.between_args_pattern.match(tag_args)
                        if not args_match:
                            loc_tag = LocationTag(tag, line, is_bad=True)
                        else:
                            loc_tag = BetweenTag(tag, line, (args_match[1], args_match[2]))
                    else:
                        loc_tag = LocationTag(tag, line)
                    # else:
                    #    raise ValueError()
                else:
                    if not loc_tag:  # if there is no tag at beginning of code block
                        if line.strip():  # and this line not empty
                            raise ValueError(
                                no_tag_err.format(allowed_tags_list=", ".join(allowed_tags))
                            )
                    new_lines.append(line)
        if in_code_block:
            add_edit()
        return edits

    existing_line_space_pattern = re.compile(r"\s+")
    escaped_doublequotes_pattern = re.compile(r'\\"')
    any_doublequotes_pattern = re.compile(r'"')

    def normalize_existing_line(self, line):
        l = line.strip()
        l = self.existing_line_space_pattern.sub(" ", l)

        # llm may escape double quotes as line in tag is already quoted
        while self.escaped_doublequotes_pattern.search(l):
            l = self.escaped_doublequotes_pattern.sub('"', l)
        # in strings like "\"text\"" llm can loss duplicating \" when escaping
        # also it can lose first or last double quote
        l = l.replace('"', "")
        return l

    def find_existing_line(self, content_lines, existing_line: str):
        existing_line = self.normalize_existing_line(existing_line)
        possible_idx = list()
        for i, line in enumerate(content_lines):
            if self.normalize_existing_line(line) == existing_line:
                possible_idx.append(i)

        if not possible_idx and len(existing_line) > 2:
            for i, line in enumerate(content_lines):
                norm_line = self.normalize_existing_line(line)
                idx = norm_line.find(existing_line)
                if (
                    idx != -1
                    # allow omitting start of comment delimiter and other similar prefixes
                    and idx <= 3
                ):
                    possible_idx.append(i)

                if i < len(content_lines) - 1:
                    idx = existing_line.find(norm_line)
                    if idx == 0:
                        next_norm_line = self.normalize_existing_line(content_lines[i + 1])
                        if not next_norm_line and i < len(content_lines) - 2:
                            next_norm_line = self.normalize_existing_line(content_lines[i + 2])
                        idx2 = existing_line.rfind(next_norm_line)
                        if len(norm_line) <= idx2 < len(norm_line) + 3:
                            possible_idx.append(i)

        return possible_idx

    def apply_between_edit(self, content_lines, edit, spinner_text):
        lines_pos = [self.find_existing_line(content_lines, l) for l in edit.tag.lines]
        if any(len(line_pos) == 0 for line_pos in lines_pos):
            not_found_line = edit.tag.lines[0 if len(lines_pos[0]) == 0 else 1]
            return (
                False,
                None,
                existing_line_not_found_err.format(not_found_line=not_found_line, fname=edit.path),
            )
        if all(len(line_pos) == 1 for line_pos in lines_pos):
            edit_range = [line_pos[0] for line_pos in lines_pos]
            edit_range.sort()
        elif len(lines_pos[0]) == 1:
            # first existing line is unique, while second occurs multiple times
            try:
                edit_range = [
                    lines_pos[0][0],
                    next(pos for pos in lines_pos[1] if pos > lines_pos[0][0]),
                ]
            except StopIteration:
                return (
                    False,
                    None,
                    existing_line_not_found_err.format(
                        not_found_line=edit.tag.lines[1], fname=edit.path
                    ),
                )
        elif len(lines_pos[1]) == 1:
            try:
                edit_range = [
                    next(pos for pos in reversed(lines_pos[0]) if pos < lines_pos[1][0]),
                    lines_pos[1][0],
                ]
            except StopIteration:
                return (
                    False,
                    None,
                    existing_line_not_found_err.format(
                        not_found_line=edit.tag.lines[0], fname=edit.path
                    ),
                )
        elif lines_pos[0] == lines_pos[1] and len(lines_pos[0]) == 2:
            # the model suggest to edit code between two identical lines and
            # there is exactly two such line in the file
            edit_range = [lines_pos[0][0], lines_pos[1][1]]
        else:
            if lines_pos[0][-1] < lines_pos[1][0]:
                # all ocurances of the first line are located before first occurrence of
                # the second line. So there is only one possible range that does not include
                # other occurrences in between
                edit_range = [lines_pos[0][-1], lines_pos[1][0]]
            else:
                return (
                    False,
                    None,
                    lines_not_unique_err.format(lines=edit.tag.lines, fname=edit.path),
                )

        if edit_range[1] - edit_range[0] > 500:
            return False, None, range_too_bin_err.format(lines=edit.tag.lines)

        content_lines_cnt = len(content_lines)
        assert edit_range[0] <= edit_range[1]
        edit_range[0] = max(edit_range[0] - 3, 0)
        edit_range[1] = min(edit_range[1] + 3, content_lines_cnt - 1)

        # first and last line must be non-empty
        while edit_range[0] > 0 and not content_lines[edit_range[0]].strip():
            edit_range[0] -= 1
        while edit_range[1] < content_lines_cnt - 1 and not content_lines[edit_range[1]].strip():
            edit_range[1] += 1

        edit_range[1] += 1

        placeholder_lines_at_begin = 0
        placeholder_lines_at_end = 0

        original_lines = list(content_lines[edit_range[0] : edit_range[1]])
        if edit_range[0] > 0:
            original_lines.insert(0, "\n")
            original_lines.insert(
                0,
                self.gpt_prompts.skipped_lines_placeholder.format(lines_count=edit_range[0]) + "\n",
            )
            placeholder_lines_at_begin += 2
        if edit_range[1] < content_lines_cnt:
            if original_lines[-1][-1] != "\n":
                original_lines[-1] = original_lines[-1] + "\n"
            original_lines.append("\n")
            original_lines.append(
                self.gpt_prompts.skipped_lines_placeholder.format(
                    lines_count=content_lines_cnt - edit_range[1]
                )
                + "\n"
            )
            placeholder_lines_at_end += 2

        merge_model = self.main_model.merge_model or self.main_model.weak_model or self.main_model

        if merge_model.system_prompt_prefix:
            merge_system_content = (
                merge_model.system_prompt_prefix + "\n" + self.gpt_prompts.merge_system_message
            )
        else:
            merge_system_content = self.gpt_prompts.merge_system_message

        merge_prompt = self.gpt_prompts.merge_prompt.format(
            existing_code="".join(original_lines),
            merge_request=self.gpt_prompts.merge_between_request.format(lines=edit.tag.lines),
            update_snippet=edit.snippet,
        )

        messages = [
            dict(role="system", content=merge_system_content),
            dict(role="user", content=merge_prompt),
        ]
        merge_result_pattern = re.compile(
            self.gpt_prompts.merge_result_regexp, re.MULTILINE | re.DOTALL
        )
        merge_no_changes_pattern = re.compile(
            self.gpt_prompts.merge_no_changes_regexp, re.MULTILINE | re.DOTALL
        )

        main_model_error = None

        for tryIdx in range(2):
            self.io.log_llm_history("TO LLM (MERGE)", format_messages(messages))
            if tryIdx != 0:
                spinner_text = spinner_text + f" (retry {tryIdx})"
            with WaitingSpinner(spinner_text):
                updated_responce = merge_model.simple_send_with_retries(
                    messages, temperature=merge_model.merge_temperature
                )
            self.io.log_llm_history(
                "LLM RESPONSE (MERGE)", format_content("ASSISTANT", updated_responce)
            )

            retry_prompt = None  # error message to merge model
            main_model_error = None  # error message for main model if merge model failed again

            updated_match = merge_result_pattern.match(updated_responce)
            if updated_match:
                updated = updated_match[1]
                updated_lines = updated.splitlines(keepends=True)

                is_wrong_insertion = False
                if edit_range[0] != 0:
                    if (
                        updated_lines[: placeholder_lines_at_begin + 1]
                        != original_lines[: placeholder_lines_at_begin + 1]
                    ):
                        for skipped_placeholder_lines in range(1, placeholder_lines_at_begin + 1):
                            if (
                                updated_lines[
                                    : (placeholder_lines_at_begin - skipped_placeholder_lines) + 2
                                ]
                                == original_lines[
                                    skipped_placeholder_lines : placeholder_lines_at_begin + 2
                                ]
                            ):
                                placeholder_lines_at_begin -= skipped_placeholder_lines
                                break
                        else:
                            is_wrong_insertion = True
                if edit_range[1] != content_lines_cnt:
                    if (
                        updated_lines[-placeholder_lines_at_end - 1 :]
                        != original_lines[-placeholder_lines_at_end - 1 :]
                    ):
                        for skipped_placeholder_lines in range(1, placeholder_lines_at_end + 1):
                            if (
                                updated_lines[
                                    -(placeholder_lines_at_end - skipped_placeholder_lines) - 2 :
                                ]
                                == original_lines[
                                    -placeholder_lines_at_end - 2 : -skipped_placeholder_lines
                                ]
                            ):
                                placeholder_lines_at_end -= skipped_placeholder_lines
                                break
                        else:
                            is_wrong_insertion = True

                if is_wrong_insertion:
                    retry_prompt = merge_not_between_err.format(lines=edit.tag.lines)
                    main_model_error = cannot_insert_between_err.format(lines=edit.tag.lines)
                else:
                    # response is ok
                    updated_lines = updated_lines[
                        placeholder_lines_at_begin : len(updated_lines) - placeholder_lines_at_end
                    ]

                    content_lines[edit_range[0] : edit_range[1]] = updated_lines
                    break
            elif merge_no_changes_pattern.match(updated_responce):
                # when user have already written a part of the code, which he requests from the LLM (for example have added declaration and request LLM to write rest of the code),
                # most of LLMs tend to repeat this part of the code in their answer
                #
                # so we need to skip this code block and best way is to add a special variant of answer for merge model
                # and here it is handled
                break
            else:
                retry_prompt = bad_merge_response_err
                main_model_error = merge_model_failed_err

            messages.append(dict(role="assistant", content=updated_responce))
            messages.append(dict(role="user", content=retry_prompt))
        else:
            # merge model failed to merge this snippet
            return False, None, main_model_error

        return True, content_lines, None

    def apply_edits(self, edits: list[BetweenCoderEdit]):
        failed: list[tuple[BetweenCoderEdit, str]] = []
        passed = []

        for idx, edit in enumerate(edits):
            full_path = self.abs_root_path(edit.path)
            base_name = os.path.basename(edit.path)

            content = None
            content_lines = None
            if Path(full_path).exists():
                content = self.io.read_text(full_path)
                content_lines = content.splitlines(keepends=True)

            if edit.tag.tag == "@BETWEEN@":
                if edit.tag.is_bad:
                    failed.append((edit, bad_between_tag_err))
                    continue
                spinner_text = f"Merging snippet {idx+1} into {base_name}"
                success, changed_lines, error_message = self.apply_between_edit(
                    content_lines, edit, spinner_text
                )
                del content_lines  # became invalid after call

                if success:
                    self.io.write_text(full_path, "".join(changed_lines))
                    passed.append(edit)
                else:
                    failed.append((edit, error_message))
            elif edit.tag.tag == "@WHOLE FILE@":
                self.io.write_text(full_path, edit.snippet)
                passed.append(edit)
            else:
                failed.append(
                    (
                        edit,
                        invalid_tag_err.format(
                            tag=edit.tag.tag, allowed_tags_list=", ".join(allowed_tags)
                        ),
                    )
                )

        if not failed:
            return

        res = (
            f"# {len(failed)} {'code block' if len(failed) == 1 else 'code blocks'} not"
            " applied!\n\n"
        )

        for failed_block in failed:
            edit, error_message = failed_block
            res += f"""{edit.path}
{self.fence[0]}
{edit.tag.tag_line.strip()}
{edit.snippet}{self.fence[1]}
"""
            res += error_message + "\n"
            res += "\n"

        if passed:
            res += f"""# The other {len(passed)} {"code block" if len(passed) == 1 else "code blocks"} were applied successfully.
Don't re-send them.
Just reply with fixed versions of the {"code block" if len(failed) == 1 else "code blocks"} above that failed to apply.
"""
        raise ValueError(res)
