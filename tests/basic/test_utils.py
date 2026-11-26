import os

from aider.utils import safe_abs_path, split_chat_history_markdown


def test_safe_abs_path_symlink_loop(tmp_path):
    # Create circular symlink: a -> b -> a
    link_a = tmp_path / "link_a"
    link_b = tmp_path / "link_b"
    link_a.symlink_to(link_b)
    link_b.symlink_to(link_a)

    # safe_abs_path must not raise, and must return an absolute path
    result = safe_abs_path(str(link_a))
    assert os.path.isabs(result)


def test_restore_chat_history_preserves_assistant_hash_lines():
    answer = "# Summary\n\n```python\n# Keep this comment\nprint(42)\n```\n"
    history = "# aider chat started at 2026-01-15 12:00:00\n#### Show an example\n" + answer

    assert split_chat_history_markdown(history) == [
        {"role": "user", "content": "Show an example\n"},
        {"role": "assistant", "content": answer},
    ]
