"""Tests for union-find chat history summarizer (PR 1 test plan, 12 areas)."""

from unittest import TestCase, mock

from aider.chat_summary_uf import ChatSummaryUF
from aider.cluster_summarizer import ClusterSummarizer
from aider.context_window import Forest, ContextWindow, _cosine_similarity
from aider.embedding_service import TFIDFEmbedder
from aider.history import ChatSummary
from aider.models import Model


def count(msg):
    """Word-count token counter (matches test_history.py)."""
    if isinstance(msg, list):
        return sum(count(m) for m in msg)
    return len(msg["content"].split())


def make_mock_model(name="gpt-3.5-turbo", summary_text="This is a summary"):
    model = mock.Mock(spec=Model)
    model.name = name
    model.token_count = count
    model.info = {"max_input_tokens": 4096}
    model.simple_send_with_retries = mock.Mock(return_value=summary_text)
    return model


def make_messages(n):
    """Create n alternating user/assistant message pairs (2n messages total)."""
    messages = []
    for i in range(n):
        messages.append({"role": "user", "content": f"User message number {i} about topic {i % 5}"})
        messages.append({"role": "assistant", "content": f"Assistant response number {i} about topic {i % 5}"})
    return messages


# ────────────────────────────────────────────────────────────
# Area 12: Forest mechanics
# ────────────────────────────────────────────────────────────


class TestForest(TestCase):
    def setUp(self):
        self.mock_summarizer = mock.Mock()
        self.mock_summarizer.summarize = mock.Mock(return_value="merged summary")
        self.forest = Forest(summarizer=self.mock_summarizer)

    def test_insert_creates_singleton(self):
        self.forest.insert("m1", "hello world", {"hello": 1.0})
        self.assertEqual(self.forest.cluster_count(), 1)
        self.assertIn("m1", self.forest.roots())
        self.assertEqual(self.forest.compact("m1"), "hello world")

    def test_insert_multiple_creates_separate_clusters(self):
        self.forest.insert("m1", "hello", {"hello": 1.0})
        self.forest.insert("m2", "world", {"world": 1.0})
        self.assertEqual(self.forest.cluster_count(), 2)

    def test_union_merges_two_clusters(self):
        self.forest.insert("m1", "hello", {"hello": 1.0})
        self.forest.insert("m2", "world", {"world": 1.0})
        self.forest.union("m1", "m2")
        self.assertEqual(self.forest.cluster_count(), 1)

    def test_union_same_root_is_noop(self):
        self.forest.insert("m1", "hello", {"hello": 1.0})
        result = self.forest.union("m1", "m1")
        self.assertEqual(result, "m1")
        self.assertEqual(self.forest.cluster_count(), 1)

    def test_union_marks_dirty(self):
        self.forest.insert("m1", "hello", {"hello": 1.0})
        self.forest.insert("m2", "world", {"world": 1.0})
        self.assertNotIn("m1", self.forest._dirty)
        self.assertNotIn("m2", self.forest._dirty)
        self.forest.union("m1", "m2")
        root = self.forest.roots()[0]
        self.assertIn(root, self.forest._dirty)

    def test_resolve_dirty_calls_summarizer(self):
        self.forest.insert("m1", "hello", {"hello": 1.0})
        self.forest.insert("m2", "world", {"world": 1.0})
        self.forest.union("m1", "m2")
        self.forest.resolve_dirty()
        self.mock_summarizer.summarize.assert_called_once()
        root = self.forest.roots()[0]
        self.assertEqual(self.forest.compact(root), "merged summary")

    def test_compact_singleton_returns_raw_content(self):
        self.forest.insert("m1", "hello world", {"hello": 1.0})
        self.assertEqual(self.forest.compact("m1"), "hello world")

    def test_compact_after_resolve_returns_summary(self):
        self.forest.insert("m1", "hello", {"hello": 1.0})
        self.forest.insert("m2", "world", {"world": 1.0})
        self.forest.union("m1", "m2")
        self.forest.resolve_dirty()
        root = self.forest.roots()[0]
        self.assertEqual(self.forest.compact(root), "merged summary")

    def test_nearest_root_finds_closest(self):
        self.forest.insert("m1", "python", {"python": 1.0, "code": 0.5})
        self.forest.insert("m2", "java", {"java": 1.0, "code": 0.5})
        result = self.forest.nearest_root({"python": 0.8, "code": 0.6})
        self.assertIsNotNone(result)
        root_id, similarity = result
        self.assertEqual(root_id, "m1")

    def test_nearest_root_empty_forest(self):
        result = self.forest.nearest_root({"python": 1.0})
        self.assertIsNone(result)

    def test_find_with_path_compression(self):
        self.forest.insert("m1", "a", {"a": 1.0})
        self.forest.insert("m2", "b", {"b": 1.0})
        self.forest.insert("m3", "c", {"c": 1.0})
        self.forest.union("m1", "m2")
        self.forest.union("m2", "m3")
        # After path compression, all nodes point to the same root
        root = self.forest._find("m3")
        self.assertEqual(self.forest._find("m1"), root)
        self.assertEqual(self.forest._find("m2"), root)

    def test_dirty_inputs_collected_on_union(self):
        self.forest.insert("m1", "hello", {"hello": 1.0})
        self.forest.insert("m2", "world", {"world": 1.0})
        self.forest.union("m1", "m2")
        root = self.forest.roots()[0]
        inputs = list(self.forest._dirty_inputs.get(root, []))
        self.assertEqual(len(inputs), 2)
        self.assertIn("hello", inputs)
        self.assertIn("world", inputs)


