import unittest
from unittest.mock import MagicMock, patch

from aider.coders.architect_coder import ArchitectCoder
from aider.coders.architect_prompts import ArchitectPrompts, ArchitectBatchEditingPrompts
from aider.coders.base_coder import Coder
from aider.io import InputOutput
from aider.models import Model

class TestArchitectCoder(unittest.TestCase):
    def setUp(self):
        self.model = Model("gpt-3.5-turbo")
        self.model.editor_model = None
        self.model.editor_edit_format = "diff"
        self.io = InputOutput(yes=True)
        self.io.confirm_ask = MagicMock(return_value=True)
        with patch("aider.coders.architect_coder.AskCoder.__init__", return_value=None):
            self.coder = ArchitectCoder(main_model=self.model, io=self.io)
            self.coder.io = self.io
            self.coder.main_model = self.model
            self.coder.auto_accept_architect = True
            self.coder.verbose = False
            self.coder.total_cost = 0
            self.coder.cur_messages = []
            self.coder.done_messages = []
            self.coder.aider_commit_hashes = None
            self.coder.move_back_cur_messages = MagicMock()

    def test_batch_editing_comprehensive(self):
        """Comprehensive test for batch editing functionality including prompts, separators, and fallbacks"""
        with patch("aider.coders.architect_coder.AskCoder.__init__", return_value=None):
            # Test batch editing enabled uses dedicated batch prompt class
            batch_coder = ArchitectCoder(main_model=self.model, io=self.io, use_batch_editing=True)
            self.assertIsInstance(batch_coder.gpt_prompts, ArchitectBatchEditingPrompts)
            self.assertIn("BATCH EDITING MODE", batch_coder.gpt_prompts.main_system)
            self.assertIn("---BATCH_EDIT_SEPARATOR---", batch_coder.gpt_prompts.main_system)
            
            # Test batch editing disabled uses normal prompts
            normal_coder = ArchitectCoder(main_model=self.model, io=self.io, use_batch_editing=False)
            self.assertIsInstance(normal_coder.gpt_prompts, ArchitectPrompts)
            self.assertNotIn("BATCH EDITING MODE", normal_coder.gpt_prompts.main_system)

        # Test separator-based splitting
        separator_sample = """
First task for file1.py:
```python
def func1():
    pass
```
---BATCH_EDIT_SEPARATOR---
Second task for file2.py:
```python
def func2():
    pass
```
---BATCH_EDIT_SEPARATOR---
Third task for file3.py:
```python
def func3():
    pass
```
"""
        chunks = self.coder.split_response_by_natural_delimiters(separator_sample)
        self.assertEqual(len(chunks), 3)
        self.assertTrue(any("file1.py" in chunk and "func1" in chunk for chunk in chunks))
        self.assertTrue(any("file2.py" in chunk and "func2" in chunk for chunk in chunks))
        self.assertTrue(any("file3.py" in chunk and "func3" in chunk for chunk in chunks))

        # Test fallback to single chunk when no separators
        natural_sample = """
[FILE: file1.py]
```python
def foo():
    pass
```
[FILE: file2.py]
```python
def bar():
    pass
```
"""
        chunks = self.coder.split_response_by_natural_delimiters(natural_sample)
        self.assertEqual(len(chunks), 1)  # Now returns entire content as one chunk
        self.assertTrue("file1.py" in chunks[0])
        self.assertTrue("file2.py" in chunks[0])

    def test_batch_mode_settings_and_validation(self):
        """Test batch mode settings, auto-lint/test disabling, and chunk validation"""
        # Test auto-lint/test settings
        captured_kwargs = []
        def mock_create(**kwargs):
            captured_kwargs.append(kwargs)
            mock_coder = MagicMock()
            mock_coder.total_cost = 0
            mock_coder.aider_commit_hashes = set()
            mock_coder.cur_messages = []
            mock_coder.done_messages = []
            mock_coder.show_announcements = MagicMock()
            mock_coder.run = MagicMock()
            return mock_coder
        
        with patch('aider.coders.architect_coder.Coder.create', side_effect=mock_create):
            # Test batch mode disables auto_lint and auto_test
            self.coder.use_batch_editing = True
            self.coder.partial_response_content = "Test\n```python\ncode\n```"
            self.coder.auto_accept_architect = True
            self.coder.abs_fnames = set(["test.py"])
            
            self.coder.reply_completed()
            
            self.assertTrue(len(captured_kwargs) > 0)
            batch_kwargs = captured_kwargs[0]
            self.assertEqual(batch_kwargs["auto_lint"], False)
            self.assertEqual(batch_kwargs["auto_test"], False)
            
            # Test non-batch mode doesn't set auto_lint/auto_test (matches original behavior)
            captured_kwargs.clear()
            self.coder.use_batch_editing = False
            
            self.coder.reply_completed()
            
            self.assertTrue(len(captured_kwargs) > 0)
            normal_kwargs = captured_kwargs[0]
            # In normal mode, auto_lint and auto_test should not be set (preserves original behavior)
            self.assertNotIn("auto_lint", normal_kwargs)
            self.assertNotIn("auto_test", normal_kwargs)

    def test_split_response_by_natural_delimiters(self):
        sample = """
[FILE: file1.py]
```python
def foo():
    pass
```
[FILE: file2.py]
```python
def bar():
    pass
```
"""
        chunks = self.coder.split_response_by_natural_delimiters(sample)
        self.assertEqual(len(chunks), 1)  # Now returns entire content as one chunk
        self.assertTrue("file1.py" in chunks[0])
        self.assertTrue("file2.py" in chunks[0])
        self.assertTrue("def foo" in chunks[0])
        self.assertTrue("def bar" in chunks[0])

    def test_extract_filenames_from_chunk(self):
        """Test filename extraction from chunks for context reduction"""
        chat_files = ['main.py', 'utils.py', 'config.py']
        
        # Test new batch format with **filename**
        chunk1 = "**main.py**\nUpdate the main function:\n```python\ndef main(): pass\n```"
        files1 = self.coder.extract_filenames_from_chunk(chunk1, chat_files)
        self.assertIn('main.py', files1)
        
        # Test multiple files in batch format
        chunk2 = "**utils.py**\nModify utility functions:\n```python\ndef util(): pass\n```"
        files2 = self.coder.extract_filenames_from_chunk(chunk2, chat_files)
        self.assertIn('utils.py', files2)
        
        # Test file not in chat_files (should still be extracted)
        chunk3 = "**newfile.py**\nCreate new file:\n```python\nprint('hello')\n```"
        files3 = self.coder.extract_filenames_from_chunk(chunk3, None)
        self.assertIn('newfile.py', files3)
        
        # Test old patterns are not matched anymore
        chunk4 = "Update the main.py file:\n```python\ndef main(): pass\n```"
        files4 = self.coder.extract_filenames_from_chunk(chunk4, chat_files)
        self.assertEqual(len(files4), 0)  # Should not match old patterns

if __name__ == "__main__":
    unittest.main()