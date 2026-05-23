from unittest.mock import Mock, patch

from aider import versioncheck


def test_check_version_ignores_unwritable_cache_path(tmp_path, monkeypatch):
    blocked_parent = tmp_path / "blocked"
    blocked_parent.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        versioncheck, "VERSION_CHECK_FNAME", blocked_parent / "versioncheck"
    )

    io = Mock()
    with patch("requests.get", side_effect=RuntimeError("offline")):
        assert versioncheck.check_version(io) is False

    io.tool_error.assert_called_once_with(
        "Error checking pypi for new version: offline"
    )
