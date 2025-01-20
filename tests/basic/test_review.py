import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from aider.coders.review_coder import ReviewCoder, ReviewComment, FileChange
from aider.coders.review_prompts import ReviewPrompts

def test_parse_review():
    """Test parsing of review responses"""
    mock_io = Mock()
    coder = ReviewCoder(mock_io)
    
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
    coder = ReviewCoder(mock_io)
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

def test_review_prompts():
    """Test review prompt templates"""
    prompts = ReviewPrompts()
    
    assert "<summary>" in prompts.main_system
    assert "<comment" in prompts.main_system
    assert "<assessment>" in prompts.main_system
    assert "issue|suggestion|security|performance" in prompts.main_system

@pytest.mark.asyncio
async def test_review_pr_local():
    """Test reviewing local branch changes"""
    mock_io = Mock()
    mock_repo = Mock()
    mock_repo.root = "/fake/path"
    
    with patch('git.Repo') as mock_git:
        mock_git.return_value.git.diff.return_value = "M\ttest.py"
        mock_git.return_value.git.show.return_value = "old content"
        
        coder = ReviewCoder(mock_io)
        coder.io = mock_io
        coder.repo = mock_repo
        
        # Mock file reading
        def mock_read_text(filename):
            return "new content"
        mock_io.read_text = mock_read_text
        
        # Test local branch review
        coder.review_pr("main", "feature")
        
        # Verify git commands were called
        mock_git.return_value.git.diff.assert_called_once()
        mock_git.return_value.git.show.assert_called_once()
