from unittest.mock import MagicMock, patch

from aider import versioncheck


def _patched_pypi(latest="999.0.0"):
    """Return a fake pypi response so check_version's network call succeeds."""
    response = MagicMock()
    response.json.return_value = {"info": {"version": latest}}
    return response


def test_check_version_swallows_not_a_directory_error(tmp_path):
    """Regression test for #5180: when something in the marker path is not a
    directory (the user had a file at ~/.aider/caches), the marker write should
    fail quietly instead of crashing aider at startup."""
    marker = tmp_path / "not-a-dir" / "marker"
    # Make the supposed parent dir actually be a file so `mkdir(parents=True)`
    # raises NotADirectoryError.
    (tmp_path / "not-a-dir").write_text("oops, I'm a file")

    io = MagicMock()
    with patch.object(versioncheck, "VERSION_CHECK_FNAME", marker), patch(
        "requests.get", return_value=_patched_pypi()
    ):
        # Should not raise. Used to bubble NotADirectoryError out of the
        # finally block.
        versioncheck.check_version(io, just_check=True)


def test_check_version_swallows_permission_error_on_marker_write(tmp_path):
    """If the marker write fails for any OSError reason (read-only fs,
    permission denied, etc.) the function should not crash."""
    marker = tmp_path / "cache" / "marker"
    io = MagicMock()

    with patch.object(versioncheck, "VERSION_CHECK_FNAME", marker), patch(
        "requests.get", return_value=_patched_pypi()
    ), patch("pathlib.Path.touch", side_effect=PermissionError(13, "denied")):
        versioncheck.check_version(io, just_check=True)


def test_check_version_verbose_warns_on_marker_write_failure(tmp_path):
    """In verbose mode the user should at least see a warning when the marker
    write fails, so the silent-skip is not completely invisible."""
    marker = tmp_path / "not-a-dir" / "marker"
    (tmp_path / "not-a-dir").write_text("oops")

    io = MagicMock()
    with patch.object(versioncheck, "VERSION_CHECK_FNAME", marker), patch(
        "requests.get", return_value=_patched_pypi()
    ):
        versioncheck.check_version(io, just_check=True, verbose=True)

    warning_calls = [
        call for call in io.tool_warning.call_args_list if "version-check marker" in str(call)
    ]
    assert warning_calls, "expected a verbose warning about the failed marker write"


def test_check_version_writes_marker_in_happy_path(tmp_path):
    """Sanity check that the normal flow still creates the marker file when
    the filesystem cooperates."""
    marker = tmp_path / "cache" / "marker"
    io = MagicMock()

    with patch.object(versioncheck, "VERSION_CHECK_FNAME", marker), patch(
        "requests.get", return_value=_patched_pypi()
    ):
        versioncheck.check_version(io, just_check=True)

    assert marker.exists(), "the marker file should be created on a clean filesystem"
