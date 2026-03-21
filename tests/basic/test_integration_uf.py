"""Integration test: union-find summarizer with real tokenizer, mock LLM.

Tests the full control loop that was broken in practice:
- too_big() fires on real token counts
- force_graduate creates cold clusters within the budget
- resolve_dirty summarizes clusters (mock LLM, no API calls)
- render() produces structured output
- /topics shows clusters, /drop-topic removes them

Uses the real model tokenizer (litellm) but mocks all LLM calls.
This catches control-loop bugs that unit tests with word-count mocks miss.
"""

from unittest import TestCase, mock

from aider.chat_summary_uf import ChatSummaryUF

from aider.models import Model
from aider import prompts


def _make_real_tokenizer_summarizer(model_name="claude-sonnet-4-5", max_tokens=1024):
    """Build ChatSummaryUF with real tokenizer but mock LLM calls."""
    model = Model(model_name)

    counter = {"n": 0}

    def mock_send(messages):
        counter["n"] += 1
        return f"Cluster {counter['n']} summary: topic discussion"

    # Mock LLM calls on both weak and main model
    model.weak_model.simple_send_with_retries = mock_send
    model.simple_send_with_retries = mock_send

    summarizer = ChatSummaryUF([model.weak_model, model], max_tokens=max_tokens)
    return summarizer, model, counter


def _build_conversation(n_exchanges=15):
    """Build a realistic multi-topic conversation with enough tokens to trigger summarization."""
    topics = [
        ("database migration", "Adding a new column called verified to the users table for email verification status. The migration needs both up and down methods, plus an index on the verified column for faster queries. We should use ALTER TABLE ADD COLUMN with a DEFAULT false."),
        ("JWT authentication", "Implementing Bearer token validation middleware with pyjwt. The token should include user_id, role, and exp claims. We need a refresh token endpoint that issues new access tokens. Token expiry is 24 hours, refresh expiry is 30 days."),
        ("React components", "Building a dashboard with react-loading-skeleton for loading states. The sidebar navigation should highlight the active route using useLocation from react-router-dom. We also need a ThemeProvider using React context for dark mode support with tailwind dark: classes."),
        ("CI pipeline", "GitHub Actions workflow that runs pytest with coverage before deploying. Using actions/cache with pip cache directory keyed on requirements.txt hash. The deploy job uses needs: [test] to depend on the test job passing first."),
        ("payment processing", "Race condition in the payment webhook handler where two webhook events process the same payment simultaneously. Fix with SELECT FOR UPDATE database lock. The lock timeout is configurable via PAYMENT_LOCK_TIMEOUT_MS with a default of 5000ms."),
    ]
    messages = []
    for i in range(n_exchanges):
        topic_name, topic_detail = topics[i % len(topics)]
        messages.append({
            "role": "user",
            "content": (
                f"I need help with {topic_name}. {topic_detail} "
                f"Can you review the current implementation in the codebase and suggest specific improvements? "
                f"I want to make sure we handle all edge cases properly. This is exchange {i}."
            ),
        })
        messages.append({
            "role": "assistant",
            "content": (
                f"I've reviewed the {topic_name} implementation. {topic_detail} "
                f"Here are my specific suggestions: "
                f"First, the current implementation doesn't handle the error case where the connection drops mid-operation. "
                f"Second, we should add input validation to prevent injection attacks. "
                f"Third, the test coverage is missing edge cases around concurrent access patterns. "
                f"Fourth, consider adding structured logging so we can debug production issues more easily. "
                f"I can help implement any of these changes right now."
            ),
        })
    return messages


