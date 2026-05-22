"""Test cost calculator"""

import sys
sys.path.insert(0, 'aider')

from observability.cost import CostCalculator

# Test 1: Claude Sonnet 4
cost = CostCalculator.calculate_cost("claude-sonnet-4", 1000, 500)
print(f"Test 1: Claude Sonnet 4 (1000 in, 500 out) = ${cost:.4f}")
assert 10.0 <= cost <= 11.0, f"Expected ~$10.50, got ${cost}"

# Test 2: GPT-4o
cost = CostCalculator.calculate_cost("gpt-4o", 2000, 1000)
print(f"Test 2: GPT-4o (2000 in, 1000 out) = ${cost:.4f}")
assert 14.0 <= cost <= 16.0, f"Expected ~$15.00, got ${cost}"

# Test 3: Model name normalization
cost1 = CostCalculator.calculate_cost("anthropic/claude-sonnet-4", 1000, 500)
cost2 = CostCalculator.calculate_cost("claude-sonnet-4", 1000, 500)
print(f"Test 3: Name normalization = ${cost1:.4f} vs ${cost2:.4f}")
assert cost1 == cost2, "Normalization failed"

# Test 4: Get pricing info
pricing = CostCalculator.get_model_pricing("claude-sonnet-4")
print(f"Test 4: Claude Sonnet 4 pricing = ${pricing.input_cost_per_1k}/1K in, ${pricing.output_cost_per_1k}/1K out")

# Test 5: Cost estimation
estimated = CostCalculator.estimate_cost("claude-sonnet-4", 1500)
print(f"Test 5: Estimated cost for 1500 tokens = ${estimated:.4f}")

print("\nAll cost calculator tests passed!")