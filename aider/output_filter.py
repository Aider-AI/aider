"""
Intelligent output filtering for /run and /test commands.

This module provides utilities to truncate and filter command output
before adding it to the chat context, preserving important error
information while reducing token usage.
"""

import re

# Common error patterns across different languages and test frameworks
ERROR_PATTERNS = [
    # Python
    r"^Traceback \(most recent call last\):",
    r"^\s*File \".*\", line \d+",
    r"^\w+Error:",
    r"^\w+Exception:",
    r"^AssertionError",
    r"^FAILED",
    r"^ERROR:",
    r"^E\s+",  # pytest error lines
    # Rust
    r"^error\[E\d+\]:",
    r"^error:",
    r"^thread .* panicked at",
    # Go
    r"^panic:",
    r"^--- FAIL:",
    r"^\s+.*_test\.go:\d+:",
    # JavaScript/TypeScript
    r"^\s+at\s+",  # stack trace
    r"^Error:",
    r"^\s*✕",  # Jest failure
    r"^FAIL\s+",
    # Java
    r"^\s+at\s+[\w.$]+\(.*:\d+\)",
    r"^java\.\w+\.\w+Exception:",
    r"^Caused by:",
    # Generic
    r"^FAILURE:",
    r"^FATAL:",
    r"^\[ERROR\]",
    r"^error:",
    r"^failed:",
]

# Patterns for lines that are usually noise
NOISE_PATTERNS = [
    r"^Collecting\s+",
    r"^Downloading\s+",
    r"^Installing\s+",
    r"^Using\s+cached\s+",
    r"^\s*\d+%\|",  # progress bars
    r"^={3,}$",  # separator lines (only equals signs)
    r"^-{3,}$",  # separator lines (only dashes)
    r"^\s*\.+$",  # dots only (progress)
    r"^Requirement already satisfied",
    r"^Successfully installed",
]

_error_re = re.compile("|".join(f"({p})" for p in ERROR_PATTERNS), re.MULTILINE)
_noise_re = re.compile("|".join(f"({p})" for p in NOISE_PATTERNS), re.MULTILINE)


def is_error_line(line):
    """Check if a line looks like an error or important diagnostic."""
    return bool(_error_re.search(line))


def is_noise_line(line):
    """Check if a line is likely noise (progress, download, etc.)."""
    return bool(_noise_re.search(line))


def truncate_output(output, max_lines=200, head_lines=50, tail_lines=100, max_error_lines=30):
    """
    Truncate command output while preserving important error information.

    Args:
        output: The raw command output string
        max_lines: Maximum lines before truncation kicks in
        head_lines: Number of lines to keep from the beginning
        tail_lines: Number of lines to keep from the end
        max_error_lines: Maximum error lines to extract from the middle

    Returns:
        tuple: (truncated_output, was_truncated)
    """
    if not output:
        return output, False

    lines = output.splitlines()
    total_lines = len(lines)

    if total_lines <= max_lines:
        return output, False

    # Keep head and tail
    head = lines[:head_lines]
    tail = lines[-tail_lines:]

    # Extract error lines from the middle section
    middle_start = head_lines
    middle_end = total_lines - tail_lines
    middle = lines[middle_start:middle_end]

    # Find error lines in the middle, with context
    # Use a set to track added line indices for O(1) lookup and avoid duplicates
    error_lines_with_context = []
    added_indices = set()
    i = 0
    while i < len(middle) and len(error_lines_with_context) < max_error_lines:
        if is_error_line(middle[i]) and not is_noise_line(middle[i]):
            # Add some context around the error (2 lines before, 3 lines after)
            start = max(0, i - 2)
            end = min(len(middle), i + 4)
            for j in range(start, end):
                if j not in added_indices:
                    added_indices.add(j)
                    error_lines_with_context.append(middle[j])
            i = end
        else:
            i += 1

    # Build the truncated output
    truncated_lines = head.copy()

    middle_truncated = len(middle)
    error_count = len(error_lines_with_context)

    if error_lines_with_context:
        truncated_lines.append("")
        truncated_lines.append(
            f"... [{middle_truncated} lines truncated, "
            f"{error_count} error-related lines extracted] ..."
        )
        truncated_lines.append("")
        truncated_lines.extend(error_lines_with_context)
        truncated_lines.append("")
        truncated_lines.append("... [end of extracted errors] ...")
        truncated_lines.append("")
    else:
        truncated_lines.append("")
        truncated_lines.append(f"... [{middle_truncated} lines truncated] ...")
        truncated_lines.append("")

    truncated_lines.extend(tail)

    return "\n".join(truncated_lines), True


def filter_output(output, max_lines=200):
    """
    Main entry point for output filtering.

    This function applies truncation and returns metadata about the operation.

    Args:
        output: Raw command output
        max_lines: Threshold for truncation

    Returns:
        dict with keys:
            - output: The (possibly truncated) output
            - truncated: Boolean indicating if truncation occurred
            - original_lines: Original line count
            - final_lines: Final line count
    """
    if not output:
        return {
            "output": output,
            "truncated": False,
            "original_lines": 0,
            "final_lines": 0,
        }

    original_lines = len(output.splitlines())
    filtered_output, was_truncated = truncate_output(output, max_lines=max_lines)
    final_lines = len(filtered_output.splitlines())

    return {
        "output": filtered_output,
        "truncated": was_truncated,
        "original_lines": original_lines,
        "final_lines": final_lines,
    }
