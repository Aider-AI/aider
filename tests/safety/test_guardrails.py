"""
Tests for safety guardrails
"""

import pytest
import sys
import os

# Add aider directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'aider'))

from safety import check_code_safety, RiskLevel


def test_detect_os_system():
    """Test detection of os.system calls"""
    code = """
import os
os.system('rm -rf /')
"""
    result = check_code_safety(code)
    
    assert not result.is_safe
    assert result.requires_confirmation
    assert len(result.violations) >= 1
    assert result.risk_score > 0.5


def test_detect_subprocess():
    """Test detection of subprocess calls"""
    code = """
import subprocess
subprocess.call(['dangerous', 'command'])
"""
    result = check_code_safety(code)
    
    assert result.requires_confirmation
    assert any('subprocess' in v.rule.description.lower() for v in result.violations)


def test_detect_eval():
    """Test detection of eval()"""
    code = "result = eval(user_input)"
    
    result = check_code_safety(code)
    
    assert result.requires_confirmation
    assert 'eval' in result.message.lower()


def test_detect_hardcoded_password():
    """Test detection of hardcoded credentials"""
    code = """
password = "my_secret_password"
api_key = "sk-1234567890"
"""
    result = check_code_safety(code)
    
    assert len(result.violations) >= 2
    # Should warn but maybe not block
    assert 'credential' in result.message.lower() or 'password' in result.message.lower()


def test_safe_code():
    """Test that safe code passes"""
    code = """
def hello_world():
    print("Hello, world!")
    return 42
"""
    result = check_code_safety(code)
    
    assert result.is_safe
    assert len(result.violations) == 0
    assert result.risk_score == 0.0


def test_multiple_violations():
    """Test code with multiple issues"""
    code = """
import os
import subprocess

password = "hardcoded"
os.system('dangerous command')
subprocess.call(['rm', '-rf', '/'])
eval(user_input)
"""
    result = check_code_safety(code)
    
    assert not result.is_safe
    assert len(result.violations) >= 4
    assert result.risk_score > 0.7


if __name__ == '__main__':
    pytest.main([__file__, '-v'])