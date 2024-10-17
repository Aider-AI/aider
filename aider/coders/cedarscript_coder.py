from cedarscript_editor import find_commands, CEDARScriptEditor
from aider.coders.base_coder import Coder
from aider.coders.base_prompts import CoderPrompts
import os
from cedarscript_integration_aider import CEDARScriptPromptsGrammar, CEDARScriptPromptsRW, CEDARScriptPromptsW

class CEDARScriptCoder(Coder):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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
        cedarscript_editor = CEDARScriptEditor(root_path=os.getcwd())
        cedarscript_commands = [x[1] for x in file_and_cedarscript_commands]
        print(f"[apply_edits] Command count: {len(cedarscript_commands)}")
        for i, applied_command_result in enumerate(cedarscript_editor.apply_commands(cedarscript_commands)):
            print(f"[apply_edits]   (#{i+1}) {applied_command_result}")

class _CEDARScriptPromptsAdapter(CoderPrompts):
    def __init__(self, cedarscript_prompts):
        self.cedarscript_prompts = cedarscript_prompts

    def __getattr__(self, name):
        result = getattr(self.cedarscript_prompts, name)
        if name != 'edit_format_training':
            print(f"[__getattr__] {name} = {result}")
        if name == 'edit_format_name':
            print(f'edit_format_name: {result()}')
        return result

class CEDARScriptCoderGrammar(CEDARScriptCoder):
    gpt_prompts = _CEDARScriptPromptsAdapter(CEDARScriptPromptsGrammar())
    edit_format = gpt_prompts.edit_format_name()

class CEDARScriptCoderRW(CEDARScriptCoder):
    gpt_prompts = _CEDARScriptPromptsAdapter(CEDARScriptPromptsRW())
    edit_format = gpt_prompts.edit_format_name()

class CEDARScriptCoderW(CEDARScriptCoder):
    gpt_prompts = _CEDARScriptPromptsAdapter(CEDARScriptPromptsW())
    edit_format = gpt_prompts.edit_format_name()

