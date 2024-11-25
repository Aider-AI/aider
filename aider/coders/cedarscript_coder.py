import os

from cedarscript_editor import find_commands, CEDARScriptEditor
import cedarscript_integration_aider
from aider.coders.folder_coder import FolderCoder


class CEDARScriptCoderBase(FolderCoder):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, prompt_folder_path=cedarscript_integration_aider.prompt_folder_path, **kwargs)
        self.root_path = kwargs.get('root_path', os.getcwd())

    def get_edits(self):
        # Note: it should be allowed for the editor to change any file in the project, as changing the file
        # doesn't require the full file contents to be sent to the LLM.
        content = self.partial_response_content
        cedarscript_commands = list(find_commands(content))
        # TODO Handle shell commands
        # self.shell_commands = [edit for edit in edits if edit[0] is None]
        for files_to_change in [cedarscript_command.files_to_change for cedarscript_command in cedarscript_commands]:
            print(f'[get_edits] "{files_to_change}"')
        result = [
            (cedarscript_command.files_to_change[0], cedarscript_command)
            for cedarscript_command in cedarscript_commands
            if cedarscript_command.files_to_change
        ]
        return result

    def apply_edits(self, file_and_cedarscript_commands):
        """
        Apply the edits (expressed as CEDARScript commands) to the files
        """
        cedarscript_editor = CEDARScriptEditor(root_path=self.root_path)
        cedarscript_commands = [x[1] for x in file_and_cedarscript_commands]
        print(f"[apply_edits] Command count: {len(cedarscript_commands)}")
        for i, applied_command_result in enumerate(cedarscript_editor.apply_commands(cedarscript_commands)):
            print(f"[apply_edits]   (#{i+1}) {applied_command_result}")


class CEDARScriptCoder(CEDARScriptCoderBase):
    edit_format = "cedarscript"
    def __init__(self, *args, **kwargs):
        super().__init__(*args, edit_format = self.edit_format, **kwargs)
