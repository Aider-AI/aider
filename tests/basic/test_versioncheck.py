from unittest.mock import MagicMock, patch

from aider.versioncheck import check_version


class TestCheckVersion:
    @patch("aider.versioncheck.VERSION_CHECK_FNAME")
    @patch("aider.versioncheck.requests", create=True)
    def test_permission_error_on_touch_does_not_crash(self, mock_requests, mock_fname):
        """Regression test for issue #4958.

        When the version cache file cannot be written (e.g. read-only filesystem,
        permission denied), check_version should handle the error gracefully
        instead of raising an uncaught PermissionError.
        """
        mock_fname.exists.return_value = False
        mock_fname.parent.mkdir.return_value = None
        mock_fname.touch.side_effect = PermissionError(
            "[Errno 13] Permission denied: '/root/.aider/caches/versioncheck'"
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {"info": {"version": "0.86.2"}}
        mock_requests.get.return_value = mock_response

        io = MagicMock()

        # Should not raise
        check_version(io)

    @patch("aider.versioncheck.VERSION_CHECK_FNAME")
    @patch("aider.versioncheck.requests", create=True)
    def test_permission_error_on_mkdir_does_not_crash(self, mock_requests, mock_fname):
        """When even the parent directory cannot be created, check_version
        should still not crash."""
        mock_fname.exists.return_value = False
        mock_fname.parent.mkdir.side_effect = PermissionError(
            "[Errno 13] Permission denied: '/root/.aider/caches'"
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {"info": {"version": "0.86.2"}}
        mock_requests.get.return_value = mock_response

        io = MagicMock()

        # Should not raise
        check_version(io)

    @patch("aider.versioncheck.VERSION_CHECK_FNAME")
    @patch("aider.versioncheck.requests", create=True)
    def test_oserror_on_touch_does_not_crash(self, mock_requests, mock_fname):
        """Other OSError variants (read-only filesystem, disk full) should
        also be handled gracefully."""
        mock_fname.exists.return_value = False
        mock_fname.parent.mkdir.return_value = None
        mock_fname.touch.side_effect = OSError("[Errno 30] Read-only file system")

        mock_response = MagicMock()
        mock_response.json.return_value = {"info": {"version": "0.86.2"}}
        mock_requests.get.return_value = mock_response

        io = MagicMock()

        # Should not raise
        check_version(io)

    @patch("aider.versioncheck.VERSION_CHECK_FNAME")
    @patch("aider.versioncheck.requests", create=True)
    @patch("aider.versioncheck.aider")
    def test_normal_version_check_still_works(self, mock_aider, mock_requests, mock_fname):
        """Ensure the fix doesn't break normal version checking behavior."""
        mock_fname.exists.return_value = False
        mock_fname.parent.mkdir.return_value = None
        mock_fname.touch.return_value = None
        mock_aider.__version__ = "0.1.0"

        mock_response = MagicMock()
        mock_response.json.return_value = {"info": {"version": "99.0.0"}}
        mock_requests.get.return_value = mock_response

        io = MagicMock()

        result = check_version(io, just_check=True)
        assert result is True
        mock_fname.touch.assert_called_once()