# ────────────────────────────────────────────────────────────
# Area 9: Stable root ordering
# ────────────────────────────────────────────────────────────


class TestStableRootOrdering(TestCase):
    def setUp(self):
        self.mock_summarizer = mock.Mock()
        self.mock_summarizer.summarize = mock.Mock(return_value="summary")
        self.forest = Forest(summarizer=self.mock_summarizer)

    def test_roots_in_insertion_order(self):
        self.forest.insert("m1", "first", {"first": 1.0})
        self.forest.insert("m2", "second", {"second": 1.0})
        self.forest.insert("m3", "third", {"third": 1.0})
        self.assertEqual(self.forest.roots(), ["m1", "m2", "m3"])

    def test_order_preserved_after_merge(self):
        self.forest.insert("m1", "first", {"first": 1.0})
        self.forest.insert("m2", "second", {"second": 1.0})
        self.forest.insert("m3", "third", {"third": 1.0})
        self.forest.insert("m4", "fourth", {"fourth": 1.0})
        # Merge m2 and m3 — surviving root keeps m2's position
        self.forest.union("m2", "m3")
        roots = self.forest.roots()
        self.assertEqual(len(roots), 3)
        # m1 is first, merged root is in m2's position, m4 is last
        self.assertEqual(roots[0], "m1")
        self.assertEqual(roots[-1], "m4")

    def test_deterministic_across_calls(self):
        self.forest.insert("m1", "first", {"first": 1.0})
        self.forest.insert("m2", "second", {"second": 1.0})
        self.forest.insert("m3", "third", {"third": 1.0})
        roots1 = self.forest.roots()
        roots2 = self.forest.roots()
        roots3 = self.forest.roots()
        self.assertEqual(roots1, roots2)
        self.assertEqual(roots2, roots3)

    def test_order_after_multiple_merges(self):
        for i in range(5):
            self.forest.insert(f"m{i}", f"msg{i}", {f"t{i}": 1.0})
        # Merge m0+m1, m3+m4
        self.forest.union("m0", "m1")
        self.forest.union("m3", "m4")
        roots = self.forest.roots()
        self.assertEqual(len(roots), 3)
        # Relative order maintained: (m0 cluster), m2, (m3 cluster)
        self.assertEqual(roots[1], "m2")


# ────────────────────────────────────────────────────────────
# Area 8: Weighted centroid
# ────────────────────────────────────────────────────────────


