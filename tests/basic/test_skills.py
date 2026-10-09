import hashlib
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from aider.skills import (
    Skill,
    discover_skills,
    load_skill_body,
)

try:
    from aider.skills import (
        build_selector_messages,
        parse_skill_selection,
        select_skills,
    )
except ImportError:
    # These helpers are introduced by Increment 2; keep catalog tests
    # independently collectable while the implementation proceeds by increment.
    pass


class TestSkillCatalog(unittest.TestCase):
    """Coverage for systems/specs/01-skill-catalog.md."""

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.io = MagicMock()

    def tearDown(self):
        self.tempdir.cleanup()

    def write_skill(self, directory, frontmatter, body="Skill body"):
        skill_dir = self.root / ".agents" / "skills" / directory
        skill_dir.mkdir(parents=True, exist_ok=True)
        path = skill_dir / "SKILL.md"
        path.write_text(f"---\n{frontmatter}\n---\n{body}\n", encoding="utf-8")
        return path

    def test_missing_catalog_returns_empty(self):
        self.assertEqual(discover_skills(self.root, self.io), [])
        self.io.tool_warning.assert_not_called()

    def test_skill_directory_without_skill_file_is_skipped_with_warning(self):
        missing_file = self.root / ".agents/skills/missing-file"
        missing_file.mkdir(parents=True)
        self.write_skill("valid", "name: Valid\ndescription: Usable")

        skills = discover_skills(self.root, self.io)

        self.assertEqual([skill.identifier for skill in skills], ["valid"])
        self.io.tool_warning.assert_called_once()
        self.assertIn("missing-file", self.io.tool_warning.call_args.args[0])

    def test_discovery_is_sorted_and_uses_directory_as_identifier(self):
        self.write_skill("z-last", "name: Zed\ndescription: Last skill")
        self.write_skill("a-first", "name: Alpha\ndescription: First skill")

        skills = discover_skills(self.root, self.io)

        self.assertEqual([skill.identifier for skill in skills], ["a-first", "z-last"])
        self.assertEqual(skills[0].name, "Alpha")
        self.assertEqual(skills[0].description, "First skill")
        self.assertEqual(skills[0].path, self.root / ".agents/skills/a-first/SKILL.md")

    def test_discovery_does_not_retain_skill_bodies(self):
        self.write_skill("review", "name: Review\ndescription: Review code", "PRIVATE BODY")

        skills = discover_skills(self.root, self.io)

        self.assertEqual(len(skills), 1)
        self.assertNotIn("PRIVATE BODY", repr(skills[0]))
        self.assertFalse(hasattr(skills[0], "body"))

    def test_discovery_stops_reading_at_the_frontmatter_delimiter(self):
        path = self.write_skill(
            "review", "name: Review\ndescription: Review code", "PRIVATE BODY SENTINEL"
        )
        file_content = path.read_text(encoding="utf-8")
        original_open = Path.open

        class FrontmatterOnlyReader(io.StringIO):
            def __init__(self, value):
                super().__init__(value)
                self.delimiter_count = 0
                self.frontmatter_closed = False

            def readline(self, *args, **kwargs):
                if self.frontmatter_closed:
                    raise AssertionError("discovery read past the frontmatter")
                line = super().readline(*args, **kwargs)
                if line.strip() == "---":
                    self.delimiter_count += 1
                    if self.delimiter_count == 2:
                        self.frontmatter_closed = True
                return line

            def read(self, *args, **kwargs):
                raise AssertionError("discovery read the complete skill file")

            def readlines(self, *args, **kwargs):
                raise AssertionError("discovery read the complete skill file")

        def open_frontmatter_only(file_path, *args, **kwargs):
            if file_path == path:
                return FrontmatterOnlyReader(file_content)
            return original_open(file_path, *args, **kwargs)

        with patch.object(Path, "open", open_frontmatter_only):
            skills = discover_skills(self.root, self.io)

        self.assertEqual([skill.identifier for skill in skills], ["review"])

    def test_body_loader_returns_complete_markdown_without_frontmatter(self):
        self.write_skill("review", "name: Review\ndescription: Review code", "First\n\nSecond")
        skill = discover_skills(self.root, self.io)[0]

        self.assertEqual(load_skill_body(skill), "First\n\nSecond\n")

    def test_body_loader_allows_empty_markdown(self):
        self.write_skill("empty", "name: Empty\ndescription: No instructions", "")
        skill = discover_skills(self.root, self.io)[0]

        self.assertEqual(load_skill_body(skill), "")

    def test_missing_and_malformed_frontmatter_are_skipped(self):
        no_frontmatter = self.root / ".agents/skills/no-frontmatter/SKILL.md"
        no_frontmatter.parent.mkdir(parents=True)
        no_frontmatter.write_text("No metadata", encoding="utf-8")
        self.write_skill("malformed", "name: [unterminated\ndescription: broken")
        self.write_skill("valid", "name: Valid\ndescription: Usable")

        skills = discover_skills(self.root, self.io)

        self.assertEqual([skill.identifier for skill in skills], ["valid"])
        self.assertEqual(self.io.tool_warning.call_count, 2)

    def test_missing_empty_and_non_string_metadata_are_skipped(self):
        cases = {
            "missing-name": "description: Missing name",
            "missing-description": "name: Missing description",
            "empty-name": "name: ''\ndescription: Empty name",
            "empty-description": "name: Empty description\ndescription: ''",
            "non-string-name": "name: 7\ndescription: Numeric name",
            "non-string-description": "name: Numeric description\ndescription: false",
        }
        for directory, frontmatter in cases.items():
            self.write_skill(directory, frontmatter)

        self.assertEqual(discover_skills(self.root, self.io), [])
        self.assertEqual(self.io.tool_warning.call_count, len(cases))
        warnings = repr(self.io.tool_warning.call_args_list)
        for call in self.io.tool_warning.call_args_list:
            self.assertTrue(any(directory in str(arg) for arg in call.args for directory in cases))
        for directory in cases:
            self.assertIn(directory, warnings)

    def test_unreadable_skill_is_warned_and_scanning_continues(self):
        bad_path = self.write_skill("broken", "name: Broken\ndescription: Cannot read")
        self.write_skill("valid", "name: Valid\ndescription: Readable")
        original_open = Path.open

        def open_skill(path, *args, **kwargs):
            if path == bad_path:
                raise OSError("permission denied")
            return original_open(path, *args, **kwargs)

        with patch.object(Path, "open", open_skill):
            skills = discover_skills(self.root, self.io)

        self.assertEqual([skill.identifier for skill in skills], ["valid"])
        self.io.tool_warning.assert_called_once()
        self.assertIn("broken", self.io.tool_warning.call_args.args[0])


