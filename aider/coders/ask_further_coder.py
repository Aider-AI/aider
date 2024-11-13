from .folder_coder import AiderFolderCoder


class AskFurtherCoder(AiderFolderCoder):
    """Ask questions about code without making any changes."""

    edit_format = "ask-further"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, edit_format = self.edit_format, **kwargs)
