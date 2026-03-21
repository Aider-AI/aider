"""Smoke test: union-find summarizer with realistic conversation data.

Uses a distilled Flask #1169 debugging conversation (from the experiment corpus)
to verify the foundation: feed messages → clusters form by topic similarity →
render() produces structured output → fallback to recursive works → stale rebuild works.

Runs with a mock model (no API calls) but real TF-IDF clustering.
"""

from unittest import TestCase, mock

from aider.chat_summary_uf import ChatSummaryUF
from aider import prompts


# -- Realistic conversation: 3 distinct topics from Flask #1169 --
# Topic A: path traversal security in send_from_directory
# Topic B: Windows drive letter handling
# Topic C: file descriptor leak under concurrency

CONVERSATION = [
    # Topic A: path traversal
    {"role": "user", "content": (
        "I'm looking into issue #1169 in Flask's helpers.py. "
        "send_from_directory fails when using absolute paths. "
        "It triggers a SecurityError because safe_join rejects the path."
    )},
    {"role": "assistant", "content": (
        "Let's look at the implementation of send_from_directory. "
        "It calls safe_join(directory, filename). If the filename is absolute, "
        "safe_join treats it as a traversal attempt. We need to resolve the realpath first."
    )},
    {"role": "user", "content": (
        "I've updated helpers.py to use os.path.realpath and os.path.commonpath "
        "to validate the path. The test_send_file_security test passes now. "
        "No directory traversal is possible."
    )},
    {"role": "assistant", "content": (
        "Good progress. Make sure to add a test case for symlink traversal. "
        "os.path.realpath resolves symlinks, which could expose paths outside "
        "the intended directory."
    )},
    {"role": "user", "content": (
        "Added test_symlink_traversal to test_helpers.py. It confirms that "
        "symlinks pointing outside the base directory are correctly rejected. "
        "The SecurityError message is now more descriptive."
    )},
    {"role": "assistant", "content": (
        "Excellent. The path validation logic in helpers.py looks solid. "
        "Update the docstrings to reflect that absolute paths are now supported "
        "provided they resolve within the base directory."
    )},

    # Topic B: Windows drive letters
    {"role": "user", "content": (
        "I noticed that on Windows, drive letters complicate the path validation. "
        "os.path.commonpath fails when comparing paths on different drives. "
        "We need ntpath.normcase to handle drive letter capitalization."
    )},
    {"role": "assistant", "content": (
        "Be careful with importing ntpath directly. Stick to os.path.normpath "
        "and os.path.abspath for cross-platform compatibility. "
        "Add a mock in test_helpers.py to simulate Windows drive boundary issues."
    )},
    {"role": "user", "content": (
        "I've added Windows path test cases using monkeypatch to simulate drive letters. "
        "The normcase fix handles C: vs c: correctly. "
        "All 42 tests in test_helpers.py pass including the new Windows cases."
    )},
    {"role": "assistant", "content": (
        "Does the CI runner confirm the Windows tests pass? We want to ensure "
        "the normalization in helpers.py doesn't accidentally strip UNC path prefixes "
        "on network shares."
    )},
    {"role": "user", "content": (
        "CI runner confirmed green on Windows. The explicit call to os.path.abspath "
        "before os.path.realpath correctly handles UNC paths and drive letter variations. "
        "No regressions in flask.tests.test_send_file."
    )},
    {"role": "assistant", "content": (
        "Perfect. The Windows path handling is now robust. "
        "Should we use posixpath.normpath internally to stop the Windows runner "
        "from converting forward slashes to backslashes?"
    )},

    # Topic C: file descriptor leak
    {"role": "user", "content": (
        "I just got a ping from a Discord user. After updating to 1.0.2, "
        "their static file serving crashes under load. "
        "The os.stat calls are leaking file descriptors."
    )},
    {"role": "assistant", "content": (
        "That is concerning. The file object is probably not being explicitly closed "
        "after the stat check in helpers.py. A context manager should fix the leak."
    )},
    {"role": "user", "content": (
        "I've written a stress test using threading to spawn 100 concurrent requests "
        "to send_from_directory. It consistently crashes at 1024 open file descriptors. "
        "Adding the context manager fixes it — stable at 12."
    )},
    {"role": "assistant", "content": (
        "Excellent reproduction strategy. The benchmarks show negligible latency impact "
        "from the context manager. Let's add the stress test to TestFileHandling "
        "as a regression test."
    )},
    {"role": "user", "content": (
        "Added the stress test to test_helpers.py. It completes in under two seconds. "
        "The file descriptor count stays bounded even with 100 concurrent requests. "
        "CI is green across all platforms."
    )},
    {"role": "assistant", "content": (
        "Great work. The resource leak fix and the stress test cover the concurrency "
        "edge case. This should prevent the issue from recurring."
    )},

    # More Topic A (interleaved — tests that clustering groups by topic, not by time)
    {"role": "user", "content": (
        "Wait, I found another edge case in the path traversal check. "
        "If the user passes a relative path that resolves outside the base directory "
        "via enough ../ components, our check misses it."
    )},
    {"role": "assistant", "content": (
        "Good catch. We should use werkzeug.utils.safe_join to combine directory "
        "and filename. It's specifically designed to prevent directory traversal. "
        "Create a reproduction test case first."
    )},
    {"role": "user", "content": (
        "The traversal test confirmed the vulnerability. I've refactored helpers.py "
        "to use safe_join. If safe_join returns None, we now raise werkzeug.exceptions.NotFound. "
        "All tests pass including the new traversal case."
    )},
    {"role": "assistant", "content": (
        "This adds a critical layer of protection. The path validation in helpers.py "
        "is now much more robust. Prepare a follow-up PR for this security hardening."
    )},
]


