import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from aider.coders import Coder
from aider.io import InputOutput
from aider.models import Model
from aider.repo import GitRepo
from aider.utils import GitTemporaryDirectory


class TestBatchCoder(unittest.TestCase):
    def setUp(self):
        self.GPT35 = Model("gpt-3.5-turbo")
        self.io = InputOutput(yes=True)
        # self.webbrowser_patcher = patch("aider.io.webbrowser.open")
        # self.mock_webbrowser = self.webbrowser_patcher.start()
        
        # Get all Python files in aider/coders directory
        coders_dir = Path(__file__).parent.parent.parent / "aider" / "coders"
        self.files = [str(f) for f in coders_dir.glob("*.py") if f.is_file()]
        
        # Create coder with all files
        self.coder = Coder.create(
            main_model=self.GPT35,
            io=self.io,
            fnames=self.files,
            edit_format='batch'
        )

    def tearDown(self):
        # self.webbrowser_patcher.stop()
        return
    """Tests that: 
    - Every request retains the chat history until the /batch command but not the history of other iterations.
    - Added files and history until the /batch is unmodified.
    - Every file is processed(even if a single file that'll be sent with the request exceeds the limits.) and no duplicate processing
    """
    def test_iterate_resets_history_and_processes_all_files(self):
        processed_files :list[str]= []
        original_context:list[dict[str,str]]
        prev_file_names : list[str] = None
        # Track messages sent to LLM and files processed
        def mock_send(self,messages, model=None, functions=None):
            nonlocal original_context       
            nonlocal processed_files
            nonlocal prev_file_names
            for original_message in original_context:
                assert original_message in messages, f"Chat history before start of the command is not retained."
            # Simulate response mentioning filename
            files_message = [msg['content'] for msg in messages if "*added these files to the chat*" in msg['content']][0]
            from re import findall
            file_names =  findall(r'.*\n(\S+\.py)\n```.*',files_message)
            for f_name in file_names:
                assert prev_file_names == None or f_name not in prev_file_names, "files from previous iterations hasn't been cleaned up."
            prev_file_names = file_names
            processed_files.extend(file_names)
            # Return minimal response
            self.partial_response_content = "Done."
            self.partial_response_function_call=dict()

        with GitTemporaryDirectory():
            # Mock the send method
            with (patch.object(Coder, 'send',new_callable=lambda: mock_send), patch.object(Coder, 'lint_edited',lambda *_,**__:None), patch.object(GitRepo,'commit',lambda *_,**__:None)): 
                self.coder.coder = Coder.create(main_model=self.coder.main_model, edit_format=self.coder.main_model.edit_format,from_coder=self.coder,**self.coder.original_kwargs)
                # Add initial conversation history
                original_context = self.coder.done_messages = [
                    {"role": "user", "content": "Initial conversation"},
                    {"role": "assistant", "content": "OK"}
                ]
                
                # Run iterate command
                self.coder.run(with_message="Process all files")
                # Verify all files were processed
                input_basenames = {Path(f).name for f in self.files}
                processed_basenames = {Path(f).name for f in processed_files}
                missing = input_basenames - processed_basenames
                assert not missing, f"Files not processed: {missing}"
                
                # Verify history preservation and structure
                assert len(self.coder.done_messages) == 2, "Original chat history was modified"
                # Verify final file state
                assert len(self.coder.abs_fnames) == len(self.files), "Not all files remained in chat"

if __name__ == "__main__":
    unittest.main()
