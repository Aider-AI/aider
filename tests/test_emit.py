import io
import os
import shutil
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from aider.emit import emit, read_template


class TestEmit(TestCase):
    def setUp(self):
        self.original_cwd = os.getcwd()
        self.tempdir = tempfile.mkdtemp()
        os.chdir(self.tempdir)

    def tearDown(self):
        os.chdir(self.original_cwd)
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def test_emit_stdout(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            emit(".aider.conf.yml", None)
            output = mock_stdout.getvalue()
            expected_output = read_template(".aider.conf.yml")
            self.assertEqual(output.strip(), expected_output.strip())

    def test_emit_new_file(self):
        new_file_path = Path(self.tempdir) / ".aider.conf.yml"
        self.assertFalse(new_file_path.exists())

        emit(".aider.conf.yml", self.tempdir)
        self.assertTrue(new_file_path.exists())
        expected_content = read_template(".aider.conf.yml")
        self.assertEqual(new_file_path.read_text().strip(), expected_content.strip())

    def test_emit_nonexistent_template_file(self):
        invalid_template_file = "nonexistent_template.yml"
        with patch("sys.stderr", new_callable=io.StringIO) as mock_stderr:
            emit(invalid_template_file, self.tempdir)
            error_output = mock_stderr.getvalue()
            self.assertIn(
                f"Error: The template file {invalid_template_file} does not exist.", error_output
            )
        existing_file_path = Path(self.tempdir) / ".aider.conf.yml"
        existing_content = "# existing content\ndark-mode: false"
        existing_file_path.write_text(existing_content)

    def test_emit_existing_file(self):
        existing_file_path = Path(self.tempdir) / ".aider.conf.yml"
        existing_content = "# existing content\ndark-mode: false"
        existing_file_path.write_text(existing_content)

        with patch("sys.stderr", new_callable=io.StringIO) as mock_stderr:
            emit(".aider.conf.yml", self.tempdir)
            error_output = mock_stderr.getvalue()
            self.assertIn(
                f"Refusing to overwrite the existing file at: {existing_file_path}", error_output
            )
            self.assertEqual(existing_file_path.read_text(), existing_content)

    def test_emit_nonexistent_directory(self):
        nonexistent_dir = Path(self.tempdir) / "nonexistent_subdir"
        with patch("sys.stderr", new_callable=io.StringIO) as mock_stderr:
            emit(".aider.conf.yml", str(nonexistent_dir))
            error_output = mock_stderr.getvalue()
            self.assertIn(f"Error: The directory {nonexistent_dir} does not exist.", error_output)
            self.assertFalse((nonexistent_dir / ".aider.conf.yml").exists())
