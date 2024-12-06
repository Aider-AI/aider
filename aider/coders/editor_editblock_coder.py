from .editblock_coder import EditBlockCoder
from .editor_editblock_prompts import EditorEditBlockPrompts


class EditorEditBlockCoder(EditBlockCoder):
    edit_format = "editor-diff"
    gpt_prompts = EditorEditBlockPrompts()

    def format_chat_markdown(self):
        chunks = self.format_chat_chunks()

        markdown = ""

        # Only include specified chunks in order
        for messages in [chunks.repo, chunks.readonly_files, chunks.chat_files, chunks.cur]:
            for msg in messages:
                # Only include user messages
                if msg["role"] != "user":
                    continue

                content = msg["content"]

                # Handle image/multipart content
                if isinstance(content, list):
                    for part in content:
                        if part.get("type") == "text":
                            markdown += part["text"] + "\n\n"
                else:
                    markdown += content + "\n\n"

        return markdown.strip()

    def format_chat_chunks(self):
        chunks = super().format_chat_chunks()
        # Only add reminder if there are current messages
        if chunks.cur:
            final = chunks.cur[-1]
            if self.main_model.reminder == "sys":
                chunks.reminder = self.reminder_message
            elif self.main_model.reminder == "user" and final["role"] == "user":
                # stuff it into the user message
                new_content = (
                    final["content"]
                    + "\n\n"
                    + self.fmt_system_prompt(self.gpt_prompts.system_reminder)
                )
                chunks.cur[-1] = dict(role=final["role"], content=new_content)
        return chunks
