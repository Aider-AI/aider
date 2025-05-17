from .architect_prompts import ArchitectPrompts
from .ask_coder import AskCoder
from .base_coder import Coder


class ArchitectCoder(AskCoder):
    edit_format = "architect"
    gpt_prompts = ArchitectPrompts()
    auto_accept_architect = False
    use_batch_editing = False
    
    def __init__(self, main_model, io, use_batch_editing=False, auto_accept_architect=None, **kwargs):
        super().__init__(main_model, io, **kwargs)
        if auto_accept_architect is not None:
            self.auto_accept_architect = auto_accept_architect
        self.use_batch_editing = use_batch_editing

    def reply_completed(self):
        content = self.partial_response_content

        if not content or not content.strip():
            return

        if not self.auto_accept_architect and not self.io.confirm_ask("Edit the files?"):
            return

        kwargs = dict()

        # Use the editor_model from the main_model if it exists, otherwise use the main_model itself
        editor_model = self.main_model.editor_model or self.main_model

        kwargs["main_model"] = editor_model
        kwargs["edit_format"] = self.main_model.editor_edit_format
        kwargs["suggest_shell_commands"] = False
        kwargs["map_tokens"] = 0
        kwargs["total_cost"] = self.total_cost
        kwargs["cache_prompts"] = False
        kwargs["num_cache_warming_pings"] = 0
        kwargs["summarize_from_coder"] = False

        new_kwargs = dict(io=self.io, from_coder=self)
        new_kwargs.update(kwargs)

        # Use the instance attribute for use_batch_editing

        if self.use_batch_editing:
            # split the architect model response into chunks using natural delimiters (code blocka, newlines, separators, etc.)
            chunks = []
            chunks = self.split_response_by_natural_delimiters(content)

            for chunk in chunks:
                if not chunk.strip():
                    continue

                # Create a new chat session with the editor coder llm model for each chunk of the architect model response
                editor_coder = Coder.create(**new_kwargs)
                editor_coder.cur_messages = []
                editor_coder.done_messages = []

                if self.verbose:
                    editor_coder.show_announcements()

                editor_coder.run(with_message=chunk, preproc=False)

                self.move_back_cur_messages("I made those changes to the files.")
                self.total_cost += editor_coder.total_cost
                if self.aider_commit_hashes is None:
                    self.aider_commit_hashes = set()
                self.aider_commit_hashes.update(editor_coder.aider_commit_hashes or set())
        else:
            # Create only one chat session with the editor coder llm model, not splitting the architect answer in chunks.
            editor_coder = Coder.create(**new_kwargs)
            editor_coder.cur_messages = []
            editor_coder.done_messages = []

            if self.verbose:
                editor_coder.show_announcements()

            # Run the editor coder with the entire architect model response
            editor_coder.run(with_message=content, preproc=False)

            self.move_back_cur_messages("I made those changes to the files.")
            self.total_cost = editor_coder.total_cost
            self.aider_commit_hashes = editor_coder.aider_commit_hashes


    def split_response_by_natural_delimiters(self, content):
        """
        Splits the content into chunks using natural delimiters, with heuristics:
        - Never splits inside code blocks (even nested/mixed fences).
        - Detects repeated block patterns (title/tag, blank lines, filename, code block) and splits accordingly.
        - Lone comments between blocks are included in both adjacent chunks.
        - Groups filename fences with their following code block.
        - Groups delimiters/tags with their following block, including blank lines.
        - Falls back to delimiter/tag splitting if no repeated pattern is found.
        """
        import re

        # Fence definitions
        fence_openers = [
            r"```[\w-]*", r"~~~~[\w-]*",
            r"<code>", r"<pre>", r"<source>", r"<codeblock>", r"<sourcecode>", r"<diff>", r"<diff-fenced>"
        ]
        fence_closers = [
            r"```", r"~~~~",
            r"</code>", r"</pre>", r"</source>", r"</codeblock>", r"</sourcecode>", r"</diff>", r"</diff-fenced>"
        ]
        fence_opener_re = re.compile(rf"^({'|'.join(fence_openers)})\s*$", re.IGNORECASE)
        fence_closer_re = re.compile(rf"^({'|'.join(fence_closers)})\s*$", re.IGNORECASE)

        # Patterns for tags/titles, filenames, comments, and delimiters
        tag_pattern = re.compile(
            r"""(
                ^\[[A-Z0-9 _:\-./()]+\]$ |                 # [ALL CAPS/NUMERIC/UNDERSCORE/ETC]
                ^<[\w\s:\-./()|=\[\]!]+>$ |                # <TAG ...>
                ^<<[\w\s:\-./()|=\[\]!]+>>$ |              # <<TAG ...>>
                ^<\|[\w\s:\-./()|=\[\]!]+\|>$ |            # <|TAG ...|>
                ^<=.*=>$ |                                 # <=...=>
                ^<!.*!>$ |                                 # <!....!>
                ^<==\|.*\|==>$                             # <==| ... |==>
            )""",
            re.MULTILINE | re.VERBOSE
        )
        filename_pattern = re.compile(r"^[\w\./\\\-]+\.?\w*$")
        comment_pattern = re.compile(r"^(#|<!--).*")
        delimiter_pattern = re.compile(
            r"""(
                ^----$ | ^={3,}$ | ^\s*#+\s.*?$ | \n{3,}
            )""",
            re.MULTILINE | re.VERBOSE
        )

        lines = content.splitlines(keepends=True)
        n = len(lines)

        # Step 1: Find all block start indices using the repeated pattern heuristic
        block_starts = []
        i = 0
        while i < n:
            # Look for 1-2 blank lines, then a tag/title, then 0-2 blank lines, then optional filename, then a fence opener
            j = i
            # Skip up to 2 blank lines
            blanks = 0
            while j < n and lines[j].strip() == "" and blanks < 2:
                j += 1
                blanks += 1
            # Tag/title
            if j < n and tag_pattern.match(lines[j]):
                tag_idx = j
                j += 1
                # Up to 2 blank lines
                blanks2 = 0
                while j < n and lines[j].strip() == "" and blanks2 < 2:
                    j += 1
                    blanks2 += 1
                # Optional filename
                if j < n and filename_pattern.match(lines[j].strip()):
                    j += 1
                # Fence opener
                if j < n and fence_opener_re.match(lines[j]):
                    block_starts.append(i)
                    # Move to the end of the code block (handle nesting)
                    fence_stack = [fence_opener_re.match(lines[j]).group(1)]
                    j += 1
                    while j < n and fence_stack:
                        if fence_opener_re.match(lines[j]):
                            fence_stack.append(fence_opener_re.match(lines[j]).group(1))
                        elif fence_closer_re.match(lines[j]):
                            if fence_stack and fence_closer_re.match(lines[j]).group(1).lower().replace("-", "") == fence_stack[-1].lower().replace("-", ""):
                                fence_stack.pop()
                        j += 1
                    i = j
                    continue
            i += 1

        # If no repeated pattern found, fallback to delimiter/tag/code block splitting
        if not block_starts:
            block_starts = [0]
            i = 0
            while i < n:
                # Find next delimiter/tag outside code blocks
                if tag_pattern.match(lines[i]) or delimiter_pattern.match(lines[i]):
                    block_starts.append(i)
                i += 1

        # Step 2: Split into chunks, handling lone comments
        chunks = []
        for idx, start in enumerate(block_starts):
            end = block_starts[idx + 1] if idx + 1 < len(block_starts) else n
            chunk_lines = lines[start:end]

            # If the last line(s) are lone comments, keep them for the next chunk too
            comment_lines = []
            while chunk_lines and comment_pattern.match(chunk_lines[-1]) and not fence_opener_re.match(chunk_lines[-1]):
                comment_lines.insert(0, chunk_lines.pop())
            chunk = "".join(chunk_lines)
            if chunk.strip():
                chunks.append(chunk)
            # Add comment lines to the next chunk as well
            if comment_lines and idx + 1 < len(block_starts):
                lines[block_starts[idx + 1]:block_starts[idx + 1]] = comment_lines

        return chunks