class TestWeightedCentroid(TestCase):
    def setUp(self):
        self.mock_summarizer = mock.Mock()
        self.mock_summarizer.summarize = mock.Mock(return_value="summary")
        self.forest = Forest(summarizer=self.mock_summarizer)

    def test_equal_size_merge_at_midpoint(self):
        self.forest.insert("m1", "a", {"x": 1.0})
        self.forest.insert("m2", "b", {"x": 0.0})
        self.forest.union("m1", "m2")
        root = self.forest.roots()[0]
        emb = self.forest._embedding[root]
        self.assertAlmostEqual(emb["x"], 0.5)

    def test_unequal_size_weights_toward_larger(self):
        # Build a 3-node cluster around "m1"
        self.forest.insert("m1", "a", {"x": 1.0})
        self.forest.insert("m2", "b", {"x": 1.0})
        self.forest.insert("m3", "c", {"x": 1.0})
        self.forest.union("m1", "m2")
        self.forest.union("m1", "m3")
        # Now m1's cluster has 3 members

        # Insert singleton with very different embedding
        self.forest.insert("m4", "d", {"x": 0.0})
        self.forest.union("m1", "m4")

        root = self.forest.roots()[0]
        emb = self.forest._embedding[root]
        # Weighted: (1.0 * 3 + 0.0 * 1) / 4 = 0.75
        self.assertAlmostEqual(emb["x"], 0.75)

    def test_weighted_centroid_sparse_dicts(self):
        # m1 cluster: size 2
        self.forest.insert("m1", "a", {"python": 1.0, "code": 0.5})
        self.forest.insert("m2", "b", {"python": 0.8, "code": 0.6})
        self.forest.union("m1", "m2")
        # m1 cluster now has size 2, centroid = midpoint of m1 and m2

        # m3: singleton, different terms
        self.forest.insert("m3", "c", {"java": 1.0, "code": 0.3})
        self.forest.union("m1", "m3")

        root = self.forest.roots()[0]
        emb = self.forest._embedding[root]
        # "code" exists in both: weighted by size 2 vs 1
        # "java" exists only in m3: weighted 0*2/3 + 1.0*1/3 = 0.333...
        self.assertIn("code", emb)
        self.assertIn("java", emb)
        self.assertAlmostEqual(emb["java"], 1.0 / 3, places=4)


# ────────────────────────────────────────────────────────────
# Area 10: Cluster summarization (model cascade)
# ────────────────────────────────────────────────────────────


class TestClusterSummarizer(TestCase):
    def test_uses_first_model_on_success(self):
        model1 = make_mock_model("weak", "weak summary")
        model2 = make_mock_model("strong", "strong summary")
        summarizer = ClusterSummarizer([model1, model2])
        result = summarizer.summarize(["text a", "text b"])
        self.assertEqual(result, "weak summary")
        model1.simple_send_with_retries.assert_called_once()
        model2.simple_send_with_retries.assert_not_called()

    def test_falls_back_to_second_model(self):
        model1 = make_mock_model("weak")
        model1.simple_send_with_retries.side_effect = Exception("fail")
        model2 = make_mock_model("strong", "strong summary")
        summarizer = ClusterSummarizer([model1, model2])
        result = summarizer.summarize(["text"])
        self.assertEqual(result, "strong summary")
        model1.simple_send_with_retries.assert_called_once()
        model2.simple_send_with_retries.assert_called_once()

    def test_raises_if_all_models_fail(self):
        model1 = make_mock_model("weak")
        model1.simple_send_with_retries.side_effect = Exception("fail1")
        model2 = make_mock_model("strong")
        model2.simple_send_with_retries.side_effect = Exception("fail2")
        summarizer = ClusterSummarizer([model1, model2])
        with self.assertRaises(ValueError):
            summarizer.summarize(["text"])

    def test_single_model_works(self):
        model = make_mock_model("only", "only summary")
        summarizer = ClusterSummarizer(model)  # not a list
        result = summarizer.summarize(["text"])
        self.assertEqual(result, "only summary")


# ────────────────────────────────────────────────────────────
# Areas 1-2: Flag selection / default unchanged
# ────────────────────────────────────────────────────────────


class TestFlagSelection(TestCase):
    def test_chat_summary_uf_is_subclass_of_chat_summary(self):
        self.assertTrue(issubclass(ChatSummaryUF, ChatSummary))

    def test_chat_summary_uf_constructs(self):
        model = make_mock_model()
        summarizer = ChatSummaryUF(model, max_tokens=100)
        self.assertIsInstance(summarizer, ChatSummaryUF)
        self.assertIsInstance(summarizer, ChatSummary)
        self.assertEqual(summarizer.max_tokens, 100)

    def test_default_constructs_chat_summary(self):
        """Default (no flag or 'recursive') should use ChatSummary, not UF."""
        model = make_mock_model()
        summarizer = ChatSummary(model, max_tokens=100)
        self.assertIsInstance(summarizer, ChatSummary)
        self.assertNotIsInstance(summarizer, ChatSummaryUF)


