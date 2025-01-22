import os
import time
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from diskcache import Cache

from aider.file_summary import FileSummary
from aider.summary_cache import SummaryCache


@pytest.fixture
def mock_io():
    io = MagicMock()
    io.read_text = MagicMock(return_value="test content")
    return io


@pytest.fixture
def mock_model():
    model = MagicMock()
    model.max_chat_history_tokens = 1000
    model.name = "test-model"
    model.info = {
        "input_cost_per_token": 0.001,
        "output_cost_per_token": 0.002
    }
    return model


@pytest.fixture
def mock_cache(tmp_path):
    cache_dir = tmp_path / ".aider/summary.cache"
    return Cache(str(cache_dir))


@pytest.fixture
def test_file(tmp_path):
    file = tmp_path / "test.py"
    content = """
def function1():
    '''Test function 1'''
    pass

def function2():
    '''Test function 2'''
    pass

class TestClass:
    '''Test class'''
    def method1(self):
        '''Test method 1'''
        pass

    def method2(self):
        '''Test method 2'''
        pass
"""
    file.write_text(content)
    return str(file)


@pytest.fixture(autouse=True)
def mock_send_completion(monkeypatch):
    mock_completion = MagicMock()
    mock_completion.usage.prompt_tokens = 100
    mock_completion.usage.completion_tokens = 50

    mock_chunk = MagicMock()                                                                                        
    mock_chunk.choices = [MagicMock()]                                                                              
    mock_chunk.choices[0].delta.content = "Test summary" 
    
    def mock_send(*args, **kwargs):
        return mock_completion, [mock_chunk]
    
    monkeypatch.setattr('aider.file_summary.send_completion', mock_send)
    return mock_send


class TestFileSummary:
    def test_initialization(self, mock_io, mock_model, mock_cache, test_file):
        summary = FileSummary(mock_io, mock_cache, mock_model, test_file)
        assert summary.fname == test_file
        assert summary.chunk_size == 800  # 80% of max_tokens
        assert summary.overlap == 200

    def test_has_changed(self, mock_io, mock_model, mock_cache, test_file):
        summary = FileSummary(mock_io, mock_cache, mock_model, test_file)

        # Initial state
        assert summary.has_changed()

        # After loading
        summary.get_summary()
        assert not summary.has_changed()

        # After modification
        time.sleep(0.1)  # Ensure mtime changes
        Path(test_file).write_text("modified content")
        assert summary.has_changed()

    def test_chunk_file(self, mock_io, mock_model, mock_cache, test_file):
        summary = FileSummary(mock_io, mock_cache, mock_model, test_file)
        content = Path(test_file).read_text()

        chunks = summary.chunk_file(content)
        assert len(chunks) > 0

        # Test that chunks preserve code structure
        for chunk in chunks:
            # No orphaned function/class definitions
            lines = chunk.splitlines()
            for i, line in enumerate(lines):
                if line.startswith(('def ', 'class ')):
                    # Check if this is the last line
                    if i < len(lines) - 1:
                        # Next line should be a docstring or indented code
                        next_line = lines[i + 1].strip()
                        assert next_line.startswith(("'''", '"""')) or lines[i + 1].startswith(' ')

    def test_cache_usage(self, mock_io, mock_model, mock_cache, test_file):
        summary = FileSummary(mock_io, mock_cache, mock_model, test_file)

        # Mock summarize to return a known value
        with patch.object(summary, 'summarize') as mock_summarize:
            mock_summarize.return_value = None
            summary.summary = "Test summary"
            summary.last_mtime = os.path.getmtime(test_file)
            summary.last_size = os.path.getsize(test_file)

            # Cache the summary
            mock_cache[test_file] = {
                "mtime": summary.last_mtime,
                "size": summary.last_size,
                "summary": summary.summary
            }

            # Create new instance and verify cache hit
            new_summary = FileSummary(mock_io, mock_cache, mock_model, test_file)
            assert new_summary.get_summary() == "Test summary"
            mock_summarize.assert_not_called()

    def test_interrupt_handling(self, mock_io, mock_model, mock_cache, test_file):
        summary = FileSummary(mock_io, mock_cache, mock_model, test_file)

        # Mock summarize_chunk to raise KeyboardInterrupt
        with patch.object(summary, 'summarize_chunk', side_effect=KeyboardInterrupt):
            with pytest.raises(KeyboardInterrupt):
                summary.summarize()
