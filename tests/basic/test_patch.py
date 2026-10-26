import unittest
from pathlib import Path
from unittest.mock import patch

from aider.coders import Coder
from aider.io import InputOutput
from aider.models import Model
from aider.utils import ChdirTemporaryDirectory, GitTemporaryDirectory


class TestPatchCoder(unittest.TestCase):
    def make_coder(self, **kwargs):
        io = InputOutput(yes=True, pretty=False, fancy_input=False)
        return Coder.create(
            main_model=Model("gpt-4o"),
            edit_format="patch",
            io=io,
            stream=False,
            **kwargs,
        )

    def add_patch(self, coder, path="hello.py"):
        coder.partial_response_content = (
            f"*** Begin Patch\n*** Add File: {path}\n"
            '+def hello():\n+    print("hello")\n*** End Patch\n'
        )
        return coder.get_edits()

    def test_run_creates_new_file(self):
        with ChdirTemporaryDirectory():
            coder = self.make_coder(use_git=False)
            self.add_patch(coder)
            reply = coder.partial_response_content
            coder.max_reflections = 0

            def send(*args, **kwargs):
                coder.partial_response_content = reply
                coder.partial_response_function_call = {}
                return []

            with patch.object(coder, "send", side_effect=send):
                coder.run(with_message="Create hello.py with a hello() function.")

            self.assertEqual(Path("hello.py").read_text(), 'def hello():\n    print("hello")\n')
            self.assertEqual(coder.num_malformed_responses, 0)
            self.assertIn(coder.abs_root_path("hello.py"), coder.abs_fnames)

    def test_add_with_git(self):
        for auto_commits in (False, True):
            with self.subTest(auto_commits=auto_commits), GitTemporaryDirectory():
                coder = self.make_coder(auto_commits=auto_commits)
                self.add_patch(coder, "nested/hello.py")
                coder.apply_updates()
                self.assertEqual(
                    Path("nested/hello.py").read_text(), 'def hello():\n    print("hello")\n'
                )
                self.assertEqual(coder.num_malformed_responses, 0)
                staged = coder.repo.repo.git.diff("--cached", "--name-only").splitlines()
                self.assertEqual(staged, ["nested/hello.py"] if auto_commits else [])

    def test_add_rejects_existing_files_before_preparation(self):
        for content in ("", "original\n"):
            with self.subTest(content=content), GitTemporaryDirectory():
                path = Path("hello.py")
                path.write_text(content)
                coder = self.make_coder()
                edits = self.add_patch(coder)
                with patch.object(coder.io, "confirm_ask") as confirm:
                    with self.assertRaisesRegex(ValueError, "File already exists"):
                        coder.prepare_to_edit(edits)
                confirm.assert_not_called()
                self.assertEqual(path.read_text(), content)
                self.assertEqual(coder.repo.repo.git.diff("--cached", "--name-only"), "")
                self.assertNotIn(coder.abs_root_path("hello.py"), coder.abs_fnames)

    def test_add_declined(self):
        with ChdirTemporaryDirectory():
            coder = self.make_coder(use_git=False)
            self.add_patch(coder)
            with patch.object(coder.io, "confirm_ask", return_value=False):
                self.assertEqual(coder.apply_updates(), set())
            self.assertFalse(Path("hello.py").exists())
            self.assertNotIn(coder.abs_root_path("hello.py"), coder.abs_fnames)

    def test_add_ignored(self):
        with GitTemporaryDirectory():
            Path(".gitignore").write_text("hello.py\n")
            coder = self.make_coder()
            self.add_patch(coder)
            with patch.object(coder.io, "confirm_ask") as confirm:
                self.assertEqual(coder.apply_updates(), set())
            confirm.assert_not_called()
            self.assertFalse(Path("hello.py").exists())
            self.assertEqual(coder.repo.repo.git.diff("--cached", "--name-only"), "")

    def test_add_dry_run(self):
        with ChdirTemporaryDirectory():
            coder = self.make_coder(use_git=False, dry_run=True)
            self.add_patch(coder, "nested/hello.py")
            coder.apply_updates()
            self.assertEqual(coder.num_malformed_responses, 0)
            self.assertFalse(Path("nested").exists())

    def test_direct_add(self):
        with ChdirTemporaryDirectory():
            coder = self.make_coder(use_git=False)
            edits = self.add_patch(coder, "nested/hello.py")
            coder.apply_edits(edits)
            self.assertEqual(
                Path("nested/hello.py").read_text(), 'def hello():\n    print("hello")\n'
            )

    def test_direct_add_rejects_existing_files(self):
        for content in ("", "original\n"):
            with self.subTest(content=content), ChdirTemporaryDirectory():
                Path("hello.py").write_text(content)
                coder = self.make_coder(use_git=False)
                with self.assertRaisesRegex(ValueError, "File already exists"):
                    coder.apply_edits(self.add_patch(coder))
                self.assertEqual(Path("hello.py").read_text(), content)

    def test_prepared_add_preserves_intervening_content(self):
        with ChdirTemporaryDirectory():
            coder = self.make_coder(use_git=False)
            edits = coder.prepare_to_edit(self.add_patch(coder))
            Path("hello.py").write_text("user content\n")
            with self.assertRaisesRegex(ValueError, "File already exists"):
                coder.apply_edits(edits)
            self.assertEqual(Path("hello.py").read_text(), "user content\n")
            # A failed application must not leave permission to overwrite an empty file.
            Path("hello.py").write_text("")
            with self.assertRaisesRegex(ValueError, "File already exists"):
                coder.apply_edits(edits)

    def test_prepared_add_permission_is_consumed(self):
        with ChdirTemporaryDirectory():
            coder = self.make_coder(use_git=False)
            edits = coder.prepare_to_edit(self.add_patch(coder))
            coder.apply_edits(edits)
            Path("hello.py").write_text("")
            with self.assertRaisesRegex(ValueError, "File already exists"):
                coder.apply_edits(edits)
            with self.assertRaisesRegex(ValueError, "File already exists"):
                coder.prepare_to_edit(edits)

    def test_new_preparation_resets_add_permission(self):
        with ChdirTemporaryDirectory():
            coder = self.make_coder(use_git=False)
            edits = coder.prepare_to_edit(self.add_patch(coder))
            coder.prepare_to_edit([])
            with self.assertRaisesRegex(ValueError, "File already exists"):
                coder.apply_edits(edits)

    def test_failed_preparation_resets_add_permission(self):
        with ChdirTemporaryDirectory():
            coder = self.make_coder(use_git=False)
            edits = self.add_patch(coder)
            with patch.object(coder, "dirty_commit", side_effect=RuntimeError("failed")):
                with self.assertRaisesRegex(RuntimeError, "failed"):
                    coder.prepare_to_edit(edits)
            self.assertTrue(Path("hello.py").exists())
            with self.assertRaisesRegex(ValueError, "File already exists"):
                coder.apply_edits(edits)

    def test_add_normalizes_paths(self):
        with ChdirTemporaryDirectory():
            coder = self.make_coder(use_git=False)
            edits = coder.prepare_to_edit(self.add_patch(coder, "./hello.py"))
            edits[0][1].path = coder.abs_root_path("hello.py")
            coder.apply_edits(edits)
            self.assertEqual(Path("hello.py").read_text(), 'def hello():\n    print("hello")\n')

    def test_add_only_applies_confirmed_files(self):
        with ChdirTemporaryDirectory():
            coder = self.make_coder(use_git=False)
            self.add_patch(coder)
            coder.partial_response_content = coder.partial_response_content.replace(
                "*** End Patch", "*** Add File: declined.py\n+declined\n*** End Patch"
            )
            with patch.object(coder.io, "confirm_ask", side_effect=[True, False]):
                coder.apply_updates()
            self.assertEqual(Path("hello.py").read_text(), 'def hello():\n    print("hello")\n')
            self.assertFalse(Path("declined.py").exists())

    def test_duplicate_add_paths_cannot_reuse_placeholder(self):
        with ChdirTemporaryDirectory():
            coder = self.make_coder(use_git=False)
            edits = self.add_patch(coder, "hello.py") + self.add_patch(coder, "./hello.py")
            edits[0][1].new_content = ""
            edits = coder.prepare_to_edit(edits)
            with self.assertRaisesRegex(ValueError, "File already exists"):
                coder.apply_edits(edits)
            self.assertEqual(Path("hello.py").read_text(), "\n")
