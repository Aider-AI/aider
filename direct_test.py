"""
Direct test - imports from files directly
"""

import sys
import os

# Add path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'aider'))

# Try direct import
try:
    from safety.guardrails import check_code_safety
    print("✅ Successfully imported check_code_safety")
    
    # Test it
    code = "os.system('test')"
    result = check_code_safety(code)
    
    print(f"\n✅ Safety check works!")
    print(f"Requires confirmation: {result.requires_confirmation}")
    print(f"Violations: {len(result.violations)}")
    
    if result.requires_confirmation:
        print("\n🎉 SUCCESS! Safety system is working!")
    
except ImportError as e:
    print(f"❌ Import failed: {e}")
    print("\nThis means the files are empty or have syntax errors.")
    print("You need to paste the code into the files.")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()