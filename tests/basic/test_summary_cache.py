import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from aider.summary_cache import SummaryCache
from aider.file_summary import FileSummary

@pytest.fixture
def mock_io():
    return MagicMock()

@pytest.fixture
def mock_main():
    model = MagicMock()
    model.max_chat_history_tokens = 1000
    return model

@pytest.fixture
def test_files(tmp_path):
    # Create test files
    files = []
    for i in range(3):
        file = tmp_path / f"test{i}.py"
        file.write_text(f"# Test file {i}")
        files.append(str(file))
    return files

class TestSummaryCache:
    def test_initialization(self, tmp_path, mock_io, mock_main):
        root = str(tmp_path)
        cache = SummaryCache(mock_io, root, mock_main)
        
        # Check cache directory creation
        cache_dir = Path(root) / SummaryCache.CACHE_DIR
        assert cache_dir.exists()
        assert cache_dir.is_dir()

    def test_get_file_summary(self, tmp_path, mock_io, mock_main, test_files):
        cache = SummaryCache(mock_io, str(tmp_path), mock_main)
        
        # Test getting new summary
        summary = cache.get_file_summary(test_files[0])
        assert isinstance(cache.file_summaries[test_files[0]], FileSummary)
        
        # Test getting cached summary
        with patch.object(FileSummary, 'get_summary') as mock_get_summary:
            mock_get_summary.return_value = "Cached summary"
            summary = cache.get_file_summary(test_files[0])
            assert summary == "Cached summary"

    def test_has_file_summary(self, tmp_path, mock_io, mock_main, test_files):
        cache = SummaryCache(mock_io, str(tmp_path), mock_main)
        
        # Test with uncached file
        assert not cache.has_file_summary(test_files[0])
        
        # Test with cached file
        cache.get_file_summary(test_files[0])
        assert cache.has_file_summary(test_files[0])
        
        # Test with non-existent file
        assert not cache.has_file_summary("nonexistent.py")

    def test_clear(self, tmp_path, mock_io, mock_main, test_files):
        cache = SummaryCache(mock_io, str(tmp_path), mock_main)
        
        # Add some summaries
        for file in test_files:
            cache.get_file_summary(file)
        
        assert len(cache.file_summaries) == len(test_files)
        
        # Clear cache
        cache.clear()
        
        assert len(cache.file_summaries) == 0
        assert len(cache.cache) == 0

    def test_persistence(self, tmp_path, mock_io, mock_main, test_files):
        # Create first cache instance
        cache1 = SummaryCache(mock_io, str(tmp_path), mock_main)
        
        # Add a summary
        with patch.object(FileSummary, 'get_summary') as mock_get_summary:
            mock_get_summary.return_value = "Test summary"
            cache1.get_file_summary(test_files[0])
        
        # Create second cache instance
        cache2 = SummaryCache(mock_io, str(tmp_path), mock_main)
        
        # Verify the summary persisted
        assert cache2.has_file_summary(test_files[0])
