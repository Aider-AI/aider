import ntpath
from unittest.mock import patch

from aider.utils import find_common_root


def test_find_common_root_falls_back_when_paths_are_on_different_drives(tmp_path):
    # Windows os.path.commonpath raises ValueError for paths on different drives.
    # A coder should still use the current directory as its safe root.
    with patch("aider.utils.os.path.commonpath", side_effect=ntpath.commonpath):
        with patch("aider.utils.os.getcwd", return_value=str(tmp_path)):
            assert find_common_root(["C:/project/app.py", "D:/shared/lib.py"]) == str(tmp_path)
