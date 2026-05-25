"""Tests for aider.retry_utils — jitter bounds + Retry-After parsing."""

import unittest
from email.utils import format_datetime
from datetime import datetime, timedelta, timezone

from aider.retry_utils import (
    MAX_RETRIES,
    compute_retry_sleep,
    parse_retry_after,
)


class TestComputeRetrySleep(unittest.TestCase):
    def test_full_jitter_within_bounds(self):
        # 1000 samples must all fall inside [0, cap]; lots of samples must
        # also not all bunch into one half of the range.
        cap = 60.0
        samples = [compute_retry_sleep(1, 0.125, cap) for _ in range(1000)]
        self.assertTrue(all(0.0 <= s <= cap for s in samples))
        # First-attempt bound is min(0.125 * 1, cap) = 0.125 — so all samples
        # actually live in [0, 0.125].
        self.assertTrue(all(s <= 0.125 + 1e-9 for s in samples))

    def test_jitter_bound_grows_with_attempt(self):
        cap = 60.0
        # Attempt 1: bound = 0.125
        s1_max = max(compute_retry_sleep(1, 0.125, cap) for _ in range(2000))
        # Attempt 5: bound = 0.125 * 16 = 2.0
        s5_max = max(compute_retry_sleep(5, 0.125, cap) for _ in range(2000))
        # Attempt 10: bound saturates at cap = 60.0
        s10_max = max(compute_retry_sleep(10, 0.125, cap) for _ in range(2000))
        self.assertLess(s1_max, 0.2)
        self.assertGreater(s5_max, 1.0)
        self.assertGreater(s10_max, 30.0)
        self.assertLessEqual(s10_max, cap)

    def test_jitter_clamps_at_cap(self):
        cap = 60.0
        # Attempt 50 would compute 0.125 * 2**49 — must be clamped at cap
        for _ in range(100):
            s = compute_retry_sleep(50, 0.125, cap)
            self.assertLessEqual(s, cap)

    def test_retry_after_overrides_jitter(self):
        # When Retry-After is given, sleep equals it (within safety cap)
        for _ in range(50):
            s = compute_retry_sleep(1, 0.125, 60.0, retry_after=30.0)
            self.assertEqual(s, 30.0)

    def test_retry_after_capped_at_double_cap(self):
        # Hostile provider says "wait 600s" — we cap at cap*2 = 120
        s = compute_retry_sleep(1, 0.125, 60.0, retry_after=600.0)
        self.assertEqual(s, 120.0)

    def test_retry_after_zero_or_negative_ignored(self):
        # Falls through to jitter when Retry-After is non-positive
        for _ in range(50):
            s = compute_retry_sleep(1, 0.125, 60.0, retry_after=0)
            self.assertLessEqual(s, 0.125)
        for _ in range(50):
            s = compute_retry_sleep(1, 0.125, 60.0, retry_after=-5)
            self.assertLessEqual(s, 0.125)


class _StubException(Exception):
    """Plain exception we can attach response shapes to."""


class _StubResponse:
    def __init__(self, headers):
        self.headers = headers


class TestParseRetryAfter(unittest.TestCase):
    def test_seconds_form_from_response_headers(self):
        exc = _StubException("rate limited")
        exc.response = _StubResponse({"Retry-After": "30"})
        self.assertEqual(parse_retry_after(exc), 30.0)

    def test_seconds_form_from_top_level_headers_attr(self):
        exc = _StubException("rate limited")
        exc.headers = {"Retry-After": "45"}
        self.assertEqual(parse_retry_after(exc), 45.0)

    def test_case_insensitive_header_name(self):
        exc = _StubException("rate limited")
        exc.headers = {"retry-after": "12"}
        self.assertEqual(parse_retry_after(exc), 12.0)

    def test_http_date_form(self):
        exc = _StubException("rate limited")
        future = datetime.now(timezone.utc) + timedelta(seconds=20)
        exc.headers = {"Retry-After": format_datetime(future)}
        delta = parse_retry_after(exc)
        # Allow small drift between when we set the header and now
        self.assertIsNotNone(delta)
        self.assertGreater(delta, 10.0)
        self.assertLessEqual(delta, 25.0)

    def test_http_date_in_past_returns_none(self):
        exc = _StubException("rate limited")
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        exc.headers = {"Retry-After": format_datetime(past)}
        self.assertIsNone(parse_retry_after(exc))

    def test_missing_header_returns_none(self):
        exc = _StubException("rate limited")
        exc.headers = {"X-Other": "1"}
        self.assertIsNone(parse_retry_after(exc))

    def test_no_response_or_headers_returns_none(self):
        exc = _StubException("rate limited")
        self.assertIsNone(parse_retry_after(exc))

    def test_garbage_header_value_returns_none(self):
        exc = _StubException("rate limited")
        exc.headers = {"Retry-After": "not a number, not a date"}
        self.assertIsNone(parse_retry_after(exc))

    def test_falls_through_to_cause(self):
        # If the outer exception lacks headers, walk __cause__ once
        inner = _StubException("inner")
        inner.headers = {"Retry-After": "17"}
        outer = _StubException("outer")
        outer.__cause__ = inner
        self.assertEqual(parse_retry_after(outer), 17.0)


class TestMaxRetriesConstant(unittest.TestCase):
    def test_max_retries_is_finite_and_reasonable(self):
        # Smoke check — the constant exists and is in a sane range so
        # users can't get trapped in retry loops indefinitely.
        self.assertIsInstance(MAX_RETRIES, int)
        self.assertGreater(MAX_RETRIES, 1)
        self.assertLess(MAX_RETRIES, 50)


if __name__ == "__main__":
    unittest.main()
