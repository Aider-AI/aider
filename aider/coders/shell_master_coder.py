from .folder_coder import AiderFolderCoder


class ShellMasterCoder(AiderFolderCoder):
    """Master of shell scripting."""

    edit_format = "shell-master"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, edit_format = self.edit_format, **kwargs)