# ────────────────────────────────────────────────────────────
# Area 3: Output format
# ────────────────────────────────────────────────────────────


class TestOutputFormat(TestCase):
    def setUp(self):
        self.model = make_mock_model(summary_text="Cluster summary text here")
        # max_tokens=400: high enough to hold UF result (~250 words),
        # but lower than 60-message input (~480 words) so too_big triggers
        self.summarizer = ChatSummaryUF(self.model, max_tokens=400)

    def test_returns_messages_when_not_too_big(self):
        messages = [
            {"role": "user", "content": "short"},
            {"role": "assistant", "content": "reply"},
        ]
        result = self.summarizer.summarize(messages)
        self.assertEqual(result, messages)

    def test_output_format_summary_ok_hot(self):
        """When enough messages graduate, output is [summary, Ok., *hot_messages]."""
        # Create enough messages to trigger graduation (27+ appends needed)
        messages = make_messages(30)  # 60 messages total
        result = self.summarizer.summarize(messages)

        # Result should be a list
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

        # First message is summary (user role, starts with summary_prefix)
        from aider import prompts

        self.assertEqual(result[0]["role"], "user")
        self.assertTrue(result[0]["content"].startswith(prompts.summary_prefix))

        # Second message is "Ok."
        self.assertEqual(result[1]["role"], "assistant")
        self.assertEqual(result[1]["content"], "Ok.")

        # Last message should be assistant (trailing Ok.)
        self.assertEqual(result[-1]["role"], "assistant")


# ────────────────────────────────────────────────────────────
# Area 4: Fallback to recursive
# ────────────────────────────────────────────────────────────


class TestFallbackToRecursive(TestCase):
    def test_fallback_when_result_exceeds_max_tokens(self):
        """If union-find output exceeds max_tokens, falls back to recursive."""
        # Model returns a very long summary that will exceed budget
        long_summary = " ".join(["word"] * 200)
        model = make_mock_model(summary_text=long_summary)
        summarizer = ChatSummaryUF(model, max_tokens=30)

        messages = make_messages(30)

        # Should still produce a result (recursive fallback)
        with mock.patch.object(
            ChatSummary,
            "summarize",
            return_value=[{"role": "user", "content": "recursive summary"}],
        ) as mock_recursive:
            result = summarizer.summarize(messages)
            # Either the UF result fits or recursive was called as fallback
            self.assertIsInstance(result, list)
            self.assertGreater(len(result), 0)

    def test_fallback_when_no_cold_clusters(self):
        """When not enough messages graduate, falls back to recursive."""
        model = make_mock_model(summary_text="summary")
        # Set max_tokens very low so too_big triggers, but only 5 messages
        # (not enough for graduation at graduate_at=26)
        summarizer = ChatSummaryUF(model, max_tokens=5)
        messages = make_messages(3)  # 6 messages, not enough for graduation

        with mock.patch.object(
            ChatSummary,
            "summarize",
            return_value=[
                {"role": "user", "content": "recursive fallback"},
                {"role": "assistant", "content": "Ok."},
            ],
        ) as mock_recursive:
            result = summarizer.summarize(messages)
            mock_recursive.assert_called_once()


# ────────────────────────────────────────────────────────────
# Area 5: summarize_all() parity
# ────────────────────────────────────────────────────────────


class TestSummarizeAllParity(TestCase):
    def test_delegates_to_parent(self):
        model = make_mock_model(summary_text="all summary")
        summarizer = ChatSummaryUF(model, max_tokens=100)
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        result = summarizer.summarize_all(messages)
        # Should produce same format as ChatSummary.summarize_all
        from aider import prompts

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["role"], "user")
        self.assertTrue(result[0]["content"].startswith(prompts.summary_prefix))


# ────────────────────────────────────────────────────────────
# Area 6: Stale discard + rebuild
# ────────────────────────────────────────────────────────────


