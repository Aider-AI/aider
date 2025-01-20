import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from aider.coders.review_coder import ReviewCoder, ReviewComment, FileChange
from aider.coders.review_prompts import ReviewPrompts

def test_parse_review():
    """Test parsing of review responses"""
    mock_io = Mock()
    mock_model = Mock()
    mock_model.extra_params = {}  # Mock extra_params as empty dict
    coder = ReviewCoder(mock_model, mock_io)
    
    review_text = """
    <summary>
    Added error handling and input validation
    </summary>
    <comment file="test.py" line="15" type="suggestion">
    Consider adding type hints to improve code clarity
    </comment>
    <comment file="main.py" line="42" type="security">
    Potential SQL injection vulnerability
    </comment>
    <assessment>
    Code changes look good overall but needs some minor improvements
    </assessment>
    """
    
    summary, comments, assessment = coder.parse_review(review_text)
    
    assert summary == "Added error handling and input validation"
    assert len(comments) == 2
    assert comments[0] == ReviewComment(
        file="test.py",
        line=15,
        type="suggestion",
        content="Consider adding type hints to improve code clarity"
    )
    assert comments[1] == ReviewComment(
        file="main.py",
        line=42,
        type="security",
        content="Potential SQL injection vulnerability"
    )
    assert assessment == "Code changes look good overall but needs some minor improvements"

def test_format_review_prompt():
    """Test formatting of review prompts"""
    mock_io = Mock()
    mock_model = Mock()
    coder = ReviewCoder(mock_model, mock_io)
    coder.fence = ('```', '```')
    
    changes = [
        FileChange(
            filename="test.py",
            old_content="def old_func():\n    pass",
            new_content="def new_func():\n    return True",
            change_type="modified"
        ),
        FileChange(
            filename="new.py",
            old_content=None,
            new_content="print('hello')",
            change_type="added"
        )
    ]
    
    prompt = coder.format_review_prompt(changes)
    
    assert "File: test.py" in prompt
    assert "Change type: modified" in prompt
    assert "def old_func():" in prompt
    assert "def new_func():" in prompt
    assert "File: new.py" in prompt
    assert "Change type: added" in prompt
    assert "print('hello')" in prompt

@pytest.mark.asyncio
async def test_review_pr_local():
    """Test reviewing local branch changes"""
    mock_io = Mock()
    mock_repo = Mock()
    mock_repo.root = "/fake/path"
    
    with patch('git.Repo') as mock_git:
        # Setup mock repo with active branch
        mock_git.return_value.active_branch.name = "feature"
        mock_git.return_value.git.diff.return_value = "M\ttest.py"
        mock_git.return_value.git.show.return_value = "old content"

        # Setup mock model and response
        mock_model = Mock()
        mock_model.name = "gpt-4"
        mock_model.extra_params = {}
        
        # Mock the completion response
        mock_response = Mock()
        mock_chunk = Mock()
        mock_chunk.choices = [Mock()]
        mock_chunk.choices[0].delta.content = "<summary>Test summary</summary>"
        mock_response.__iter__ = Mock(return_value=iter([mock_chunk]))

        coder = ReviewCoder(mock_model, mock_io)
        coder.io = mock_io
        coder.repo = mock_repo

        # Mock file reading
        def mock_read_text(filename):
            return "new content"
        mock_io.read_text = mock_read_text

        # Mock send_completion
        with patch('aider.coders.review_coder.send_completion', return_value=(None, mock_response)):
            # Test local branch review
            coder.review_pr("main", "feature")

        # Verify git commands were called
        mock_git.return_value.git.diff.assert_called_once_with("main...feature", "--name-status")
        mock_git.return_value.git.show.assert_called_once()
