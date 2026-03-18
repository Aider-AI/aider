"""Cluster summarizer wrapping aider's model API.

Takes a list of text fragments (previous summary + new inputs) and produces
a single summary via model.simple_send_with_retries(). Cascades through
models on failure.
"""

CLUSTER_SUMMARIZE_PROMPT = """\
Summarize the following conversation fragments into a single coherent summary.
If a previous summary is included, integrate the new information into it.

Preserve:
- File paths and filenames
- Function and class names
- Library and package names
- Error messages and stack traces
- Key decisions and their rationale

Write in first person as the user ("I asked you...").
Do NOT include fenced code blocks in the summary.
Be concise but preserve all technical details."""


class ClusterSummarizer:
    """Wraps aider's model API for per-cluster summarization."""

    def __init__(self, models):
        self.models = models if isinstance(models, list) else [models]

    def summarize(self, texts):
        """Summarize a list of text fragments into a single summary.

        Args:
            texts: List of strings (previous summary and/or raw content).

        Returns:
            Summary string.

        Raises:
            ValueError: If all models fail.
        """
        content = "\n\n---\n\n".join(texts)
        messages = [
            {"role": "system", "content": CLUSTER_SUMMARIZE_PROMPT},
            {"role": "user", "content": content},
        ]

        for model in self.models:
            try:
                result = model.simple_send_with_retries(messages)
                if result is not None:
                    return result
            except Exception:
                continue

        raise ValueError("cluster summarizer unexpectedly failed for all models")