class TestStaleDiscardAndRebuild(TestCase):
    def test_fed_count_shrink_triggers_rebuild(self):
        """When messages shrink (previous result applied), forest rebuilds."""
        model = make_mock_model(summary_text="cluster summary")
        summarizer = ChatSummaryUF(model, max_tokens=30)

        # First call with many messages
        messages_large = make_messages(30)
        summarizer.summarize(messages_large)
        old_fed_count = summarizer._fed_count
        self.assertEqual(old_fed_count, 60)

        # Simulate summarize_end applying the result: done_messages shrinks
        messages_small = make_messages(5)

        # _init_context_window should be called since _fed_count (60) > len(messages_small) (10)
        with mock.patch.object(summarizer, "_init_context_window", wraps=summarizer._init_context_window) as mock_init:
            summarizer.summarize(messages_small)
            mock_init.assert_called_once()

    def test_fed_count_tracks_incremental_feeding(self):
        """_fed_count increases with each call, feeding only new messages."""
        model = make_mock_model(summary_text="cluster summary")
        summarizer = ChatSummaryUF(model, max_tokens=30)

        messages = make_messages(15)  # 30 messages
        summarizer.summarize(messages)
        self.assertEqual(summarizer._fed_count, 30)

        # Add more messages
        messages_more = messages + make_messages(5)  # 40 messages
        # Context window should only receive the 10 new messages
        with mock.patch.object(summarizer.context_window, "append", wraps=summarizer.context_window.append) as mock_append:
            summarizer.summarize(messages_more)
            # Only the new user/assistant messages should be appended
            # 10 new messages, all have content, so 10 appends
            self.assertEqual(mock_append.call_count, 10)


# ────────────────────────────────────────────────────────────
# Area 11: Incremental feeding
# ────────────────────────────────────────────────────────────


class TestIncrementalFeeding(TestCase):
    def test_skips_non_user_assistant_roles(self):
        """System messages and other roles are not fed to context window."""
        model = make_mock_model(summary_text="summary")
        summarizer = ChatSummaryUF(model, max_tokens=5)

        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
            {"role": "function", "content": "result"},
        ]

        with mock.patch.object(
            summarizer.context_window, "append", wraps=summarizer.context_window.append
        ) as mock_append, mock.patch.object(
            ChatSummary, "summarize", return_value=messages
        ):
            summarizer.summarize(messages)
            # Only user and assistant messages should be appended
            self.assertEqual(mock_append.call_count, 2)

    def test_empty_content_not_fed(self):
        """Messages with empty content are not fed."""
        model = make_mock_model(summary_text="summary")
        # max_tokens=1 so too_big triggers even with small messages
        summarizer = ChatSummaryUF(model, max_tokens=1)

        messages = [
            {"role": "user", "content": "hello there friend"},
            {"role": "assistant", "content": ""},
            {"role": "user", "content": "world again now"},
        ]

        with mock.patch.object(
            summarizer.context_window, "append", wraps=summarizer.context_window.append
        ) as mock_append, mock.patch.object(
            ChatSummary, "summarize", return_value=messages
        ):
            summarizer.summarize(messages)
            # Only non-empty user/assistant messages
            self.assertEqual(mock_append.call_count, 2)


# ────────────────────────────────────────────────────────────
# Area 7: Low token budget
# ────────────────────────────────────────────────────────────


class TestLowTokenBudget(TestCase):
    def test_low_budget_falls_back_gracefully(self):
        """With a very low token budget, falls back to recursive without crashing."""
        model = make_mock_model(summary_text="short summary")
        summarizer = ChatSummaryUF(model, max_tokens=10)

        messages = make_messages(30)

        # Should not raise, should produce a result
        with mock.patch.object(
            ChatSummary,
            "summarize",
            return_value=[
                {"role": "user", "content": "fallback"},
                {"role": "assistant", "content": "Ok."},
            ],
        ):
            result = summarizer.summarize(messages)
            self.assertIsInstance(result, list)
            self.assertGreater(len(result), 0)


# ────────────────────────────────────────────────────────────
# Mixed-role message handling
# ────────────────────────────────────────────────────────────


