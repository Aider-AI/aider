#!/usr/bin/env python3

import json
from collections import defaultdict, deque
from pathlib import Path

# Get the analytics file path
analytics_path = Path.home() / ".aider" / "analytics.jsonl"

# Dictionary to store model stats
model_stats = defaultdict(int)

# Number of lines to process from the end
N = 1000

# Read and process the last N lines of the file
with open(analytics_path) as f:
    # Get last N lines using deque
    lines = deque(f, N)
    for line in lines:
        try:
            event = json.loads(line)
            # Check if this is a message_send event
            if event["event"] == "message_send":
                properties = event["properties"]
                main_model = properties.get("main_model")
                total_tokens = properties.get("total_tokens", 0)
                if main_model:
                    model_stats[main_model] += total_tokens
        except json.JSONDecodeError:
            continue

# Calculate total for percentages
total_tokens = sum(model_stats.values())

# Print results
print("\nModel Token Usage Summary:")
print("-" * 80)
print(f"{'Model Name':<40} {'Total Tokens':>15} {'Percent':>10}")
print("-" * 80)

for model, tokens in sorted(model_stats.items(), key=lambda x: x[1], reverse=True):
    percentage = (tokens / total_tokens) * 100 if total_tokens > 0 else 0
    print(f"{model:<40} {tokens:>15,} {percentage:>9.1f}%")

print("-" * 80)
print(f"{'TOTAL':<40} {total_tokens:>15,} {100:>9.1f}%")
