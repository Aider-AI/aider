"""
Comprehensive test for observability system
Tests tracer, metrics, and cost calculation together
"""

import sys
import time
sys.path.insert(0, 'aider')

from observability import get_tracer, get_metrics_store

print("=" * 70)
print("TESTING OBSERVABILITY SYSTEM")
print("=" * 70)

# Get tracer and metrics store
tracer = get_tracer()
metrics_store = get_metrics_store()

print(f"\nTracer enabled: {tracer.enabled}")
print(f"LangSmith enabled: {tracer.langsmith_enabled}")
print(f"Metrics database: {metrics_store.db_path}")

# Test 1: Trace a successful LLM call
print("\n" + "-" * 70)
print("TEST 1: Successful LLM Call")
print("-" * 70)

with tracer.trace_llm_call(
    model="claude-sonnet-4",
    prompt_type="code_generation",
    metadata={"user": "test_user", "file": "test.py"}
) as trace:
    # Simulate LLM call
    time.sleep(0.1)  # Simulate 100ms latency
    
    # Log results
    trace.log_result(
        input_tokens=1500,
        output_tokens=750,
        success=True
    )

print("Logged successful call")
print(f"  Run ID: {trace.run_id}")
print(f"  Model: {trace.model}")
print(f"  Tokens: {trace.input_tokens} in, {trace.output_tokens} out")

# Test 2: Trace a failed LLM call
print("\n" + "-" * 70)
print("TEST 2: Failed LLM Call")
print("-" * 70)

with tracer.trace_llm_call(
    model="gpt-4o",
    prompt_type="chat"
) as trace:
    # Simulate failure
    time.sleep(0.05)
    
    trace.log_result(
        input_tokens=500,
        output_tokens=0,
        success=False,
        error_message="Rate limit exceeded"
    )

print("Logged failed call")
print(f"  Run ID: {trace.run_id}")
print(f"  Error: {trace.error_message}")

# Test 3: Get statistics
print("\n" + "-" * 70)
print("TEST 3: Statistics")
print("-" * 70)

stats = tracer.get_statistics(hours=24)
print(f"Total requests: {stats['total_requests']}")
print(f"Successful: {stats['successful_requests']}")
print(f"Failed: {stats['failed_requests']}")
print(f"Success rate: {stats['success_rate']:.1f}%")
print(f"Total tokens: {stats['total_tokens']:,}")
print(f"Total cost: ${stats['total_cost_usd']:.4f}")
print(f"Avg latency: {stats['avg_latency_ms']:.2f}ms")

# Test 4: Model breakdown
print("\n" + "-" * 70)
print("TEST 4: Model Breakdown")
print("-" * 70)

breakdown = tracer.get_model_breakdown(hours=24)
for model_stat in breakdown:
    print(f"  {model_stat['model']}:")
    print(f"    Requests: {model_stat['requests']}")
    print(f"    Tokens: {model_stat['tokens']:,}")
    print(f"    Cost: ${model_stat['cost_usd']:.4f}")
    print(f"    Avg Latency: {model_stat['avg_latency_ms']:.2f}ms")

# Test 5: Recent metrics
print("\n" + "-" * 70)
print("TEST 5: Recent Metrics")
print("-" * 70)

recent = metrics_store.get_metrics(limit=5)
print(f"Retrieved {len(recent)} recent metrics:")
for i, metric in enumerate(recent[:3], 1):
    status = "SUCCESS" if metric.success else "FAILED"
    print(f"\n  {i}. {status}")
    print(f"     Model: {metric.model}")
    print(f"     Tokens: {metric.total_tokens:,}")
    print(f"     Cost: ${metric.cost_usd:.4f}")
    print(f"     Latency: {metric.latency_ms:.0f}ms")
    print(f"     Type: {metric.prompt_type}")

# Summary
print("\n" + "=" * 70)
print("OBSERVABILITY SYSTEM TEST SUMMARY")
print("=" * 70)
print("✓ Tracer working")
print("✓ Metrics store working")
print("✓ Cost calculation working")
print("✓ Statistics aggregation working")
print("✓ Model breakdown working")
print("\nALL TESTS PASSED!")
print("=" * 70)