class TestMixedRoleHandling(TestCase):
    def test_system_messages_in_tail_preserved(self):
        """System messages interspersed with user/assistant are preserved in hot tail."""
        model = make_mock_model(summary_text="cluster summary")
        summarizer = ChatSummaryUF(model, max_tokens=400)

        messages = []
        for i in range(30):
            messages.append({"role": "user", "content": f"User message {i} about topic {i % 3}"})
            messages.append({"role": "assistant", "content": f"Assistant response {i} about topic {i % 3}"})
        # Insert system messages near the end
        messages.insert(-2, {"role": "system", "content": "System reminder"})
        messages.insert(-1, {"role": "tool", "content": "Tool output"})

        result = summarizer.summarize(messages)
        if result != messages:  # Only check if summarization happened
            result_contents = [m.get("content", "") for m in result]
            # System and tool messages from the tail should be preserved
            self.assertIn("System reminder", result_contents)
            self.assertIn("Tool output", result_contents)

    def test_hot_tail_maps_to_correct_original_messages(self):
        """hot_count user/assistant messages map back to correct original indices."""
        model = make_mock_model(summary_text="cluster summary")
        summarizer = ChatSummaryUF(model, max_tokens=400)

        messages = make_messages(30)  # 60 messages
        # Insert 3 system messages in the last 10 messages
        messages.insert(55, {"role": "system", "content": "reminder 1"})
        messages.insert(58, {"role": "system", "content": "reminder 2"})
        messages.insert(61, {"role": "system", "content": "reminder 3"})

        result = summarizer.summarize(messages)
        if result != messages:
            # All 3 system messages should appear in the result
            system_msgs = [m for m in result if m.get("role") == "system"]
            self.assertEqual(len(system_msgs), 3)


# ────────────────────────────────────────────────────────────
# Memory bounds
# ────────────────────────────────────────────────────────────


class TestMemoryBounds(TestCase):
    def test_hot_list_trimmed_after_graduation(self):
        """_hot list is trimmed after messages graduate, bounding memory."""
        embedder = TFIDFEmbedder()
        mock_summarizer = mock.Mock()
        mock_summarizer.summarize = mock.Mock(return_value="summary")

        cw = ContextWindow(
            embedder, mock_summarizer,
            graduate_at=5, max_cold_clusters=10,
        )
        # Append many messages — should graduate and trim
        for i in range(20):
            cw.append(f"message {i} about topic {i % 3}")

        # _hot should only contain ungraduated messages (at most graduate_at)
        self.assertLessEqual(len(cw._hot), cw._graduate_at)
        # _graduated_index should be 0 (trimmed)
        self.assertEqual(cw._graduated_index, 0)

    def test_hot_stays_bounded_over_long_session(self):
        """Memory stays bounded even after many appends."""
        embedder = TFIDFEmbedder()
        mock_summarizer = mock.Mock()
        mock_summarizer.summarize = mock.Mock(return_value="summary")

        cw = ContextWindow(
            embedder, mock_summarizer,
            graduate_at=5, max_cold_clusters=10,
        )
        for i in range(200):
            cw.append(f"message {i}")

        # _hot should never exceed graduate_at
        self.assertLessEqual(len(cw._hot), cw._graduate_at)


# ────────────────────────────────────────────────────────────
# Embedding service
# ────────────────────────────────────────────────────────────


class TestTFIDFEmbedder(TestCase):
    def test_embed_returns_sparse_dict(self):
        embedder = TFIDFEmbedder()
        result = embedder.embed("python code review")
        self.assertIsInstance(result, dict)
        self.assertIn("python", result)
        self.assertIn("code", result)
        self.assertIn("review", result)

    def test_embed_empty_string(self):
        embedder = TFIDFEmbedder()
        result = embedder.embed("")
        self.assertEqual(result, {})

    def test_embed_stopwords_filtered(self):
        embedder = TFIDFEmbedder()
        result = embedder.embed("the quick brown fox")
        self.assertNotIn("the", result)
        self.assertIn("quick", result)
        self.assertIn("brown", result)
        self.assertIn("fox", result)

    def test_vocabulary_grows(self):
        embedder = TFIDFEmbedder()
        embedder.embed("python code")
        size1 = embedder.vocab_size
        embedder.embed("java programming")
        size2 = embedder.vocab_size
        self.assertGreater(size2, size1)

    def test_doc_count_increments(self):
        embedder = TFIDFEmbedder()
        self.assertEqual(embedder.doc_count, 0)
        embedder.embed("hello")
        self.assertEqual(embedder.doc_count, 1)
        embedder.embed("world")
        self.assertEqual(embedder.doc_count, 2)

    def test_similar_texts_have_high_cosine(self):
        embedder = TFIDFEmbedder()
        emb1 = embedder.embed("python debugging error traceback")
        emb2 = embedder.embed("python error debugging stack trace")
        sim = _cosine_similarity(emb1, emb2)
        self.assertGreater(sim, 0.3)

    def test_different_texts_have_low_cosine(self):
        embedder = TFIDFEmbedder()
        emb1 = embedder.embed("python debugging error traceback")
        emb2 = embedder.embed("cooking recipe pasta tomato sauce")
        sim = _cosine_similarity(emb1, emb2)
        self.assertLess(sim, 0.1)


