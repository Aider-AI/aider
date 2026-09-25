import os
import tempfile
import unittest

import yaml

from aider.soul import (
    SOUL_FILENAMES,
    denial_message,
    entry_lint,
    find_soul_file,
    is_protected_edit_target,
    load_soul,
    parse_soul,
)
from aider.soul_eval import lint_suite, parse_suite

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures", "soul")


def fixture(name):
    with open(os.path.join(FIXTURE_DIR, name), encoding="utf-8") as fh:
        return fh.read()


def valid_soul_and_suite():
    soul = parse_soul(fixture("SOUL.md"), os.path.join(FIXTURE_DIR, "SOUL.md"))
    suite = parse_suite(fixture("SOUL.suite.yaml"))
    return soul, suite


class TestSoulLoader(unittest.TestCase):
    def test_finds_soul_walking_up(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sub = os.path.join(tmpdir, "a", "b")
            os.makedirs(sub)
            with open(os.path.join(tmpdir, "SOUL.md"), "w") as fh:
                fh.write("# soul")
            self.assertEqual(find_soul_file(sub), os.path.join(tmpdir, "SOUL.md"))

    def test_stops_at_git_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "SOUL.md"), "w") as fh:
                fh.write("# stray soul above the repo")
            repo = os.path.join(tmpdir, "repo")
            sub = os.path.join(repo, "sub")
            os.makedirs(os.path.join(repo, ".git"))
            os.makedirs(sub)
            # the stray SOUL.md above the repo root is never picked up
            self.assertIsNone(find_soul_file(sub))

    def test_returns_none_when_absent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertIsNone(find_soul_file(tmpdir))

    def test_parses_axioms_values_and_purpose(self):
        soul, _ = valid_soul_and_suite()
        self.assertEqual(soul.version, "0.1.0")
        self.assertEqual(soul.agent, "fixture-agent")
        self.assertIn("test fixture soul", soul.purpose)
        self.assertEqual([a["id"] for a in soul.axioms], ["AX-01", "AX-02"])
        self.assertIn("tool output", soul.axioms[0]["statement"])
        self.assertEqual(soul.values, ["Care", "Honesty"])

    def test_resolves_suite_path_from_frontmatter(self):
        soul, _ = valid_soul_and_suite()
        self.assertTrue(soul.suite_path.endswith("SOUL.suite.yaml"))

    def test_accepts_soul_with_paired_probes(self):
        soul, suite = valid_soul_and_suite()
        self.assertEqual(entry_lint(soul, suite), [])

    def test_rejects_orphan_axiom_naming_it(self):
        soul, suite = valid_soul_and_suite()
        without_ax02 = dict(suite)
        without_ax02["section_a"] = [p for p in suite["section_a"] if p.get("axiom") != "AX-02"]
        errs = entry_lint(soul, without_ax02)
        self.assertTrue(errs)
        self.assertTrue(any("AX-02" in e for e in errs))

    def test_rejects_soul_with_no_axioms(self):
        soul, suite = valid_soul_and_suite()
        soul.axioms = []
        errs = entry_lint(soul, suite)
        self.assertTrue(any("no axioms" in e for e in errs))

    def test_compiled_section_states_axiom_precedence(self):
        soul, _ = valid_soul_and_suite()
        compiled = soul.compile_system_section()
        self.assertIn("[AX-01]", compiled)
        self.assertIn("[AX-02]", compiled)
        self.assertIn("1. Care", compiled)
        self.assertIn("2. Honesty", compiled)
        self.assertIn("SOUL.md", compiled)
        self.assertIn("may never edit", compiled)

    def test_load_soul_rejects_orphan_at_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "SOUL.md"), "w") as fh:
                fh.write(fixture("SOUL.md"))
            suite = parse_suite(fixture("SOUL.suite.yaml"))
            suite["section_a"] = [p for p in suite["section_a"] if p.get("axiom") != "AX-02"]
            with open(os.path.join(tmpdir, "SOUL.suite.yaml"), "w") as fh:
                yaml.safe_dump(suite, fh)
            soul, errors = load_soul(tmpdir)
            self.assertIsNone(soul)
            self.assertTrue(any("AX-02" in e for e in errors))

    def test_load_soul_requires_paired_suite(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "SOUL.md"), "w") as fh:
                fh.write(fixture("SOUL.md"))
            soul, errors = load_soul(tmpdir)
            self.assertIsNone(soul)
            self.assertTrue(any("suite" in e for e in errors))

    def test_load_soul_returns_none_without_soul_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            soul, errors = load_soul(tmpdir)
            self.assertIsNone(soul)
            self.assertEqual(errors, [])


class TestSoulGuard(unittest.TestCase):
    def test_protects_soul_file_and_eval_artifacts(self):
        self.assertTrue(is_protected_edit_target("SOUL.md"))
        self.assertTrue(is_protected_edit_target("src/SOUL.md"))
        self.assertTrue(is_protected_edit_target("SOUL.suite.yaml"))
        self.assertTrue(is_protected_edit_target("evals/SOUL.baseline.json"))
        self.assertTrue(is_protected_edit_target("sub\\dir\\SOUL.md"))

    def test_does_not_protect_ordinary_files(self):
        self.assertFalse(is_protected_edit_target("notes.md"))
        self.assertFalse(is_protected_edit_target("src/soul.py"))
        self.assertFalse(is_protected_edit_target("SOUL.md.bak"))
        self.assertFalse(is_protected_edit_target(None))

    def test_protected_filenames(self):
        self.assertEqual(set(SOUL_FILENAMES), {"SOUL.md", "SOUL.suite.yaml", "SOUL.baseline.json"})

    def test_denial_names_the_legitimate_path(self):
        msg = denial_message("SOUL.md")
        self.assertIn("formation guard", msg)
        self.assertIn("SOUL.md", msg)
        self.assertIn("human edit", msg)

    def test_lint_suite_names_orphan_axiom(self):
        _, suite = valid_soul_and_suite()
        without_benign = dict(suite)
        without_benign["section_a"] = [
            p for p in suite["section_a"] if p.get("kind") != "must_not_refuse"
        ]
        errs = lint_suite(without_benign)
        self.assertTrue(any("AX-01" in e and "must_not_refuse" in e for e in errs))


if __name__ == "__main__":
    unittest.main()
