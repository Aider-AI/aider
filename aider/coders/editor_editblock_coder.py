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