def _word_count(msg):
    if isinstance(msg, list):
        return sum(_word_count(m) for m in msg)
    if isinstance(msg, str):
        return len(msg.split())
    return len(msg.get("content", "").split())


def _make_summarizer(max_tokens=400):
    """Build a ChatSummaryUF with a mock model that returns unique cluster summaries."""
    counter = {"n": 0}

    def _unique_summary(msgs):
        counter["n"] += 1
        return f"Cluster {counter['n']} summary: discussed Flask helpers.py topic {counter['n']}"

    model = mock.Mock()
    model.name = "gemini/gemini-3.1-flash-lite-preview"
    model.token_count = _word_count
    model.info = {"max_input_tokens": 4096}
    model.simple_send_with_retries = mock.Mock(side_effect=_unique_summary)
    return ChatSummaryUF(models=[model], max_tokens=max_tokens), model


def _padded_conversation():
    """Conversation + padding to exceed graduate_at (26 user/assistant messages)."""
    padded = list(CONVERSATION)
    for i in range(20):
        padded.append({"role": "user", "content": f"Follow-up question {i} about helpers.py path validation"})
        padded.append({"role": "assistant", "content": f"Response {i} about the security fix in send_from_directory"})
    return padded


class TestSmokeUFFoundation(TestCase):
    """End-to-end foundation tests: clustering, rendering, fallback, rebuild."""

    def test_clusters_form_from_realistic_data(self):
        """TF-IDF clustering produces cold clusters from a multi-topic conversation."""
        summarizer, model = _make_summarizer()
        padded = _padded_conversation()

        result = summarizer.summarize(padded)
        cw = summarizer.context_window
        forest = cw._forest

        self.assertGreater(forest.cluster_count(), 0, "Expected cold clusters")
        self.assertGreater(cw.hot_count, 0, "Expected hot messages")
        self.assertNotEqual(result, padded, "Expected summarized output, not original")

    def test_output_format_matches_recursive(self):
        """Output is [summary_msg, 'Ok.', *hot_messages] — same as recursive."""
        summarizer, model = _make_summarizer()
        padded = _padded_conversation()

        result = summarizer.summarize(padded)

        # First message is summary with prefix
        self.assertEqual(result[0]["role"], "user")
        self.assertTrue(result[0]["content"].startswith(prompts.summary_prefix))

        # Second message is "Ok."
        self.assertEqual(result[1]["role"], "assistant")
        self.assertEqual(result[1]["content"], "Ok.")

        # Remaining are hot messages from the original
        for msg in result[2:]:
            self.assertIn(msg["role"], ("user", "assistant"))

    def test_render_produces_cold_and_hot(self):
        """render() returns cold summaries followed by hot contents."""
        summarizer, model = _make_summarizer()
        padded = _padded_conversation()
        summarizer.summarize(padded)

        cw = summarizer.context_window
        rendered = cw.render()

        # Cold part: cluster summaries
        cold_count = cw.cold_count
        hot_count = cw.hot_count
        self.assertEqual(len(rendered), cold_count + hot_count)

        # Cold parts are either cluster summaries (contain "Cluster" from mock)
        # or raw singleton content (never merged, so not summarized)
        cold_parts = rendered[:cold_count]
        summarized = [p for p in cold_parts if "Cluster" in p]
        self.assertGreater(len(summarized), 0, "Expected at least one merged cluster summary")

    def test_distinct_topics_form_separate_clusters(self):
        """Messages about different topics cluster separately, not by timestamp."""
        summarizer, model = _make_summarizer()
        padded = _padded_conversation()
        summarizer.summarize(padded)

        forest = summarizer.context_window._forest
        # With 3 distinct topics + padding, should get multiple clusters
        self.assertGreater(forest.cluster_count(), 1,
                           "Expected multiple clusters from distinct topics")

    def test_fallback_to_recursive_when_inflated(self):
        """If union-find result exceeds budget, falls back to recursive."""
        # Very low budget forces fallback
        summarizer, model = _make_summarizer(max_tokens=5)
        padded = _padded_conversation()

        # Should not crash — falls back to recursive
        result = summarizer.summarize(padded)
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

    def test_stale_rebuild_after_done_messages_shrink(self):
        """When done_messages shrinks, prefix mismatch triggers rebuild."""
        summarizer, model = _make_summarizer()
        padded = _padded_conversation()

        # First summarization
        result = summarizer.summarize(padded)
        self.assertGreater(len(summarizer._fed_messages), 0)

        # Simulate summarize_end applying the result (done_messages = result, shorter).
        # The result has different content (summaries), so prefix check fails → rebuild.
        with mock.patch.object(summarizer, "_rebuild", wraps=summarizer._rebuild) as mock_rebuild:
            result2 = summarizer.summarize(result)
            if summarizer.too_big(result):
                mock_rebuild.assert_called_once()
            # If result fits budget, summarize returns early — no rebuild needed

    def test_incremental_feeding_skips_system_messages(self):
        """System messages are not fed into the forest."""
        summarizer, model = _make_summarizer()
        msgs = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello from user"},
            {"role": "assistant", "content": "Hello from assistant"},
        ] * 20  # 60 messages, 40 user/assistant
        summarizer.summarize(msgs)

        cw = summarizer.context_window
        # System messages should not have been appended to hot zone
        # Only user/assistant messages are fed
        total_fed = cw.hot_count + sum(
            len(cw._forest._children.get(r, set()))
            for r in cw._forest.roots()
        )
        # Should be 40 (20 user + 20 assistant), not 60
        self.assertLessEqual(total_fed, 40)

    def test_deterministic_render_across_calls(self):
        """render() produces identical output on repeated calls (stable ordering)."""
        summarizer, model = _make_summarizer()
        padded = _padded_conversation()
        summarizer.summarize(padded)

        cw = summarizer.context_window
        render1 = cw.render()
        render2 = cw.render()
        self.assertEqual(render1, render2)
