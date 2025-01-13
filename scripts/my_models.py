#!/usr/bin/env python3

import json
from collections import defaultdict, deque
from pathlib import Path


def collect_model_stats(n_lines=1000):
    """Collect model usage statistics from the analytics file."""
    analytics_path = Path.home() / ".aider" / "analytics.jsonl"
    model_stats = defaultdict(int)

    with open(analytics_path) as f:
        lines = deque(f, n_lines)
        for line in lines:
            try:
                event = json.loads(line)
                if event["event"] == "message_send":
                    properties = event["properties"]
                    main_model = properties.get("main_model")

                    total_tokens = properties.get("total_tokens", 0)
                    if main_model == "deepseek/deepseek-coder":
                        main_model = "deepseek/deepseek-chat"
                    if main_model:
                        model_stats[main_model] += total_tokens
            except json.JSONDecodeError:
                continue

    return model_stats


def format_text_table(model_stats):
    """Format model statistics as a text table."""
    total_tokens = sum(model_stats.values())
    lines = []

    lines.append("\nModel Token Usage Summary:")
    lines.append("-" * 80)
    lines.append(f"{'Model Name':<40} {'Total Tokens':>15} {'Percent':>10}")
    lines.append("-" * 80)

    for model, tokens in sorted(model_stats.items(), key=lambda x: x[1], reverse=True):
        percentage = (tokens / total_tokens) * 100 if total_tokens > 0 else 0
        lines.append(f"{model:<40} {tokens:>15,} {percentage:>9.1f}%")

    lines.append("-" * 80)
    lines.append(f"{'TOTAL':<40} {total_tokens:>15,} {100:>9.1f}%")

    return "\n".join(lines)


def format_html_table(model_stats):
    """Format model statistics as an HTML table."""
    total_tokens = sum(model_stats.values())

    html = [
        "<style>",
        "table { border-collapse: collapse; width: 100%; }",
        "th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }",
        "th { background-color: #f2f2f2; }",
        "tr:hover { background-color: #f5f5f5; }",
        ".right { text-align: right; }",
        "</style>",
        "<table>",
        (
            "<tr><th>Model Name</th><th class='right'>Total Tokens</th><th"
            " class='right'>Percent</th></tr>"
        ),
    ]

    for model, tokens in sorted(model_stats.items(), key=lambda x: x[1], reverse=True):
        percentage = (tokens / total_tokens) * 100 if total_tokens > 0 else 0
        html.append(
            f"<tr><td>{model}</td>"
            f"<td class='right'>{tokens:,}</td>"
            f"<td class='right'>{percentage:.1f}%</td></tr>"
        )

    html.append("</table>")

    # Add note about redacted models if any are present
    if any("REDACTED" in model for model in model_stats.keys()):
        html.extend(
            [
                "",
                "{: .note :}",
                "Some models show as REDACTED, because they are new or unpopular models.",
                'Aider\'s analytics only records the names of "well known" LLMs.',
            ]
        )

    return "\n".join(html)


if __name__ == "__main__":
    stats = collect_model_stats()
    print(format_text_table(stats))
