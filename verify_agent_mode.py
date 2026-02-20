#!/usr/bin/env python
"""
Simple verification script for agent mode integration.
This checks that the agent mode is properly registered without requiring full dependencies.
"""

import sys
import os

# Add aider to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("Agent Mode Integration Verification")
print("=" * 60)

try:
    # Test 1: Check that agent_coder.py exists and has correct syntax
    print("\n✓ Test 1: Checking agent_coder.py exists...")
    agent_coder_path = "aider/coders/agent_coder.py"
    assert os.path.exists(agent_coder_path), f"{agent_coder_path} not found"

    with open(agent_coder_path) as f:
        content = f.read()
        assert "class AgentCoder" in content, "AgentCoder class not found"
        assert 'edit_format = "agent"' in content, "edit_format not set correctly"
    print("  ✓ agent_coder.py exists and contains AgentCoder class")

    # Test 2: Check that agent_prompts.py exists
    print("\n✓ Test 2: Checking agent_prompts.py exists...")
    agent_prompts_path = "aider/coders/agent_prompts.py"
    assert os.path.exists(agent_prompts_path), f"{agent_prompts_path} not found"

    with open(agent_prompts_path) as f:
        content = f.read()
        assert "class AgentPrompts" in content, "AgentPrompts class not found"
    print("  ✓ agent_prompts.py exists and contains AgentPrompts class")

    # Test 3: Check that AgentCoder is registered in __init__.py
    print("\n✓ Test 3: Checking AgentCoder registration in __init__.py...")
    init_path = "aider/coders/__init__.py"
    with open(init_path) as f:
        content = f.read()
        assert "from .agent_coder import AgentCoder" in content, "AgentCoder not imported"
        assert "AgentCoder," in content, "AgentCoder not in __all__"
    print("  ✓ AgentCoder is properly registered in __init__.py")

    # Test 4: Check that /agent command exists in commands.py
    print("\n✓ Test 4: Checking /agent command in commands.py...")
    commands_path = "aider/commands.py"
    with open(commands_path) as f:
        content = f.read()
        assert "def cmd_agent" in content, "cmd_agent method not found"
        assert '"agent"' in content or "'agent'" in content, "agent mode not referenced"
    print("  ✓ /agent command is defined in commands.py")

    # Test 5: Check that agent mode is in chat mode list
    print("\n✓ Test 5: Checking agent mode in chat mode list...")
    with open(commands_path) as f:
        content = f.read()
        # Look for the show_formats section
        assert "Autonomous agent mode" in content or "autonomous agent" in content.lower(), \
            "Agent mode not in chat mode descriptions"
    print("  ✓ Agent mode is listed in chat modes")

    # Test 6: Check that tests exist
    print("\n✓ Test 6: Checking test_agent.py exists...")
    test_path = "tests/basic/test_agent.py"
    assert os.path.exists(test_path), f"{test_path} not found"

    with open(test_path) as f:
        content = f.read()
        assert "TestAgentCoder" in content, "TestAgentCoder class not found"
        assert "test_agent_coder_creation" in content, "Basic tests not found"
    print("  ✓ test_agent.py exists with test cases")

    # Test 7: Syntax check
    print("\n✓ Test 7: Running Python syntax check...")
    import py_compile
    py_compile.compile(agent_coder_path, doraise=True)
    py_compile.compile(agent_prompts_path, doraise=True)
    py_compile.compile(test_path, doraise=True)
    print("  ✓ All new files have valid Python syntax")

    print("\n" + "=" * 60)
    print("✅ All verification tests passed!")
    print("=" * 60)
    print("\nAgent mode features:")
    print("  • Autonomous file editing without confirmation")
    print("  • Automatic test running after edits")
    print("  • Iterative fixing of test failures")
    print("  • Configurable max iterations")
    print("\nUsage:")
    print("  /agent <prompt>           - Run a single request in agent mode")
    print("  /chat-mode agent          - Switch to agent mode")
    print("  /agent                    - Switch to agent mode")
    print("=" * 60)

    sys.exit(0)

except AssertionError as e:
    print(f"\n❌ Verification failed: {e}")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
