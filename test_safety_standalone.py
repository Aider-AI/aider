"""
Standalone test for safety guardrails
Tests the safety module without running full Aider
"""

import sys
import os

# Add aider directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'aider'))

from safety import check_code_safety, get_audit_logger

def test_dangerous_code():
    """Test that dangerous code is detected"""
    print("=" * 60)
    print("TEST 1: Detecting os.system()")
    print("=" * 60)
    
    dangerous_code = """
import os

def delete_files():
    os.system('rm -rf /')
"""
    
    result = check_code_safety(dangerous_code, filename="test.py")
    
    print(f"\n✅ Is Safe: {result.is_safe}")
    print(f"⚠️  Requires Confirmation: {result.requires_confirmation}")
    print(f"📊 Risk Score: {result.risk_score:.2f}")
    print(f"🚨 Violations Found: {len(result.violations)}")
    
    print(f"\n{result.message}")
    
    if result.requires_confirmation:
        print("\n✅ SUCCESS: Dangerous code was correctly flagged!")
    else:
        print("\n❌ FAILURE: Should have required confirmation")
    
    return result.requires_confirmation


def test_subprocess():
    """Test subprocess detection"""
    print("\n" + "=" * 60)
    print("TEST 2: Detecting subprocess.call()")
    print("=" * 60)
    
    code = """
import subprocess

def run_command():
    subprocess.call(['dangerous', 'command'])
"""
    
    result = check_code_safety(code)
    
    print(f"\n✅ Is Safe: {result.is_safe}")
    print(f"⚠️  Requires Confirmation: {result.requires_confirmation}")
    print(f"🚨 Violations: {len(result.violations)}")
    
    if result.violations:
        print("\n✅ SUCCESS: subprocess detected!")
    
    return len(result.violations) > 0


def test_hardcoded_credentials():
    """Test credential detection"""
    print("\n" + "=" * 60)
    print("TEST 3: Detecting hardcoded credentials")
    print("=" * 60)
    
    code = """
password = "my_secret_password"
api_key = "sk-1234567890"
secret_token = "very_secret"
"""
    
    result = check_code_safety(code)
    
    print(f"\n✅ Is Safe: {result.is_safe}")
    print(f"🚨 Violations: {len(result.violations)}")
    
    if result.violations:
        print("\nDetected:")
        for v in result.violations:
            print(f"  - Line {v.line_number}: {v.rule.description}")
        print("\n✅ SUCCESS: Credentials detected!")
    
    return len(result.violations) >= 2


def test_safe_code():
    """Test that safe code passes"""
    print("\n" + "=" * 60)
    print("TEST 4: Safe code should pass")
    print("=" * 60)
    
    safe_code = """
def hello_world():
    print("Hello, world!")
    return 42

def calculate(a, b):
    return a + b
"""
    
    result = check_code_safety(safe_code)
    
    print(f"\n✅ Is Safe: {result.is_safe}")
    print(f"🚨 Violations: {len(result.violations)}")
    print(f"📊 Risk Score: {result.risk_score:.2f}")
    
    if result.is_safe and len(result.violations) == 0:
        print("\n✅ SUCCESS: Safe code passed!")
    else:
        print("\n❌ FAILURE: Safe code shouldn't be flagged")
    
    return result.is_safe and len(result.violations) == 0


def test_eval_exec():
    """Test eval/exec detection"""
    print("\n" + "=" * 60)
    print("TEST 5: Detecting eval() and exec()")
    print("=" * 60)
    
    code = """
def dangerous():
    result = eval(user_input)
    exec(malicious_code)
"""
    
    result = check_code_safety(code)
    
    print(f"\n⚠️  Requires Confirmation: {result.requires_confirmation}")
    print(f"🚨 Violations: {len(result.violations)}")
    
    if len(result.violations) >= 2:
        print("\n✅ SUCCESS: Both eval() and exec() detected!")
    
    return len(result.violations) >= 2


def test_audit_logging():
    """Test audit logger"""
    print("\n" + "=" * 60)
    print("TEST 6: Audit Logging")
    print("=" * 60)
    
    logger = get_audit_logger()
    
    # Create a test result
    code = "os.system('test')"
    result = check_code_safety(code)
    
    # Log it
    log_id = logger.log_safety_check(
        result,
        filename="test.py",
        code_snippet=code,
        user_approved=False
    )
    
    print(f"\n✅ Logged to database with ID: {log_id}")
    
    # Get stats
    stats = logger.get_stats()
    print(f"\n📊 Audit Statistics:")
    print(f"  Total Checks: {stats['total_checks']}")
    print(f"  User Rejected: {stats['user_rejected']}")
    print(f"  Avg Risk Score: {stats['avg_risk_score']:.2f}")
    
    # Get recent
    recent = logger.get_recent_checks(limit=3)
    print(f"\n📋 Recent Checks: {len(recent)}")
    
    if log_id and stats['total_checks'] > 0:
        print("\n✅ SUCCESS: Audit logging works!")
        return True
    
    return False


def main():
    """Run all tests"""
    print("\n" + "🔒" * 30)
    print("TESTING AIDER SAFETY GUARDRAILS")
    print("🔒" * 30)
    
    results = []
    
    try:
        results.append(("Dangerous os.system()", test_dangerous_code()))
        results.append(("Subprocess detection", test_subprocess()))
        results.append(("Hardcoded credentials", test_hardcoded_credentials()))
        results.append(("Safe code passes", test_safe_code()))
        results.append(("eval/exec detection", test_eval_exec()))
        results.append(("Audit logging", test_audit_logging()))
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Your safety system is working!")
        print("\n✅ Database location: ~/.aider/safety_audit.db")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)