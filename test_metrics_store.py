"""Test metrics store"""

import sys
import uuid
sys.path.insert(0, 'aider')

from observability.metrics import MetricsStore

print("=" * 60)
print("TESTING METRICS STORE")
print("=" * 60)

# Create store
store = MetricsStore()
print(f"\nDatabase location: {store.db_path}")

# Test 1: Log metrics
print("\nTest 1: Logging metrics...")
for i in range(5):
    run_id = str(uuid.uuid4())
    metric_id = store.log_metric(
        run_id=run_id,
        model="claude-sonnet-4",
        input_tokens=1000 + i * 100,
        output_tokens=500 + i * 50,
        cost_usd=10.5 + i,
        latency_ms=200.0 + i * 10,
        success=True,
        prompt_type="code_generation"
    )
    print(f"  Logged metric {i+1} with ID: {metric_id}")

# Test 2: Get recent metrics
print("\nTest 2: Retrieving metrics...")
metrics = store.get_metrics(limit=5)
print(f"  Retrieved {len(metrics)} metrics")
for m in metrics[:2]:
    print(f"  - {m.model}: {m.total_tokens} tokens, ${m.cost_usd:.4f}, {m.latency_ms:.0f}ms")

# Test 3: Get statistics
print("\nTest 3: Statistics...")
stats = store.get_statistics(hours=24)
print(f"  Total requests: {stats['total_requests']}")
print(f"  Success rate: {stats['success_rate']:.1f}%")
print(f"  Total cost: ${stats['total_cost_usd']:.4f}")
print(f"  Avg latency: {stats['avg_latency_ms']:.2f}ms")

# Test 4: Model breakdown
print("\nTest 4: Model breakdown...")
breakdown = store.get_model_breakdown(hours=24)
for model_stat in breakdown:
    print(f"  {model_stat['model']}: {model_stat['requests']} requests, ${model_stat['cost_usd']:.4f}")

print("\n" + "=" * 60)
print("ALL METRICS TESTS PASSED")
print("=" * 60)