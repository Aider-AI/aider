import unittest
from unittest.mock import MagicMock, patch

from aider.coders.architect_coder import ArchitectCoder
from aider.io import InputOutput
from aider.models import Model


class TestBatchEditing(unittest.TestCase):
    def setUp(self):
        self.GPT35 = Model("gpt-3.5-turbo")
        self.webbrowser_patcher = patch("aider.io.webbrowser.open")
        self.mock_webbrowser = self.webbrowser_patcher.start()

    def tearDown(self):
        self.webbrowser_patcher.stop()

    def test_batch_editing_default_value(self):
        """Test that the default value for use_batch_editing is False"""
        # Create an architect coder with default settings
        io = InputOutput(yes=True)
        with patch("aider.coders.architect_coder.AskCoder.__init__", return_value=None):
            coder = ArchitectCoder(main_model=self.GPT35, io=io)
            
            # Check that the default value is False
            self.assertFalse(coder.use_batch_editing)

    def test_batch_editing_parameter_passing(self):
        """Test that the use_batch_editing parameter is correctly passed to the ArchitectCoder"""
        io = InputOutput(yes=True)
        
        # Test with explicit True setting
        with patch("aider.coders.architect_coder.AskCoder.__init__", return_value=None):
            coder = ArchitectCoder(main_model=self.GPT35, io=io, use_batch_editing=True)
            self.assertTrue(coder.use_batch_editing)
        
        # Test with explicit False setting
        with patch("aider.coders.architect_coder.AskCoder.__init__", return_value=None):
            coder = ArchitectCoder(main_model=self.GPT35, io=io, use_batch_editing=False)
            self.assertFalse(coder.use_batch_editing)

    def test_batch_editing_usage_in_reply_completed(self):
        """Test that the use_batch_editing attribute controls the flow in reply_completed"""
        io = InputOutput(yes=True)
        io.confirm_ask = MagicMock(return_value=True)
        
        # Create an ArchitectCoder with use_batch_editing=True
        with patch("aider.coders.architect_coder.AskCoder.__init__", return_value=None):
            coder = ArchitectCoder(main_model=self.GPT35, io=io)
            # Set up the necessary attributes manually
            coder.io = io  # Need to set this explicitly since we're mocking __init__
            coder.main_model = self.GPT35
            coder.auto_accept_architect = True
            coder.verbose = False
            coder.total_cost = 0
            coder.cur_messages = []
            coder.done_messages = []
            coder.aider_commit_hashes = None
            coder.move_back_cur_messages = MagicMock()
            
            # Mock the split_response_by_natural_delimiters method
            coder.split_response_by_natural_delimiters = MagicMock()
            coder.split_response_by_natural_delimiters.return_value = ["chunk1", "chunk2"]
            
            # Mock editor_coder creation and execution
            mock_editor = MagicMock()
            mock_editor.total_cost = 0
            mock_editor.aider_commit_hashes = set()
            
            # Test with use_batch_editing=True
            coder.use_batch_editing = True
            with patch("aider.coders.architect_coder.Coder.create", return_value=mock_editor):
                # Set partial response content
                coder.partial_response_content = "Make these changes to the code"
                
                # Call reply_completed
                coder.reply_completed()
                
                # Verify split_response_by_natural_delimiters was called
                coder.split_response_by_natural_delimiters.assert_called_once_with("Make these changes to the code")
                
                # Verify Coder.create was called twice (once for each chunk)
                self.assertEqual(mock_editor.run.call_count, 2)
            
            # Reset mocks
            coder.split_response_by_natural_delimiters.reset_mock()
            mock_editor.run.reset_mock()
            
            # Test with use_batch_editing=False
            coder.use_batch_editing = False
            with patch("aider.coders.architect_coder.Coder.create", return_value=mock_editor):
                # Call reply_completed
                coder.reply_completed()
                
                # Verify split_response_by_natural_delimiters was NOT called
                coder.split_response_by_natural_delimiters.assert_not_called()
                
                # Verify Coder.create was called once for the entire content
                mock_editor.run.assert_called_once()


if __name__ == "__main__":
    unittest.main()