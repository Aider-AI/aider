import unittest
from unittest.mock import MagicMock, patch

from aider.io import InputOutput
from aider.versioncheck import check_version


class TestVersionCheck(unittest.TestCase):
    def setUp(self):
        self.io = InputOutput(pretty=False, yes=True)

    @patch("requests.get")
    @patch("aider.versioncheck.VERSION_CHECK_FNAME")
    def test_check_version_permission_error_on_touch(self, mock_fname, mock_get):
        mock_fname.exists.return_value = False
        mock_fname.parent.mkdir.return_value = None
        mock_fname.touch.side_effect = PermissionError(
            "Permission denied: ~/.aider/caches/versioncheck"
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {"info": {"version": "0.0.1"}}
        mock_get.return_value = mock_response

        # Should complete gracefully without raising PermissionError
        result = check_version(self.io, just_check=True)
        self.assertIsInstance(result, bool)

    @patch("requests.get")
    @patch("aider.versioncheck.VERSION_CHECK_FNAME")
    def test_check_version_oserror_on_mkdir(self, mock_fname, mock_get):
        mock_fname.exists.return_value = False
        mock_fname.parent.mkdir.side_effect = OSError("Read-only file system")

        mock_response = MagicMock()
        mock_response.json.return_value = {"info": {"version": "0.0.1"}}
        mock_get.return_value = mock_response

        # Should complete gracefully without raising OSError
        result = check_version(self.io, just_check=True)
        self.assertIsInstance(result, bool)

    @patch("requests.get")
    @patch("aider.versioncheck.VERSION_CHECK_FNAME")
    def test_check_version_oserror_on_exists_check(self, mock_fname, mock_get):
        mock_fname.exists.side_effect = OSError("Permission denied")

        mock_response = MagicMock()
        mock_response.json.return_value = {"info": {"version": "0.0.1"}}
        mock_get.return_value = mock_response

        # Should complete gracefully without raising OSError
        result = check_version(self.io, just_check=False)
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
