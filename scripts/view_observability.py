"""
View Observability Metrics
Display statistics and recent metrics from local database
"""

import sys
from pathlib import Path

# Add aider to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'aider'))

from observability import get_tracer, get_metrics_store

def main():
    tracer = get_tracer()
    metrics_store = get_metrics_store()
    
    print("=" * 70)
    print("AIDER OBSERVABILITY METRICS")
    print("=" * 70)
    
    print(f"\nDatabase: {metrics_store.db_path}")
    print(f"Tracer enabled: {tracer.enabled}")
    print(f"LangSmith enabled: {tracer.langsmith_enabled}")
    
    # Overall statistics
    print("\n" + "-" * 70)
    print("STATISTICS (Last 24 Hours)")
    print("-" * 70)
    
    stats = tracer.get_statistics(hours=24)
    
    if stats['total_requests'] == 0:
        print("\nNo metrics recorded yet.")
        print("Run Aider with observability enabled to start collecting metrics.")
        return
    
    print(f"\nRequests:")
    print(f"  Total: {stats['total_requests']}")
    print(f"  Successful: {stats['successful_requests']}")
    print(f"  Failed: {stats['failed_requests']}")
    print(f"  Success Rate: {stats['success_rate']:.1f}%")
    
    print(f"\nTokens:")
    print(f"  Input: {stats['total_input_tokens']:,}")
    print(f"  Output: {stats['total_output_tokens']:,}")
    print(f"  Total: {stats['total_tokens']:,}")
    
    print(f"\nCost:")
    print(f"  Total: ${stats['total_cost_usd']:.4f}")
    print(f"  Average per request: ${stats['avg_cost_usd']:.4f}")
    
    print(f"\nLatency:")
    print(f"  Average: {stats['avg_latency_ms']:.2f}ms")
    print(f"  Min: {stats['min_latency_ms']:.2f}ms")
    print(f"  Max: {stats['max_latency_ms']:.2f}ms")
    
    # Model breakdown
    print("\n" + "-" * 70)
    print("MODEL BREAKDOWN")
    print("-" * 70)
    
    breakdown = tracer.get_model_breakdown(hours=24)
    for model_stat in breakdown:
        print(f"\n{model_stat['model']}:")
        print(f"  Requests: {model_stat['requests']}")
        print(f"  Tokens: {model_stat['tokens']:,}")
        print(f"  Cost: ${model_stat['cost_usd']:.4f}")
        print(f"  Avg Latency: {model_stat['avg_latency_ms']:.2f}ms")
    
    # Recent metrics
    print("\n" + "-" * 70)
    print("RECENT REQUESTS (Last 10)")
    print("-" * 70)
    
    recent = metrics_store.get_metrics(limit=10)
    for i, metric in enumerate(recent, 1):
        status = "✓" if metric.success else "✗"
        print(f"\n{i}. {status} [{metric.timestamp}]")
        print(f"   Model: {metric.model}")
        print(f"   Tokens: {metric.input_tokens} in, {metric.output_tokens} out ({metric.total_tokens} total)")
        print(f"   Cost: ${metric.cost_usd:.4f}")
        print(f"   Latency: {metric.latency_ms:.0f}ms")
        print(f"   Type: {metric.prompt_type}")
        if not metric.success:
            print(f"   Error: {metric.error_message}")
    
    print("\n" + "=" * 70)

if __name__ == '__main__':
    main()