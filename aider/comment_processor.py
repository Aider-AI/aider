import re
from typing import Optional, Tuple, List
from grep_ast import TreeContext
from aider.io import InputOutput


class CommentProcessor:
    """Processes AI comments in source files"""

    # Compiled regex pattern for AI comments
    ai_comment_pattern = re.compile(
        r"(?:#|//|--) *(ai\b.*|ai\b.*|.*\bai[?!]?) *$", re.IGNORECASE
    )

    def __init__(self, io: InputOutput, coder, analytics=None):
        self.io = io
        self.coder = coder
        self.analytics = analytics

    def get_ai_comments(self, filepath):
        """Extract AI comment line numbers, comments and action status from a file"""
        line_nums = []
        comments = []
        has_action = None  # None, "!" or "?"
        content = self.io.read_text(filepath, silent=True)
        if not content:
            return None, None, None

        for i, line in enumerate(content.splitlines(), 1):
            if match := self.ai_comment_pattern.search(line):
                comment = match.group(0).strip()
                if comment:
                    line_nums.append(i)
                    comments.append(comment)
                    comment = comment.lower()
                    comment = comment.lstrip("/#-")
                    comment = comment.strip()
                    if comment.startswith("ai!") or comment.endswith("ai!"):
                        has_action = "!"
                    elif comment.startswith("ai?") or comment.endswith("ai?"):
                        has_action = "?"
        if not line_nums:
            return None, None, None
        return line_nums, comments, has_action

    def process_changes(self, changed_files)
        """Process file changes and generate prompt from AI comments"""
        from aider.watch_prompts import watch_code_prompt, watch_ask_prompt

        has_action = None
        added = False
        for fname in changed_files:
            _, _, action = self.get_ai_comments(fname)
            if action in ("!", "?"):
                has_action = action

            if fname in self.coder.abs_fnames:
                continue
            if self.analytics:
                self.analytics.event("ai-comments file-add")
            self.coder.abs_fnames.add(fname)
            rel_fname = self.coder.get_rel_fname(fname)
            if not added:
                self.io.tool_output()
                added = True
            self.io.tool_output(f"Added {rel_fname} to the chat")

        if not has_action:
            if added:
                self.io.tool_output(
                    "End your comment with AI! to request changes or AI? to ask questions"
                )
            return ""

        if self.analytics:
            self.analytics.event("ai-comments execute")
        self.io.tool_output("Processing your request...")

        if has_action == "!":
            res = watch_code_prompt
        elif has_action == "?":
            res = watch_ask_prompt

        # Refresh all AI comments from tracked files
        for fname in self.coder.abs_fnames:
            line_nums, comments, _action = self.get_ai_comments(fname)
            if not line_nums:
                continue

            code = self.io.read_text(fname)
            if not code:
                continue

            rel_fname = self.coder.get_rel_fname(fname)
            res += f"\n{rel_fname}:\n"

            # Convert comment line numbers to line indices (0-based)
            lois = [ln - 1 for ln, _ in zip(line_nums, comments) if ln > 0]

            try:
                context = TreeContext(
                    rel_fname,
                    code,
                    color=False,
                    line_number=False,
                    child_context=False,
                    last_line=False,
                    margin=0,
                    mark_lois=True,
                    loi_pad=3,
                    show_top_of_file_parent_scope=False,
                )
                context.lines_of_interest = set()
                context.add_lines_of_interest(lois)
                context.add_context()
                res += context.format()
            except ValueError:
                for ln, comment in zip(line_nums, comments):
                    res += f"  Line {ln}: {comment}\n"

        return res
