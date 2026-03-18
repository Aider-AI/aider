"""
Test suite for observability module
"""

import pytest
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'aider'))

from observability import (
    ObservabilityTracer,
    CostCalculator,
    get_metrics_store
)


def test_cost_calculator():
    """Test cost calculation"""
    # Claude Sonnet 4
    cost = CostCalculator.calculate_cost("claude-sonnet-4", 1000, 500)
    assert 10.0 <= cost <= 11.0, f"Expected ~$10.50, got ${cost}"
    
    # GPT-4o
    cost = CostCalculator.calculate_cost("gpt-4o", 2000, 1000)
    assert 14.0 <= cost <= 16.0, f"Expected ~$15.00, got ${cost}"


def test_model_name_normalization():
    """Test model name normalization"""
    cost1 = CostCalculator.calculate_cost("anthropic/claude-sonnet-4", 1000, 500)
    cost2 = CostCalculator.calculate_cost("claude-sonnet-4", 1000, 500)
    assert cost1 == cost2, "Normalization failed"


def test_tracer_context():
    """Test tracer context manager"""
    tracer = ObservabilityTracer(enabled=True, langsmith_enabled=False)
    
    with tracer.trace_llm_call(
        model="claude-sonnet-4",
        prompt_type="test"
    ) as trace:
        time.sleep(0.05)  # Simulate 50ms latency
        
        trace.log_result(
            input_tokens=1000,
            output_tokens=500,
            success=True
        )
    
    # Verify trace was logged
    assert trace.logged
    assert trace.input_tokens == 1000
    assert trace.output_tokens == 500


def test_metrics_store():
    """Test metrics storage"""
    store = get_metrics_store()
    
    # Log a metric
    metric_id = store.log_metric(
        run_id="test-run-123",
        model="claude-sonnet-4",
        input_tokens=1000,
        output_tokens=500,
        cost_usd=10.5,
        latency_ms=200.0,
        success=True,
        prompt_type="test"
    )
    
    assert metric_id > 0
    
    # Retrieve metrics
    metrics = store.get_metrics(limit=1)
    assert len(metrics) >= 1
    assert metrics[0].model == "claude-sonnet-4"


def test_statistics():
    """Test statistics aggregation"""
    tracer = ObservabilityTracer(enabled=True, langsmith_enabled=False)
    
    # Log some metrics
    for i in range(3):
        with tracer.trace_llm_call(model="claude-sonnet-4") as trace:
            trace.log_result(
                input_tokens=1000 + i * 100,
                output_tokens=500 + i * 50,
                success=True
            )
    
    stats = tracer.get_statistics(hours=24)
    assert stats['total_requests'] >= 3
    assert stats['success_rate'] > 0


def test_model_breakdown():
    """Test model breakdown"""
    tracer = ObservabilityTracer(enabled=True, langsmith_enabled=False)
    
    breakdown = tracer.get_model_breakdown(hours=24)
    assert isinstance(breakdown, list)


def test_disabled_tracer():
    """Test that disabled tracer doesn't log"""
    tracer = ObservabilityTracer(enabled=False)
    
    with tracer.trace_llm_call(model="test") as trace:
        trace.log_result(
            input_tokens=1000,
            output_tokens=500,
            success=True
        )
    
    # Should not have logged anything
    assert not trace.enabled


if __name__ == '__main__':
    pytest.main([__file__, '-v'])