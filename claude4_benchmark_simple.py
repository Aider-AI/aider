#!/usr/bin/env python3
"""
Simple Claude 4 benchmark test that bypasses the complex benchmark harness
"""
import os
import sys
import time
import json
import tempfile
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def create_simple_exercise():
    """Create a simple coding exercise"""
    return {
        "name": "fizzbuzz",
        "description": "Write a function that prints numbers 1-15, but prints 'Fizz' for multiples of 3, 'Buzz' for multiples of 5, and 'FizzBuzz' for multiples of both.",
        "starter_code": "def fizzbuzz():\n    # TODO: Implement fizzbuzz\n    pass\n",
        "test_code": """
def test_fizzbuzz():
    import io
    import sys
    from contextlib import redirect_stdout
    
    f = io.StringIO()
    with redirect_stdout(f):
        fizzbuzz()
    output = f.getvalue().strip().split('\\n')
    
    expected = ['1', '2', 'Fizz', '4', 'Buzz', 'Fizz', '7', '8', 'Fizz', 'Buzz', '11', 'Fizz', '13', '14', 'FizzBuzz']
    assert output == expected, f"Expected {expected}, got {output}"
    print("✅ Test passed!")

if __name__ == "__main__":
    test_fizzbuzz()
"""
    }

def test_claude_model(model_name, exercise):
    """Test a Claude model with a simple exercise"""
    print(f"🧪 Testing {model_name}...")
    
    try:
        import litellm
        
        # Create the prompt
        prompt = f"""You are a coding assistant. Please implement the following function:

Description: {exercise['description']}

Starting code:
{exercise['starter_code']}

Please provide ONLY the complete function implementation as raw Python code. Do not wrap it in markdown code blocks or include any explanations."""

        start_time = time.time()
        
        response = litellm.completion(
            model=model_name,
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=500,
            temperature=0.1
        )
        
        duration = time.time() - start_time
        implementation = response.choices[0].message.content.strip()
        
        # Extract code from markdown if present
        if '```python' in implementation:
            start = implementation.find('```python') + 9
            end = implementation.find('```', start)
            if end != -1:
                implementation = implementation[start:end].strip()
        elif '```' in implementation:
            start = implementation.find('```') + 3
            end = implementation.find('```', start)
            if end != -1:
                implementation = implementation[start:end].strip()
        
        print(f"   ⏱️  Response time: {duration:.2f}s")
        print(f"   📝 Implementation received ({len(implementation)} chars)")
        print(f"   📄 Code preview: {implementation[:100]}...")
        
        # Create temp file and test the implementation
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(implementation + '\n\n' + exercise['test_code'])
            temp_file = f.name
        
        try:
            # Run the test
            import subprocess
            result = subprocess.run([sys.executable, temp_file], 
                                 capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print(f"   ✅ Test PASSED!")
                print(f"   📤 Output: {result.stdout.strip()}")
                return {"model": model_name, "passed": True, "duration": duration, "implementation": implementation}
            else:
                print(f"   ❌ Test FAILED")
                print(f"   📤 Error: {result.stderr.strip()}")
                return {"model": model_name, "passed": False, "duration": duration, "error": result.stderr}
                
        finally:
            os.unlink(temp_file)
            
    except Exception as e:
        print(f"   ❌ Model test failed: {str(e)}")
        return {"model": model_name, "passed": False, "error": str(e)}

def run_claude4_benchmark():
    """Run a simple Claude 4 benchmark"""
    print("🎯 Claude 4 Simple Benchmark")
    print("=" * 40)
    
    # Check API key
    if not os.getenv('ANTHROPIC_API_KEY'):
        print("❌ ANTHROPIC_API_KEY not found")
        return
    
    # Test models
    models_to_test = [
        "claude-sonnet-4-20250514",
        "claude-opus-4-20250514", 
        "claude-3-5-sonnet-20241022"  # For comparison
    ]
    
    exercise = create_simple_exercise()
    results = []
    
    for model in models_to_test:
        result = test_claude_model(model, exercise)
        results.append(result)
        print()
    
    # Summary
    print("📊 BENCHMARK RESULTS")
    print("=" * 30)
    for result in results:
        status = "✅ PASS" if result.get('passed') else "❌ FAIL"
        duration = result.get('duration', 0)
        print(f"{result['model']:<35} {status} ({duration:.2f}s)")
    
    passed_models = [r for r in results if r.get('passed')]
    print(f"\n🎉 {len(passed_models)}/{len(results)} models passed the test!")
    
    if passed_models:
        fastest = min(passed_models, key=lambda x: x.get('duration', float('inf')))
        print(f"🏆 Fastest: {fastest['model']} ({fastest['duration']:.2f}s)")

if __name__ == "__main__":
    run_claude4_benchmark()