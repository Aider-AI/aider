import requests
from aider import versioncheck
from aider.io import InputOutput


def test_check_version_survives_unwritable_cache(monkeypatch, tmp_path):
    # The version check only caches its last run; an unwritable home directory must not crash aider.
    cache_blocker = tmp_path / "not-a-directory"
    cache_blocker.write_text("blocked", encoding="utf-8")
    monkeypatch.setattr(
        versioncheck,
        "VERSION_CHECK_FNAME",
        cache_blocker / "caches" / "versioncheck",
    )

    def offline_get(*args, **kwargs):
        raise requests.exceptions.ConnectionError("offline")

    monkeypatch.setattr(requests, "get", offline_get)

    io = InputOutput(pretty=False)
    assert versioncheck.check_version(io) is False
