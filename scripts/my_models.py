#!/usr/bin/env python3

import json
import os
from collections import defaultdict
from pathlib import Path

# Get the analytics file path
analytics_path = Path.home() / ".aider" / "analytics.jsonl"

# Dictionary to store model stats
model_stats = defaultdict(int)

# Read and process the file
with open(analytics_path) as f:
    for line in f:
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

# Print results
print("\nModel Token Usage Summary:")
print("-" * 60)
print(f"{'Model Name':<40} {'Total Tokens':>15}")
print("-" * 60)

for model, tokens in sorted(model_stats.items()):
    print(f"{model:<40} {tokens:>15,}")

print("-" * 60)
print(f"{'TOTAL':<40} {sum(model_stats.values()):>15,}")