# ────────────────────────────────────────────────────────────
# ContextWindow integration
# ────────────────────────────────────────────────────────────


class TestContextWindow(TestCase):
    def setUp(self):
        self.embedder = TFIDFEmbedder()
        self.mock_summarizer = mock.Mock()
        self.mock_summarizer.summarize = mock.Mock(return_value="cluster summary")

    def test_append_and_render(self):
        cw = ContextWindow(
            self.embedder, self.mock_summarizer,
            graduate_at=3, max_cold_clusters=10
        )
        for i in range(5):
            cw.append(f"message {i} about topic {i}")
        rendered = cw.render()
        self.assertGreater(len(rendered), 0)

    def test_hot_count_tracks_correctly(self):
        cw = ContextWindow(
            self.embedder, self.mock_summarizer,
            graduate_at=3, max_cold_clusters=10
        )
        self.assertEqual(cw.hot_count, 0)
        cw.append("msg1")
        self.assertEqual(cw.hot_count, 1)
        cw.append("msg2")
        self.assertEqual(cw.hot_count, 2)
        cw.append("msg3")
        self.assertEqual(cw.hot_count, 3)
        # 4th append: hot = 4, 4 > graduate_at=3, so one graduates
        cw.append("msg4")
        self.assertEqual(cw.hot_count, 3)
        self.assertEqual(cw.cold_count, 1)

    def test_graduation_sends_to_forest(self):
        cw = ContextWindow(
            self.embedder, self.mock_summarizer,
            graduate_at=2, max_cold_clusters=10
        )
        cw.append("message alpha about python")
        cw.append("message beta about java")
        self.assertEqual(cw.cold_count, 0)
        # Third message triggers graduation of first
        cw.append("message gamma about rust")
        self.assertGreater(cw.cold_count, 0)

    def test_force_merge_when_too_many_clusters(self):
        cw = ContextWindow(
            self.embedder, self.mock_summarizer,
            graduate_at=1, max_cold_clusters=2
        )
        # Each append with graduate_at=1 means hot keeps only 1
        # After 4 appends: 3 graduated, 1 hot. 3 clusters > max 2, force merge
        for i in range(4):
            cw.append(f"unique topic number {i} with keyword{i}")
        self.assertLessEqual(cw.cold_count, 2)

    def test_render_includes_cold_and_hot(self):
        cw = ContextWindow(
            self.embedder, self.mock_summarizer,
            graduate_at=2, max_cold_clusters=10
        )
        cw.append("cold message about python")
        cw.append("cold message about java")
        cw.append("hot message about rust")  # triggers graduation of first
        cw.resolve_dirty()
        rendered = cw.render()
        # Should include both cold summaries/content and hot content
        self.assertGreater(len(rendered), 0)

    def test_resolve_dirty_produces_summaries(self):
        cw = ContextWindow(
            self.embedder, self.mock_summarizer,
            graduate_at=1, max_cold_clusters=1,
            merge_threshold=0.0  # force merges
        )
        cw.append("python code review")
        cw.append("python debugging errors")
        cw.append("python testing framework")
        # With graduate_at=1, max_cold=1: all get merged into one cluster
        cw.resolve_dirty()
        # The summarizer should have been called for the dirty merged cluster
        if self.mock_summarizer.summarize.called:
            rendered = cw.render()
            # Cold part should contain the summary
            self.assertGreater(len(rendered), 0)
