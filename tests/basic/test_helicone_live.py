import pytest

from aider.helicone import HeliconeModelManager


def test_helicone_get_all_model_ids_live():
    """Integration-style test: fetch Helicone public registry and assert non-empty IDs.

    Uses the real Helicone public endpoint. Skips on network errors to avoid false failures
    when offline.
    """
    mgr = HeliconeModelManager()
    # Force a live fetch by disabling cached content on this instance
    mgr.content = None
    mgr._cache_loaded = True

    try:
        ids = mgr.get_all_model_ids()
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"Live Helicone registry fetch failed or network unavailable: {e}")

    assert isinstance(ids, list)
    assert len(ids) > 0

    # Assert presence of some well-known Helicone registry IDs
    expected_ids = [
        "gpt-4o",
        "gpt-4.1",
        "o3-mini",
        "claude-3.7-sonnet",
        "deepseek-v3",
        "grok-4",
        "gemini-2.5-pro",
    ]
    for mid in expected_ids:
        assert mid in ids, f"Expected Helicone model id missing: {mid}"