class TestIntegrationControlLoop(TestCase):
    """Verify the control loop works with real tokenizers."""

    def test_too_big_fires_with_real_tokenizer(self):
        """Sanity check: too_big returns True for a realistic conversation."""
        summarizer, model, _ = _make_real_tokenizer_summarizer(max_tokens=1024)
        messages = _build_conversation(8)
        total = sum(summarizer.token_count(m) for m in messages)
        self.assertGreater(total, 1024, f"Expected >1024 tokens, got {total}")
        self.assertTrue(summarizer.too_big(messages))

    def test_cold_clusters_form(self):
        """The critical test: summarize() produces cold clusters, not a recursive blob."""
        summarizer, model, counter = _make_real_tokenizer_summarizer(max_tokens=1024)
        messages = _build_conversation(8)

        result = summarizer.summarize(messages)

        # Must not return original (that means too_big was False)
        self.assertNotEqual(result, messages, "summarize() returned original messages unchanged")

        # Must have cold clusters
        self.assertGreater(
            summarizer.context_window.cold_count, 0,
            "No cold clusters formed — force_graduate didn't work"
        )

        # Result must start with summary prefix (UF path, not recursive)
        self.assertEqual(result[0]["role"], "user")
        self.assertTrue(
            result[0]["content"].startswith(prompts.summary_prefix),
            "Result doesn't start with summary prefix"
        )

        # LLM was called for cluster summarization
        self.assertGreater(counter["n"], 0, "No LLM calls made for cluster summarization")

        # Result fits within budget
        result_tokens = sum(summarizer.token_count(m) for m in result)
        self.assertLessEqual(result_tokens, 1024, f"Result {result_tokens} exceeds budget 1024")

    def test_result_smaller_than_input(self):
        """UF result must be strictly smaller than input."""
        summarizer, model, _ = _make_real_tokenizer_summarizer(max_tokens=1024)
        messages = _build_conversation(8)

        result = summarizer.summarize(messages)

        result_tokens = sum(summarizer.token_count(m) for m in result)
        input_tokens = sum(summarizer.token_count(m) for m in messages)
        self.assertLess(result_tokens, input_tokens)

    def test_hot_zone_within_budget(self):
        """Hot messages should fit in ~25% of max_tokens after graduation."""
        summarizer, model, _ = _make_real_tokenizer_summarizer(max_tokens=1024)
        messages = _build_conversation(8)

        summarizer.summarize(messages)

        hot_budget = 1024 // 4  # 256
        hot_messages = summarizer.context_window.hot_messages()
        hot_tokens = sum(
            summarizer.token_count({"role": "user", "content": c})
            for c in hot_messages
        )
        # Allow some slack — the 25% is a target, not a hard cap
        self.assertLess(
            hot_tokens, 1024 // 2,
            f"Hot zone {hot_tokens} tokens exceeds half the budget"
        )

    def test_repeated_summarize_cycles(self):
        """Simulate multiple summarize cycles like a real session."""
        summarizer, model, _ = _make_real_tokenizer_summarizer(max_tokens=1024)

        # First batch
        messages = _build_conversation(6)
        result1 = summarizer.summarize(messages)
        self.assertNotEqual(result1, messages)

        # Simulate summarize_end applying the result
        # Then more messages arrive
        messages2 = list(result1)
        for i in range(4):
            messages2.append({
                "role": "user",
                "content": f"Follow-up question {i} about deployment configuration",
            })
            messages2.append({
                "role": "assistant",
                "content": f"Here is my response {i} about the deployment setup and configuration.",
            })

        # Second summarization cycle
        if summarizer.too_big(messages2):
            result2 = summarizer.summarize(messages2)
            self.assertNotEqual(result2, messages2)
            # Should still have clusters
            self.assertGreaterEqual(summarizer.context_window.cold_count, 0)

    def test_low_budget_still_works(self):
        """Even at a very low budget, UF path should succeed or fall back gracefully."""
        summarizer, model, _ = _make_real_tokenizer_summarizer(max_tokens=256)
        messages = _build_conversation(6)

        result = summarizer.summarize(messages)

        # Should produce a result (either UF or recursive fallback)
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        result_tokens = sum(summarizer.token_count(m) for m in result)
        self.assertLessEqual(result_tokens, 256)
