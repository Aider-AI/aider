#!/usr/bin/env python3

import unittest

from aider.coders.search_replace import (
    RelativeIndenter,
    all_preprocs,
    flexible_search_and_replace,
    search_and_replace,
)


class TestRelativeIndenter(unittest.TestCase):
    def test_round_trip_spaces(self):
        text = "class A:\n    def f(self):\n        return 1\n"
        ri = RelativeIndenter([text, text, text])
        self.assertEqual(ri.make_absolute(ri.make_relative(text)), text)

    def test_round_trip_tabs(self):
        text = "class A:\n\tdef f(self):\n\t\treturn 1\n"
        ri = RelativeIndenter([text, text, text])
        self.assertEqual(ri.make_absolute(ri.make_relative(text)), text)

    def test_round_trip_mixed_tabs_and_spaces(self):
        text = "if x:\n\ta = 1\n          b = 2\n"
        ri = RelativeIndenter([text, text, text])
        self.assertEqual(ri.make_absolute(ri.make_relative(text)), text)

    def test_outdented_block_edit_keeps_untouched_lines(self):
        original = "if x:\n\ta = 1\n\tb = 2\n          d = 3\n"
        search = "a = 1\nb = 2\n"
        replace = "a = 1\nb = 3\n"

        res = flexible_search_and_replace(
            (search, replace, original),
            [(search_and_replace, all_preprocs)],
        )

        self.assertEqual(res, "if x:\n\ta = 1\n\tb = 3\n          d = 3\n")


if __name__ == "__main__":
    unittest.main()
