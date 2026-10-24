import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from benchmark.enable_tests import (
    enable_java_tests,
    enable_javascript_tests,
    enable_tests,
)


class TestEnableJavascriptTests(unittest.TestCase):
    def test_enables_all_supported_skip_forms(self):
        content = """xtest('one', () => {});
  xit ('two', () => {});
test.skip('three', () => {});
\tit.skip ('four', () => {});
"""
        expected = """test('one', () => {});
  it ('two', () => {});
test('three', () => {});
\tit ('four', () => {});
"""

        self.assertEqual(enable_javascript_tests(content), expected)

    def test_preserves_active_tests_and_non_test_references(self):
        content = """test('active', () => {});
it('active', () => {});
const example = "test.skip('documented')";
// xit('commented out', () => {});
"""

        self.assertEqual(enable_javascript_tests(content), content)

    def test_is_idempotent(self):
        content = "xtest('one', () => {});\nit.skip('two', () => {});\n"
        enabled = enable_javascript_tests(content)

        self.assertEqual(enable_javascript_tests(enabled), enabled)


class TestEnableJavaTests(unittest.TestCase):
    def test_removes_disabled_annotations_with_and_without_reason(self):
        content = """    @Disabled
    @Test
    void first() {}

\t@Disabled("not implemented")
    @Test
    void second() {}
"""
        expected = """    @Test
    void first() {}

    @Test
    void second() {}
"""

        self.assertEqual(enable_java_tests(content), expected)

    def test_preserves_active_tests_and_non_annotation_references(self):
        content = """@Test
void active() {}
String example = "@Disabled";
// @Disabled
"""

        self.assertEqual(enable_java_tests(content), content)

    def test_is_idempotent(self):
        content = '@Disabled("later")\n@Test\nvoid first() {}\n'
        enabled = enable_java_tests(content)

        self.assertEqual(enable_java_tests(enabled), enabled)


class TestEnableTestsFiles(unittest.TestCase):
    def test_updates_javascript_fixture(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "example.spec.js"
            path.write_text("test.skip('one', () => {});\n")

            enable_tests(path)

            self.assertEqual(path.read_text(), "test('one', () => {});\n")

    def test_updates_java_fixture(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "ExampleTest.java"
            path.write_text("@Disabled\n@Test\nvoid example() {}\n")

            enable_tests(path)

            self.assertEqual(path.read_text(), "@Test\nvoid example() {}\n")


if __name__ == "__main__":
    unittest.main()