class TestSkillSelection(unittest.TestCase):
    """Coverage for systems/specs/02-skill-selection.md."""

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        root = Path(self.tempdir.name)
        review_path = root / "review" / "SKILL.md"
        tests_path = root / "tests" / "SKILL.md"
        review_path.parent.mkdir()
        tests_path.parent.mkdir()
        review_path.write_text("REVIEW BODY SENTINEL", encoding="utf-8")
        tests_path.write_text("TESTS BODY SENTINEL", encoding="utf-8")
        self.catalog = [
            Skill("review", "Review", "Review code quality", review_path),
            Skill("tests", "Tests", "Write useful tests", tests_path),
        ]
        self.io = MagicMock()

    def tearDown(self):
        self.tempdir.cleanup()

    def response(self, content):
        completion = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
        )
        return hashlib.sha1(b"selector"), completion

    def test_selector_context_contains_request_history_and_metadata_only(self):
        conversation = [
            {"role": "user", "content": "Earlier request"},
            {"role": "assistant", "content": "Earlier answer"},
        ]

        messages = build_selector_messages(conversation, "Review this change", self.catalog)
        serialized = repr(messages)

        allowed_values = (
            "Earlier request",
            "Earlier answer",
            "Review this change",
            "review",
            "Review code quality",
            "tests",
            "Write useful tests",
        )
        for allowed in allowed_values:
            self.assertIn(allowed, serialized)
        for excluded in ("REPO MAP", "ATTACHED FILE", "FULL BODY", "SKILL BODY"):
            self.assertNotIn(excluded, serialized)
        self.assertNotIn("REVIEW BODY SENTINEL", serialized)
        self.assertNotIn("TESTS BODY SENTINEL", serialized)

    def test_empty_catalog_skips_model_call(self):
        model = MagicMock()

        self.assertEqual(select_skills(model, self.io, [], "Request", []), [])

        model.send_completion.assert_not_called()

    def test_selection_uses_plain_non_streaming_completion(self):
        model = MagicMock()
        model.send_completion.return_value = self.response('["tests"]')

        selected = select_skills(model, self.io, [], "Write tests", self.catalog)

        self.assertEqual(selected, [self.catalog[1]])
        model.send_completion.assert_called_once()
        args, kwargs = model.send_completion.call_args
        sent_messages = kwargs.get("messages", args[0] if args else None)
        expected_messages = build_selector_messages([], "Write tests", self.catalog)
        self.assertEqual(sent_messages, expected_messages)
        functions = kwargs.get("functions", args[1] if len(args) > 1 else None)
        stream = kwargs.get("stream", args[2] if len(args) > 2 else None)
        self.assertIsNone(functions)
        self.assertFalse(stream)

    def test_empty_single_and_multiple_selections(self):
        for content, expected in (
            ("[]", []),
            ('["review"]', [self.catalog[0]]),
            ('["tests", "review"]', [self.catalog[1], self.catalog[0]]),
        ):
            with self.subTest(content=content):
                self.assertEqual(parse_skill_selection(content, self.catalog), expected)

    def test_duplicate_identifiers_are_removed_in_first_occurrence_order(self):
        selected = parse_skill_selection('["tests", "review", "tests"]', self.catalog)

        self.assertEqual(selected, [self.catalog[1], self.catalog[0]])

    def test_invalid_json_shapes_values_and_unknown_identifiers_select_nothing(self):
        invalid_results = (
            "not json",
            "{}",
            '"review"',
            '["review", 3]',
            '["review", "unknown"]',
        )
        for result in invalid_results:
            with self.subTest(result=result):
                self.assertEqual(parse_skill_selection(result, self.catalog), [])

    def test_provider_failure_warns_and_falls_back_to_empty_selection(self):
        model = MagicMock()
        model.send_completion.side_effect = RuntimeError("provider unavailable")

        self.assertEqual(select_skills(model, self.io, [], "Request", self.catalog), [])

        self.io.tool_warning.assert_called_once()
        self.assertIn("skill", self.io.tool_warning.call_args.args[0].lower())

    def test_invalid_model_response_warns_and_selects_nothing(self):
        invalid_responses = (
            "not json",
            "{}",
            '["review", 7]',
            '["review", "unknown"]',
        )
        for content in invalid_responses:
            with self.subTest(content=content):
                model = MagicMock()
                model.send_completion.return_value = self.response(content)
                io = MagicMock()

                self.assertEqual(select_skills(model, io, [], "Request", self.catalog), [])

                io.tool_warning.assert_called_once()

    def test_retryable_provider_failure_uses_retry_classification(self):
        model = MagicMock()
        model.send_completion.side_effect = [RuntimeError("try again"), self.response('["review"]')]
        with (
            patch("aider.skills.LiteLLMExceptions") as exception_types,
            patch("aider.skills.time.sleep") as sleep,
        ):
            exception_types.return_value.exceptions_tuple.return_value = (RuntimeError,)
            exception_types.return_value.get_ex_info.return_value = SimpleNamespace(
                retry=True, description="temporary provider failure"
            )
            selected = select_skills(model, self.io, [], "Request", self.catalog)

        self.assertEqual(selected, [self.catalog[0]])
        self.assertEqual(model.send_completion.call_count, 2)
        sleep.assert_called_once()


if __name__ == "__main__":
    unittest.main()
