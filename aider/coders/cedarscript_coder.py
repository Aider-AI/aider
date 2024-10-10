import re
import xml.etree.ElementTree as ET

from cedarscript_editor import PythonCEDARScriptEditor
from cedarscript_ast_parser import CEDARScriptASTParser, Command
from aider.coders.base_coder import Coder
from aider.coders.cedarscript_prompts_w import CedarPromptsW
from aider.coders.cedarscript_prompts_rw import CedarPromptsRW
from aider.coders.cedarscript_prompts_g import CedarPromptsGrammar
import os


class CedarCoder(Coder):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cedarscript_parser = CEDARScriptASTParser()
        self.cedar_editor = PythonCEDARScriptEditor(os.getcwd())

    def find_cedar_commands(self, content):
        # Regex pattern to match Cedar blocks
        pattern = r'```CEDARScript\n(.*?)```'
        cedar_script_blocks = re.findall(pattern, content, re.DOTALL)
        print(f'[find_cedar_commands] Script block count: {len(cedar_script_blocks)}')
        if len(cedar_script_blocks) == 0:
            raise ValueError("No CEDARScript block detected. Perhaps you forgot to enclose the block using ```CEDARScript and ``` ? Or was that intentional?")
        for cedar_script in cedar_script_blocks:
            parsed_commands, parse_errors = self.cedarscript_parser.parse_script(cedar_script)
            if parse_errors:
                raise ValueError(f"CEDARScript parsing errors: {[str(pe) for pe in parse_errors]}")
            for cedar_command in parsed_commands:
                yield cedar_command


    def get_edits(self):
        # Note: it should be allowed for the editor to change any file in the project, as changing the file
        # doesn't require the full file contents to be sent to the LLM.
        content = self.partial_response_content
        cedar_commands: list[Command] = list(self.find_cedar_commands(content))
        # TODO Handle shell commands
        # self.shell_commands = [edit for edit in edits if edit[0] is None]
        for files_to_change in [cedar_command.files_to_change for cedar_command in cedar_commands]:
            print(f'[get_edits] "{files_to_change}"')
        result = [(cedar_command.files_to_change[0], cedar_command) for cedar_command in cedar_commands if cedar_command.files_to_change]
        return result

    def apply_edits(self, file_and_cedar_commands):
        """
        Apply the edits (expressed as Cedar commands) to the files
        """
        cedar_commands = [x[1] for x in file_and_cedar_commands]
        print(f"[apply_edits] Command count: {len(cedar_commands)}")
        for i, applied_command_result in enumerate(self.cedar_editor.apply_commands(cedar_commands)):
            print(f"[apply_edits]   (#{i+1}) {applied_command_result}")


    def _format_cedar_output(self, operation: str, status: str, result: list[str]) -> str:
        """Format the output according to CEDAR specification"""
        root = ET.Element("cedar-operation")
        ET.SubElement(root, "type").text = operation
        ET.SubElement(root, "status").text = status
        params = ET.SubElement(root, "parameters")
        # Add parameters here if needed
        result_elem = ET.SubElement(root, "result")
        for item in result:
            ET.SubElement(result_elem, "item").text = item
        ET.SubElement(root, "execution-time").text = "0.05s"  # Example execution time
        return ET.tostring(root, encoding="unicode")


class CedarCoderGrammar(CedarCoder):
    gpt_prompts = CedarPromptsGrammar()
    edit_format = gpt_prompts.edit_format_name()


class CedarCoderRW(CedarCoder):
    gpt_prompts = CedarPromptsRW()
    edit_format = gpt_prompts.edit_format_name()


class CedarCoderW(CedarCoder):
    gpt_prompts = CedarPromptsW()
    edit_format = gpt_prompts.edit_format_name()

