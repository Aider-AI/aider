"""Retry sleep helpers for LLM provider calls.

Two improvements over plain exponential backoff:

1. Full-jitter — the actual sleep is randomized within ``[0, cap]`` rather
   than being exactly ``cap``. Many clients hitting a shared 429 at the
   same time would otherwise wake up together and re-hit the provider in
   sync; jitter spreads them out across the window. This is the recipe
   described in the AWS Architecture Blog post "Exponential Backoff And
   Jitter" (2015), specifically the "Full Jitter" variant.

2. ``Retry-After`` honoring — when the provider response carries a
   ``Retry-After`` header (RFC 7231 §7.1.3, integer seconds or HTTP-date),
   use that value verbatim instead of guessing. Capped at ``cap * 2`` so
   a hostile or buggy provider can't put us to sleep for hours.
"""

import random
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

MAX_RETRIES = 8


def compute_retry_sleep(attempt, base_delay, cap, retry_after=None):
    """Return seconds to sleep before retry ``attempt`` (1-indexed).

    - If ``retry_after`` is set (parsed from a provider response header),
      use it directly, capped at ``cap * 2`` for safety.
    - Otherwise full-jitter exponential: the upper bound grows as
      ``base_delay * 2 ** (attempt - 1)``, clamped at ``cap``, and the
      actual sleep is drawn uniformly from ``[0, bound]``.
    """
    if retry_after is not None and retry_after > 0:
        return min(float(retry_after), cap * 2)
    bound = min(base_delay * (2 ** max(attempt - 1, 0)), cap)
    return random.uniform(0, bound)


def _extract_headers(exception):
    """Walk common attribute paths to find an exception's response headers.

    Different SDKs expose headers in different places; we try the common
    ones in turn. Returns the headers object (dict-like) or None.
    """
    for attr in ("response_headers", "headers"):
        h = getattr(exception, attr, None)
        if h:
            return h
    response = getattr(exception, "response", None)
    if response is not None:
        h = getattr(response, "headers", None)
        if h:
            return h
    return None


def _header_value(headers, name):
    """Case-insensitive header lookup that tolerates dict / list-of-tuples /
    SDK header objects."""
    if headers is None:
        return None
    # Try direct .get() first (dict, httpx.Headers, requests CaseInsensitiveDict)
    try:
        v = headers.get(name) or headers.get(name.lower()) or headers.get(name.upper())
        if v is not None:
            return v
    except (AttributeError, TypeError):
        pass
    # Fallback: iterate
    try:
        target = name.lower()
        for key in headers:
            if str(key).lower() == target:
                return headers[key]
    except (TypeError, KeyError):
        pass
    return None


def parse_retry_after(exception):
    """Extract a Retry-After value (in seconds, as float) from an exception.

    Handles both integer-seconds form (``"30"``) and HTTP-date form
    (``"Wed, 21 Oct 2026 07:28:00 GMT"``). Walks ``__cause__`` once if the
    immediate exception has no headers. Returns ``None`` if the header is
    absent or unparseable.
    """
    headers = _extract_headers(exception)
    if headers is None:
        cause = getattr(exception, "__cause__", None)
        if cause is not None and cause is not exception:
            headers = _extract_headers(cause)
    if headers is None:
        return None

    value = _header_value(headers, "Retry-After")
    if value is None:
        return None

    # Integer seconds form
    try:
        return float(value)
    except (ValueError, TypeError):
        pass

    # HTTP-date form
    try:
        dt = parsedate_to_datetime(str(value))
    except (TypeError, ValueError, IndexError):
        return None
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = (dt - datetime.now(timezone.utc)).total_seconds()
    return delta if delta > 0 else None
