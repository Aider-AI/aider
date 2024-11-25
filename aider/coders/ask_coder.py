from .folder_coder import AiderFolderCoder


class AskCoder(AiderFolderCoder):
    """Ask questions about code without making any changes."""

    edit_format = "ask"

    def __init__(self, *args, edit_format: str = edit_format, **kwargs):
        """
        :param edit_format: Allows subclasses to specify their own edit_format
        """
        super().__init__(*args, edit_format = edit_format, **kwargs)
