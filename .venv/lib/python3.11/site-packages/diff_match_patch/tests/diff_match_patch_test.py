#!/usr/bin/python3

"""Diff Match and Patch -- Test harness
Copyright 2018 The diff-match-patch Authors.
https://github.com/google/diff-match-patch

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import importlib
import os
import sys
import time
import unittest

parentPath = os.path.abspath("..")
if parentPath not in sys.path:
    sys.path.insert(0, parentPath)
import diff_match_patch as dmp_module

# Force a module reload.  Allows one to edit the DMP module and rerun the tests
# without leaving the Python interpreter.
importlib.reload(dmp_module)


class DiffMatchPatchTest(unittest.TestCase):
    def setUp(self):
        "Test harness for dmp_module."
        self.dmp = dmp_module.diff_match_patch()

    def diff_rebuildtexts(self, diffs):
        # Construct the two texts which made up the diff originally.
        text1 = ""
        text2 = ""
        for x in range(0, len(diffs)):
            if diffs[x][0] != dmp_module.diff_match_patch.DIFF_INSERT:
                text1 += diffs[x][1]
            if diffs[x][0] != dmp_module.diff_match_patch.DIFF_DELETE:
                text2 += diffs[x][1]
        return (text1, text2)


class DiffTest(DiffMatchPatchTest):
    """DIFF TEST FUNCTIONS"""

    def testDiffCommonPrefix(self):
        # Detect any common prefix.
        # Null case.
        self.assertEqual(0, self.dmp.diff_commonPrefix("abc", "xyz"))

        # Non-null case.
        self.assertEqual(4, self.dmp.diff_commonPrefix("1234abcdef", "1234xyz"))

        # Whole case.
        self.assertEqual(4, self.dmp.diff_commonPrefix("1234", "1234xyz"))

    def testDiffCommonSuffix(self):
        # Detect any common suffix.
        # Null case.
        self.assertEqual(0, self.dmp.diff_commonSuffix("abc", "xyz"))

        # Non-null case.
        self.assertEqual(4, self.dmp.diff_commonSuffix("abcdef1234", "xyz1234"))

        # Whole case.
        self.assertEqual(4, self.dmp.diff_commonSuffix("1234", "xyz1234"))

    def testDiffCommonOverlap(self):
        # Null case.
        self.assertEqual(0, self.dmp.diff_commonOverlap("", "abcd"))

        # Whole case.
        self.assertEqual(3, self.dmp.diff_commonOverlap("abc", "abcd"))

        # No overlap.
        self.assertEqual(0, self.dmp.diff_commonOverlap("123456", "abcd"))

        # Overlap.
        self.assertEqual(3, self.dmp.diff_commonOverlap("123456xxx", "xxxabcd"))

        # Unicode.
        # Some overly clever languages (C#) may treat ligatures as equal to their
        # component letters.  E.g. U+FB01 == 'fi'
        self.assertEqual(0, self.dmp.diff_commonOverlap("fi", "\ufb01i"))

    def testDiffHalfMatch(self):
        # Detect a halfmatch.
        self.dmp.Diff_Timeout = 1
        # No match.
        self.assertEqual(None, self.dmp.diff_halfMatch("1234567890", "abcdef"))

        self.assertEqual(None, self.dmp.diff_halfMatch("12345", "23"))

        # Single Match.
        self.assertEqual(
            ("12", "90", "a", "z", "345678"),
            self.dmp.diff_halfMatch("1234567890", "a345678z"),
        )

        self.assertEqual(
            ("a", "z", "12", "90", "345678"),
            self.dmp.diff_halfMatch("a345678z", "1234567890"),
        )

        self.assertEqual(
            ("abc", "z", "1234", "0", "56789"),
            self.dmp.diff_halfMatch("abc56789z", "1234567890"),
        )

        self.assertEqual(
            ("a", "xyz", "1", "7890", "23456"),
            self.dmp.diff_halfMatch("a23456xyz", "1234567890"),
        )

        # Multiple Matches.
        self.assertEqual(
            ("12123", "123121", "a", "z", "1234123451234"),
            self.dmp.diff_halfMatch("121231234123451234123121", "a1234123451234z"),
        )

        self.assertEqual(
            ("", "-=-=-=-=-=", "x", "", "x-=-=-=-=-=-=-="),
            self.dmp.diff_halfMatch("x-=-=-=-=-=-=-=-=-=-=-=-=", "xx-=-=-=-=-=-=-="),
        )

        self.assertEqual(
            ("-=-=-=-=-=", "", "", "y", "-=-=-=-=-=-=-=y"),
            self.dmp.diff_halfMatch("-=-=-=-=-=-=-=-=-=-=-=-=y", "-=-=-=-=-=-=-=yy"),
        )

        # Non-optimal halfmatch.
        # Optimal diff would be -q+x=H-i+e=lloHe+Hu=llo-Hew+y not -qHillo+x=HelloHe-w+Hulloy
        self.assertEqual(
            ("qHillo", "w", "x", "Hulloy", "HelloHe"),
            self.dmp.diff_halfMatch("qHilloHelloHew", "xHelloHeHulloy"),
        )

        # Optimal no halfmatch.
        self.dmp.Diff_Timeout = 0
        self.assertEqual(
            None, self.dmp.diff_halfMatch("qHilloHelloHew", "xHelloHeHulloy")
        )

    def testDiffLinesToChars(self):
        # Convert lines down to characters.
        self.assertEqual(
            ("\x01\x02\x01", "\x02\x01\x02", ["", "alpha\n", "beta\n"]),
            self.dmp.diff_linesToChars("alpha\nbeta\nalpha\n", "beta\nalpha\nbeta\n"),
        )

        self.assertEqual(
            ("", "\x01\x02\x03\x03", ["", "alpha\r\n", "beta\r\n", "\r\n"]),
            self.dmp.diff_linesToChars("", "alpha\r\nbeta\r\n\r\n\r\n"),
        )

        self.assertEqual(
            ("\x01", "\x02", ["", "a", "b"]), self.dmp.diff_linesToChars("a", "b")
        )

        # More than 256 to reveal any 8-bit limitations.
        n = 300
        lineList = []
        charList = []
        for i in range(1, n + 1):
            lineList.append(str(i) + "\n")
            charList.append(chr(i))
        self.assertEqual(n, len(lineList))
        lines = "".join(lineList)
        chars = "".join(charList)
        self.assertEqual(n, len(chars))
        lineList.insert(0, "")
        self.assertEqual((chars, "", lineList), self.dmp.diff_linesToChars(lines, ""))

    def testDiffCharsToLines(self):
        # Convert chars up to lines.
        diffs = [
            (self.dmp.DIFF_EQUAL, "\x01\x02\x01"),
            (self.dmp.DIFF_INSERT, "\x02\x01\x02"),
        ]
        self.dmp.diff_charsToLines(diffs, ["", "alpha\n", "beta\n"])
        self.assertEqual(
            [
                (self.dmp.DIFF_EQUAL, "alpha\nbeta\nalpha\n"),
                (self.dmp.DIFF_INSERT, "beta\nalpha\nbeta\n"),
            ],
            diffs,
        )

        # More than 256 to reveal any 8-bit limitations.
        n = 300
        lineList = []
        charList = []
        for i in range(1, n + 1):
            lineList.append(str(i) + "\n")
            charList.append(chr(i))
        self.assertEqual(n, len(lineList))
        lines = "".join(lineList)
        chars = "".join(charList)
        self.assertEqual(n, len(chars))
        lineList.insert(0, "")
        diffs = [(self.dmp.DIFF_DELETE, chars)]
        self.dmp.diff_charsToLines(diffs, lineList)
        self.assertEqual([(self.dmp.DIFF_DELETE, lines)], diffs)

        # More than 1,114,112 to verify any 17 * 16-bit limitation.
        lineList = []
        for i in range(1, 1115000 + 1):
            lineList.append(str(i) + "\n")
        chars = "".join(lineList)
        results = self.dmp.diff_linesToChars(chars, "")
        diffs = [(self.dmp.DIFF_INSERT, results[0])]
        self.dmp.diff_charsToLines(diffs, results[2])
        self.assertEqual(chars, diffs[0][1])

    def testDiffCleanupMerge(self):
        # Cleanup a messy diff.
        # Null case.
        diffs = []
        self.dmp.diff_cleanupMerge(diffs)
        self.assertEqual([], diffs)

        # No change case.
        diffs = [
            (self.dmp.DIFF_EQUAL, "a"),
            (self.dmp.DIFF_DELETE, "b"),
            (self.dmp.DIFF_INSERT, "c"),
        ]
        self.dmp.diff_cleanupMerge(diffs)
        self.assertEqual(
            [
                (self.dmp.DIFF_EQUAL, "a"),
                (self.dmp.DIFF_DELETE, "b"),
                (self.dmp.DIFF_INSERT, "c"),
            ],
            diffs,
        )

        # Merge equalities.
        diffs = [
            (self.dmp.DIFF_EQUAL, "a"),
            (self.dmp.DIFF_EQUAL, "b"),
            (self.dmp.DIFF_EQUAL, "c"),
        ]
        self.dmp.diff_cleanupMerge(diffs)
        self.assertEqual([(self.dmp.DIFF_EQUAL, "abc")], diffs)

        # Merge deletions.
        diffs = [
            (self.dmp.DIFF_DELETE, "a"),
            (self.dmp.DIFF_DELETE, "b"),
            (self.dmp.DIFF_DELETE, "c"),
        ]
        self.dmp.diff_cleanupMerge(diffs)
        self.assertEqual([(self.dmp.DIFF_DELETE, "abc")], diffs)

        # Merge insertions.
        diffs = [
            (self.dmp.DIFF_INSERT, "a"),
            (self.dmp.DIFF_INSERT, "b"),
            (self.dmp.DIFF_INSERT, "c"),
        ]
        self.dmp.diff_cleanupMerge(diffs)
        self.assertEqual([(self.dmp.DIFF_INSERT, "abc")], diffs)

        # Merge interweave.
        diffs = [
            (self.dmp.DIFF_DELETE, "a"),
            (self.dmp.DIFF_INSERT, "b"),
            (self.dmp.DIFF_DELETE, "c"),
            (self.dmp.DIFF_INSERT, "d"),
            (self.dmp.DIFF_EQUAL, "e"),
            (self.dmp.DIFF_EQUAL, "f"),
        ]
        self.dmp.diff_cleanupMerge(diffs)
        self.assertEqual(
            [
                (self.dmp.DIFF_DELETE, "ac"),
                (self.dmp.DIFF_INSERT, "bd"),
                (self.dmp.DIFF_EQUAL, "ef"),
            ],
            diffs,
        )

        # Prefix and suffix detection.
        diffs = [
            (self.dmp.DIFF_DELETE, "a"),
            (self.dmp.DIFF_INSERT, "abc"),
            (self.dmp.DIFF_DELETE, "dc"),
        ]
        self.dmp.diff_cleanupMerge(diffs)
        self.assertEqual(
            [
                (self.dmp.DIFF_EQUAL, "a"),
                (self.dmp.DIFF_DELETE, "d"),
                (self.dmp.DIFF_INSERT, "b"),
                (self.dmp.DIFF_EQUAL, "c"),
            ],
            diffs,
        )

        # Prefix and suffix detection with equalities.
        diffs = [
            (self.dmp.DIFF_EQUAL, "x"),
            (self.dmp.DIFF_DELETE, "a"),
            (self.dmp.DIFF_INSERT, "abc"),
            (self.dmp.DIFF_DELETE, "dc"),
            (self.dmp.DIFF_EQUAL, "y"),
        ]
        self.dmp.diff_cleanupMerge(diffs)
        self.assertEqual(
            [
                (self.dmp.DIFF_EQUAL, "xa"),
                (self.dmp.DIFF_DELETE, "d"),
                (self.dmp.DIFF_INSERT, "b"),
                (self.dmp.DIFF_EQUAL, "cy"),
            ],
            diffs,
        )

        # Slide edit left.
        diffs = [
            (self.dmp.DIFF_EQUAL, "a"),
            (self.dmp.DIFF_INSERT, "ba"),
            (self.dmp.DIFF_EQUAL, "c"),
        ]
        self.dmp.diff_cleanupMerge(diffs)
        self.assertEqual(
            [(self.dmp.DIFF_INSERT, "ab"), (self.dmp.DIFF_EQUAL, "ac")], diffs
        )

        # Slide edit right.
        diffs = [
            (self.dmp.DIFF_EQUAL, "c"),
            (self.dmp.DIFF_INSERT, "ab"),
            (self.dmp.DIFF_EQUAL, "a"),
        ]
        self.dmp.diff_cleanupMerge(diffs)
        self.assertEqual(
            [(self.dmp.DIFF_EQUAL, "ca"), (self.dmp.DIFF_INSERT, "ba")], diffs
        )

        # Slide edit left recursive.
        diffs = [
            (self.dmp.DIFF_EQUAL, "a"),
            (self.dmp.DIFF_DELETE, "b"),
            (self.dmp.DIFF_EQUAL, "c"),
            (self.dmp.DIFF_DELETE, "ac"),
            (self.dmp.DIFF_EQUAL, "x"),
        ]
        self.dmp.diff_cleanupMerge(diffs)
        self.assertEqual(
            [(self.dmp.DIFF_DELETE, "abc"), (self.dmp.DIFF_EQUAL, "acx")], diffs
        )

        # Slide edit right recursive.
        diffs = [
            (self.dmp.DIFF_EQUAL, "x"),
            (self.dmp.DIFF_DELETE, "ca"),
            (self.dmp.DIFF_EQUAL, "c"),
            (self.dmp.DIFF_DELETE, "b"),
            (self.dmp.DIFF_EQUAL, "a"),
        ]
        self.dmp.diff_cleanupMerge(diffs)
        self.assertEqual(
            [(self.dmp.DIFF_EQUAL, "xca"), (self.dmp.DIFF_DELETE, "cba")], diffs
        )

        # Empty merge.
        diffs = [
            (self.dmp.DIFF_DELETE, "b"),
            (self.dmp.DIFF_INSERT, "ab"),
            (self.dmp.DIFF_EQUAL, "c"),
        ]
        self.dmp.diff_cleanupMerge(diffs)
        self.assertEqual(
            [(self.dmp.DIFF_INSERT, "a"), (self.dmp.DIFF_EQUAL, "bc")], diffs
        )

        # Empty equality.
        diffs = [
            (self.dmp.DIFF_EQUAL, ""),
            (self.dmp.DIFF_INSERT, "a"),
            (self.dmp.DIFF_EQUAL, "b"),
        ]
        self.dmp.diff_cleanupMerge(diffs)
        self.assertEqual(
            [(self.dmp.DIFF_INSERT, "a"), (self.dmp.DIFF_EQUAL, "b")], diffs
        )

    def testDiffCleanupSemanticLossless(self):
        # Slide diffs to match logical boundaries.
        # Null case.
        diffs = []
        self.dmp.diff_cleanupSemanticLossless(diffs)
        self.assertEqual([], diffs)

        # Blank lines.
        diffs = [
            (self.dmp.DIFF_EQUAL, "AAA\r\n\r\nBBB"),
            (self.dmp.DIFF_INSERT, "\r\nDDD\r\n\r\nBBB"),
            (self.dmp.DIFF_EQUAL, "\r\nEEE"),
        ]
        self.dmp.diff_cleanupSemanticLossless(diffs)
        self.assertEqual(
            [
                (self.dmp.DIFF_EQUAL, "AAA\r\n\r\n"),
                (self.dmp.DIFF_INSERT, "BBB\r\nDDD\r\n\r\n"),
                (self.dmp.DIFF_EQUAL, "BBB\r\nEEE"),
            ],
            diffs,
        )

        # Line boundaries.
        diffs = [
            (self.dmp.DIFF_EQUAL, "AAA\r\nBBB"),
            (self.dmp.DIFF_INSERT, " DDD\r\nBBB"),
            (self.dmp.DIFF_EQUAL, " EEE"),
        ]
        self.dmp.diff_cleanupSemanticLossless(diffs)
        self.assertEqual(
            [
                (self.dmp.DIFF_EQUAL, "AAA\r\n"),
                (self.dmp.DIFF_INSERT, "BBB DDD\r\n"),
                (self.dmp.DIFF_EQUAL, "BBB EEE"),
            ],
            diffs,
        )

        # Word boundaries.
        diffs = [
            (self.dmp.DIFF_EQUAL, "The c"),
            (self.dmp.DIFF_INSERT, "ow and the c"),
            (self.dmp.DIFF_EQUAL, "at."),
        ]
        self.dmp.diff_cleanupSemanticLossless(diffs)
        self.assertEqual(
            [
                (self.dmp.DIFF_EQUAL, "The "),
                (self.dmp.DIFF_INSERT, "cow and the "),
                (self.dmp.DIFF_EQUAL, "cat."),
            ],
            diffs,
        )

        # Alphanumeric boundaries.
        diffs = [
            (self.dmp.DIFF_EQUAL, "The-c"),
            (self.dmp.DIFF_INSERT, "ow-and-the-c"),
            (self.dmp.DIFF_EQUAL, "at."),
        ]
        self.dmp.diff_cleanupSemanticLossless(diffs)
        self.assertEqual(
            [
                (self.dmp.DIFF_EQUAL, "The-"),
                (self.dmp.DIFF_INSERT, "cow-and-the-"),
                (self.dmp.DIFF_EQUAL, "cat."),
            ],
            diffs,
        )

        # Hitting the start.
        diffs = [
            (self.dmp.DIFF_EQUAL, "a"),
            (self.dmp.DIFF_DELETE, "a"),
            (self.dmp.DIFF_EQUAL, "ax"),
        ]
        self.dmp.diff_cleanupSemanticLossless(diffs)
        self.assertEqual(
            [(self.dmp.DIFF_DELETE, "a"), (self.dmp.DIFF_EQUAL, "aax")], diffs
        )

        # Hitting the end.
        diffs = [
            (self.dmp.DIFF_EQUAL, "xa"),
            (self.dmp.DIFF_DELETE, "a"),
            (self.dmp.DIFF_EQUAL, "a"),
        ]
        self.dmp.diff_cleanupSemanticLossless(diffs)
        self.assertEqual(
            [(self.dmp.DIFF_EQUAL, "xaa"), (self.dmp.DIFF_DELETE, "a")], diffs
        )

        # Sentence boundaries.
        diffs = [
            (self.dmp.DIFF_EQUAL, "The xxx. The "),
            (self.dmp.DIFF_INSERT, "zzz. The "),
            (self.dmp.DIFF_EQUAL, "yyy."),
        ]
        self.dmp.diff_cleanupSemanticLossless(diffs)
        self.assertEqual(
            [
                (self.dmp.DIFF_EQUAL, "The xxx."),
                (self.dmp.DIFF_INSERT, " The zzz."),
                (self.dmp.DIFF_EQUAL, " The yyy."),
            ],
            diffs,
        )

    def testDiffCleanupSemantic(self):
        # Cleanup semantically trivial equalities.
        # Null case.
        diffs = []
        self.dmp.diff_cleanupSemantic(diffs)
        self.assertEqual([], diffs)

        # No elimination #1.
        diffs = [
            (self.dmp.DIFF_DELETE, "ab"),
            (self.dmp.DIFF_INSERT, "cd"),
            (self.dmp.DIFF_EQUAL, "12"),
            (self.dmp.DIFF_DELETE, "e"),
        ]
        self.dmp.diff_cleanupSemantic(diffs)
        self.assertEqual(
            [
                (self.dmp.DIFF_DELETE, "ab"),
                (self.dmp.DIFF_INSERT, "cd"),
                (self.dmp.DIFF_EQUAL, "12"),
                (self.dmp.DIFF_DELETE, "e"),
            ],
            diffs,
        )

        # No elimination #2.
        diffs = [
            (self.dmp.DIFF_DELETE, "abc"),
            (self.dmp.DIFF_INSERT, "ABC"),
            (self.dmp.DIFF_EQUAL, "1234"),
            (self.dmp.DIFF_DELETE, "wxyz"),
        ]
        self.dmp.diff_cleanupSemantic(diffs)
        self.assertEqual(
            [
                (self.dmp.DIFF_DELETE, "abc"),
                (self.dmp.DIFF_INSERT, "ABC"),
                (self.dmp.DIFF_EQUAL, "1234"),
                (self.dmp.DIFF_DELETE, "wxyz"),
            ],
            diffs,
        )

        # Simple elimination.
        diffs = [
            (self.dmp.DIFF_DELETE, "a"),
            (self.dmp.DIFF_EQUAL, "b"),
            (self.dmp.DIFF_DELETE, "c"),
        ]
        self.dmp.diff_cleanupSemantic(diffs)
        self.assertEqual(
            [(self.dmp.DIFF_DELETE, "abc"), (self.dmp.DIFF_INSERT, "b")], diffs
        )

        # Backpass elimination.
        diffs = [
            (self.dmp.DIFF_DELETE, "ab"),
            (self.dmp.DIFF_EQUAL, "cd"),
            (self.dmp.DIFF_DELETE, "e"),
            (self.dmp.DIFF_EQUAL, "f"),
            (self.dmp.DIFF_INSERT, "g"),
        ]
        self.dmp.diff_cleanupSemantic(diffs)
        self.assertEqual(
            [(self.dmp.DIFF_DELETE, "abcdef"), (self.dmp.DIFF_INSERT, "cdfg")], diffs
        )

        # Multiple eliminations.
        diffs = [
            (self.dmp.DIFF_INSERT, "1"),
            (self.dmp.DIFF_EQUAL, "A"),
            (self.dmp.DIFF_DELETE, "B"),
            (self.dmp.DIFF_INSERT, "2"),
            (self.dmp.DIFF_EQUAL, "_"),
            (self.dmp.DIFF_INSERT, "1"),
            (self.dmp.DIFF_EQUAL, "A"),
            (self.dmp.DIFF_DELETE, "B"),
            (self.dmp.DIFF_INSERT, "2"),
        ]
        self.dmp.diff_cleanupSemantic(diffs)
        self.assertEqual(
            [(self.dmp.DIFF_DELETE, "AB_AB"), (self.dmp.DIFF_INSERT, "1A2_1A2")], diffs
        )

        # Word boundaries.
        diffs = [
            (self.dmp.DIFF_EQUAL, "The c"),
            (self.dmp.DIFF_DELETE, "ow and the c"),
            (self.dmp.DIFF_EQUAL, "at."),
        ]
        self.dmp.diff_cleanupSemantic(diffs)
        self.assertEqual(
            [
                (self.dmp.DIFF_EQUAL, "The "),
                (self.dmp.DIFF_DELETE, "cow and the "),
                (self.dmp.DIFF_EQUAL, "cat."),
            ],
            diffs,
        )

        # No overlap elimination.
        diffs = [(self.dmp.DIFF_DELETE, "abcxx"), (self.dmp.DIFF_INSERT, "xxdef")]
        self.dmp.diff_cleanupSemantic(diffs)
        self.assertEqual(
            [(self.dmp.DIFF_DELETE, "abcxx"), (self.dmp.DIFF_INSERT, "xxdef")], diffs
        )

        # Overlap elimination.
        diffs = [(self.dmp.DIFF_DELETE, "abcxxx"), (self.dmp.DIFF_INSERT, "xxxdef")]
        self.dmp.diff_cleanupSemantic(diffs)
        self.assertEqual(
            [
                (self.dmp.DIFF_DELETE, "abc"),
                (self.dmp.DIFF_EQUAL, "xxx"),
                (self.dmp.DIFF_INSERT, "def"),
            ],
            diffs,
        )

        # Reverse overlap elimination.
        diffs = [(self.dmp.DIFF_DELETE, "xxxabc"), (self.dmp.DIFF_INSERT, "defxxx")]
        self.dmp.diff_cleanupSemantic(diffs)
        self.assertEqual(
            [
                (self.dmp.DIFF_INSERT, "def"),
                (self.dmp.DIFF_EQUAL, "xxx"),
                (self.dmp.DIFF_DELETE, "abc"),
            ],
            diffs,
        )

        # Two overlap eliminations.
        diffs = [
            (self.dmp.DIFF_DELETE, "abcd1212"),
            (self.dmp.DIFF_INSERT, "1212efghi"),
            (self.dmp.DIFF_EQUAL, "----"),
            (self.dmp.DIFF_DELETE, "A3"),
            (self.dmp.DIFF_INSERT, "3BC"),
        ]
        self.dmp.diff_cleanupSemantic(diffs)
        self.assertEqual(
            [
                (self.dmp.DIFF_DELETE, "abcd"),
                (self.dmp.DIFF_EQUAL, "1212"),
                (self.dmp.DIFF_INSERT, "efghi"),
                (self.dmp.DIFF_EQUAL, "----"),
                (self.dmp.DIFF_DELETE, "A"),
                (self.dmp.DIFF_EQUAL, "3"),
                (self.dmp.DIFF_INSERT, "BC"),
            ],
            diffs,
        )

    def testDiffCleanupEfficiency(self):
        # Cleanup operationally trivial equalities.
        self.dmp.Diff_EditCost = 4
        # Null case.
        diffs = []
        self.dmp.diff_cleanupEfficiency(diffs)
        self.assertEqual([], diffs)

        # No elimination.
        diffs = [
            (self.dmp.DIFF_DELETE, "ab"),
            (self.dmp.DIFF_INSERT, "12"),
            (self.dmp.DIFF_EQUAL, "wxyz"),
            (self.dmp.DIFF_DELETE, "cd"),
            (self.dmp.DIFF_INSERT, "34"),
        ]
        self.dmp.diff_cleanupEfficiency(diffs)
        self.assertEqual(
            [
                (self.dmp.DIFF_DELETE, "ab"),
                (self.dmp.DIFF_INSERT, "12"),
                (self.dmp.DIFF_EQUAL, "wxyz"),
                (self.dmp.DIFF_DELETE, "cd"),
                (self.dmp.DIFF_INSERT, "34"),
            ],
            diffs,
        )

        # Four-edit elimination.
        diffs = [
            (self.dmp.DIFF_DELETE, "ab"),
            (self.dmp.DIFF_INSERT, "12"),
            (self.dmp.DIFF_EQUAL, "xyz"),
            (self.dmp.DIFF_DELETE, "cd"),
            (self.dmp.DIFF_INSERT, "34"),
        ]
        self.dmp.diff_cleanupEfficiency(diffs)
        self.assertEqual(
            [(self.dmp.DIFF_DELETE, "abxyzcd"), (self.dmp.DIFF_INSERT, "12xyz34")],
            diffs,
        )

        # Three-edit elimination.
        diffs = [
            (self.dmp.DIFF_INSERT, "12"),
            (self.dmp.DIFF_EQUAL, "x"),
            (self.dmp.DIFF_DELETE, "cd"),
            (self.dmp.DIFF_INSERT, "34"),
        ]
        self.dmp.diff_cleanupEfficiency(diffs)
        self.assertEqual(
            [(self.dmp.DIFF_DELETE, "xcd"), (self.dmp.DIFF_INSERT, "12x34")], diffs
        )

        # Backpass elimination.
        diffs = [
            (self.dmp.DIFF_DELETE, "ab"),
            (self.dmp.DIFF_INSERT, "12"),
            (self.dmp.DIFF_EQUAL, "xy"),
            (self.dmp.DIFF_INSERT, "34"),
            (self.dmp.DIFF_EQUAL, "z"),
            (self.dmp.DIFF_DELETE, "cd"),
            (self.dmp.DIFF_INSERT, "56"),
        ]
        self.dmp.diff_cleanupEfficiency(diffs)
        self.assertEqual(
            [(self.dmp.DIFF_DELETE, "abxyzcd"), (self.dmp.DIFF_INSERT, "12xy34z56")],
            diffs,
        )

        # High cost elimination.
        self.dmp.Diff_EditCost = 5
        diffs = [
            (self.dmp.DIFF_DELETE, "ab"),
            (self.dmp.DIFF_INSERT, "12"),
            (self.dmp.DIFF_EQUAL, "wxyz"),
            (self.dmp.DIFF_DELETE, "cd"),
            (self.dmp.DIFF_INSERT, "34"),
        ]
        self.dmp.diff_cleanupEfficiency(diffs)
        self.assertEqual(
            [(self.dmp.DIFF_DELETE, "abwxyzcd"), (self.dmp.DIFF_INSERT, "12wxyz34")],
            diffs,
        )
        self.dmp.Diff_EditCost = 4

    def testDiffPrettyHtml(self):
        # Pretty print.
        diffs = [
            (self.dmp.DIFF_EQUAL, "a\n"),
            (self.dmp.DIFF_DELETE, "<B>b</B>"),
            (self.dmp.DIFF_INSERT, "c&d"),
        ]
        self.assertEqual(
            '<span>a&para;<br></span><del style="background:#ffe6e6;">&lt;B&gt;b&lt;/B&gt;</del><ins style="background:#e6ffe6;">c&amp;d</ins>',
            self.dmp.diff_prettyHtml(diffs),
        )

    def testDiffText(self):
        # Compute the source and destination texts.
        diffs = [
            (self.dmp.DIFF_EQUAL, "jump"),
            (self.dmp.DIFF_DELETE, "s"),
            (self.dmp.DIFF_INSERT, "ed"),
            (self.dmp.DIFF_EQUAL, " over "),
            (self.dmp.DIFF_DELETE, "the"),
            (self.dmp.DIFF_INSERT, "a"),
            (self.dmp.DIFF_EQUAL, " lazy"),
        ]
        self.assertEqual("jumps over the lazy", self.dmp.diff_text1(diffs))

        self.assertEqual("jumped over a lazy", self.dmp.diff_text2(diffs))

    def testDiffDelta(self):
        # Convert a diff into delta string.
        diffs = [
            (self.dmp.DIFF_EQUAL, "jump"),
            (self.dmp.DIFF_DELETE, "s"),
            (self.dmp.DIFF_INSERT, "ed"),
            (self.dmp.DIFF_EQUAL, " over "),
            (self.dmp.DIFF_DELETE, "the"),
            (self.dmp.DIFF_INSERT, "a"),
            (self.dmp.DIFF_EQUAL, " lazy"),
            (self.dmp.DIFF_INSERT, "old dog"),
        ]
        text1 = self.dmp.diff_text1(diffs)
        self.assertEqual("jumps over the lazy", text1)

        delta = self.dmp.diff_toDelta(diffs)
        self.assertEqual("=4\t-1\t+ed\t=6\t-3\t+a\t=5\t+old dog", delta)

        # Convert delta string into a diff.
        self.assertEqual(diffs, self.dmp.diff_fromDelta(text1, delta))

        # Generates error (19 != 20).
        try:
            self.dmp.diff_fromDelta(text1 + "x", delta)
            self.assertFalse(True)
        except ValueError:
            # Exception expected.
            pass

        # Generates error (19 != 18).
        try:
            self.dmp.diff_fromDelta(text1[1:], delta)
            self.assertFalse(True)
        except ValueError:
            # Exception expected.
            pass

        # Generates error (%c3%xy invalid Unicode).
        # Note: Python 3 can decode this.
        # try:
        #  self.dmp.diff_fromDelta("", "+%c3xy")
        #  self.assertFalse(True)
        # except ValueError:
        #  # Exception expected.
        #  pass

        # Test deltas with special characters.
        diffs = [
            (self.dmp.DIFF_EQUAL, "\u0680 \x00 \t %"),
            (self.dmp.DIFF_DELETE, "\u0681 \x01 \n ^"),
            (self.dmp.DIFF_INSERT, "\u0682 \x02 \\ |"),
        ]
        text1 = self.dmp.diff_text1(diffs)
        self.assertEqual("\u0680 \x00 \t %\u0681 \x01 \n ^", text1)

        delta = self.dmp.diff_toDelta(diffs)
        self.assertEqual("=7\t-7\t+%DA%82 %02 %5C %7C", delta)

        # Convert delta string into a diff.
        self.assertEqual(diffs, self.dmp.diff_fromDelta(text1, delta))

        # Verify pool of unchanged characters.
        diffs = [
            (
                self.dmp.DIFF_INSERT,
                "A-Z a-z 0-9 - _ . ! ~ * ' ( ) ; / ? : @ & = + $ , # ",
            )
        ]
        text2 = self.dmp.diff_text2(diffs)
        self.assertEqual("A-Z a-z 0-9 - _ . ! ~ * ' ( ) ; / ? : @ & = + $ , # ", text2)

        delta = self.dmp.diff_toDelta(diffs)
        self.assertEqual("+A-Z a-z 0-9 - _ . ! ~ * ' ( ) ; / ? : @ & = + $ , # ", delta)

        # Convert delta string into a diff.
        self.assertEqual(diffs, self.dmp.diff_fromDelta("", delta))

        # 160 kb string.
        a = "abcdefghij"
        for i in range(14):
            a += a
        diffs = [(self.dmp.DIFF_INSERT, a)]
        delta = self.dmp.diff_toDelta(diffs)
        self.assertEqual("+" + a, delta)

        # Convert delta string into a diff.
        self.assertEqual(diffs, self.dmp.diff_fromDelta("", delta))

    def testDiffXIndex(self):
        # Translate a location in text1 to text2.
        self.assertEqual(
            5,
            self.dmp.diff_xIndex(
                [
                    (self.dmp.DIFF_DELETE, "a"),
                    (self.dmp.DIFF_INSERT, "1234"),
                    (self.dmp.DIFF_EQUAL, "xyz"),
                ],
                2,
            ),
        )

        # Translation on deletion.
        self.assertEqual(
            1,
            self.dmp.diff_xIndex(
                [
                    (self.dmp.DIFF_EQUAL, "a"),
                    (self.dmp.DIFF_DELETE, "1234"),
                    (self.dmp.DIFF_EQUAL, "xyz"),
                ],
                3,
            ),
        )

    def testDiffLevenshtein(self):
        # Levenshtein with trailing equality.
        self.assertEqual(
            4,
            self.dmp.diff_levenshtein(
                [
                    (self.dmp.DIFF_DELETE, "abc"),
                    (self.dmp.DIFF_INSERT, "1234"),
                    (self.dmp.DIFF_EQUAL, "xyz"),
                ]
            ),
        )
        # Levenshtein with leading equality.
        self.assertEqual(
            4,
            self.dmp.diff_levenshtein(
                [
                    (self.dmp.DIFF_EQUAL, "xyz"),
                    (self.dmp.DIFF_DELETE, "abc"),
                    (self.dmp.DIFF_INSERT, "1234"),
                ]
            ),
        )
        # Levenshtein with middle equality.
        self.assertEqual(
            7,
            self.dmp.diff_levenshtein(
                [
                    (self.dmp.DIFF_DELETE, "abc"),
                    (self.dmp.DIFF_EQUAL, "xyz"),
                    (self.dmp.DIFF_INSERT, "1234"),
                ]
            ),
        )

    def testDiffBisect(self):
        # Normal.
        a = "cat"
        b = "map"
        # Since the resulting diff hasn't been normalized, it would be ok if
        # the insertion and deletion pairs are swapped.
        # If the order changes, tweak this test as required.
        self.assertEqual(
            [
                (self.dmp.DIFF_DELETE, "c"),
                (self.dmp.DIFF_INSERT, "m"),
                (self.dmp.DIFF_EQUAL, "a"),
                (self.dmp.DIFF_DELETE, "t"),
                (self.dmp.DIFF_INSERT, "p"),
            ],
            self.dmp.diff_bisect(a, b, sys.maxsize),
        )

        # Timeout.
        self.assertEqual(
            [(self.dmp.DIFF_DELETE, "cat"), (self.dmp.DIFF_INSERT, "map")],
            self.dmp.diff_bisect(a, b, 0),
        )

    def testDiffMain(self):
        # Perform a trivial diff.
        # Null case.
        self.assertEqual([], self.dmp.diff_main("", "", False))

        # Equality.
        self.assertEqual(
            [(self.dmp.DIFF_EQUAL, "abc")], self.dmp.diff_main("abc", "abc", False)
        )

        # Simple insertion.
        self.assertEqual(
            [
                (self.dmp.DIFF_EQUAL, "ab"),
                (self.dmp.DIFF_INSERT, "123"),
                (self.dmp.DIFF_EQUAL, "c"),
            ],
            self.dmp.diff_main("abc", "ab123c", False),
        )

        # Simple deletion.
        self.assertEqual(
            [
                (self.dmp.DIFF_EQUAL, "a"),
                (self.dmp.DIFF_DELETE, "123"),
                (self.dmp.DIFF_EQUAL, "bc"),
            ],
            self.dmp.diff_main("a123bc", "abc", False),
        )

        # Two insertions.
        self.assertEqual(
            [
                (self.dmp.DIFF_EQUAL, "a"),
                (self.dmp.DIFF_INSERT, "123"),
                (self.dmp.DIFF_EQUAL, "b"),
                (self.dmp.DIFF_INSERT, "456"),
                (self.dmp.DIFF_EQUAL, "c"),
            ],
            self.dmp.diff_main("abc", "a123b456c", False),
        )

        # Two deletions.
        self.assertEqual(
            [
                (self.dmp.DIFF_EQUAL, "a"),
                (self.dmp.DIFF_DELETE, "123"),
                (self.dmp.DIFF_EQUAL, "b"),
                (self.dmp.DIFF_DELETE, "456"),
                (self.dmp.DIFF_EQUAL, "c"),
            ],
            self.dmp.diff_main("a123b456c", "abc", False),
        )

        # Perform a real diff.
        # Switch off the timeout.
        self.dmp.Diff_Timeout = 0
        # Simple cases.
        self.assertEqual(
            [(self.dmp.DIFF_DELETE, "a"), (self.dmp.DIFF_INSERT, "b")],
            self.dmp.diff_main("a", "b", False),
        )

        self.assertEqual(
            [
                (self.dmp.DIFF_DELETE, "Apple"),
                (self.dmp.DIFF_INSERT, "Banana"),
                (self.dmp.DIFF_EQUAL, "s are a"),
                (self.dmp.DIFF_INSERT, "lso"),
                (self.dmp.DIFF_EQUAL, " fruit."),
            ],
            self.dmp.diff_main("Apples are a fruit.", "Bananas are also fruit.", False),
        )

        self.assertEqual(
            [
                (self.dmp.DIFF_DELETE, "a"),
                (self.dmp.DIFF_INSERT, "\u0680"),
                (self.dmp.DIFF_EQUAL, "x"),
                (self.dmp.DIFF_DELETE, "\t"),
                (self.dmp.DIFF_INSERT, "\x00"),
            ],
            self.dmp.diff_main("ax\t", "\u0680x\x00", False),
        )

        # Overlaps.
        self.assertEqual(
            [
                (self.dmp.DIFF_DELETE, "1"),
                (self.dmp.DIFF_EQUAL, "a"),
                (self.dmp.DIFF_DELETE, "y"),
                (self.dmp.DIFF_EQUAL, "b"),
                (self.dmp.DIFF_DELETE, "2"),
                (self.dmp.DIFF_INSERT, "xab"),
            ],
            self.dmp.diff_main("1ayb2", "abxab", False),
        )

        self.assertEqual(
            [
                (self.dmp.DIFF_INSERT, "xaxcx"),
                (self.dmp.DIFF_EQUAL, "abc"),
                (self.dmp.DIFF_DELETE, "y"),
            ],
            self.dmp.diff_main("abcy", "xaxcxabc", False),
        )

        self.assertEqual(
            [
                (self.dmp.DIFF_DELETE, "ABCD"),
                (self.dmp.DIFF_EQUAL, "a"),
                (self.dmp.DIFF_DELETE, "="),
                (self.dmp.DIFF_INSERT, "-"),
                (self.dmp.DIFF_EQUAL, "bcd"),
                (self.dmp.DIFF_DELETE, "="),
                (self.dmp.DIFF_INSERT, "-"),
                (self.dmp.DIFF_EQUAL, "efghijklmnopqrs"),
                (self.dmp.DIFF_DELETE, "EFGHIJKLMNOefg"),
            ],
            self.dmp.diff_main(
                "ABCDa=bcd=efghijklmnopqrsEFGHIJKLMNOefg",
                "a-bcd-efghijklmnopqrs",
                False,
            ),
        )

        # Large equality.
        self.assertEqual(
            [
                (self.dmp.DIFF_INSERT, " "),
                (self.dmp.DIFF_EQUAL, "a"),
                (self.dmp.DIFF_INSERT, "nd"),
                (self.dmp.DIFF_EQUAL, " [[Pennsylvania]]"),
                (self.dmp.DIFF_DELETE, " and [[New"),
            ],
            self.dmp.diff_main(
                "a [[Pennsylvania]] and [[New", " and [[Pennsylvania]]", False
            ),
        )

        # Timeout.
        self.dmp.Diff_Timeout = 0.1  # 100ms
        a = "`Twas brillig, and the slithy toves\nDid gyre and gimble in the wabe:\nAll mimsy were the borogoves,\nAnd the mome raths outgrabe.\n"
        b = "I am the very model of a modern major general,\nI've information vegetable, animal, and mineral,\nI know the kings of England, and I quote the fights historical,\nFrom Marathon to Waterloo, in order categorical.\n"
        # Increase the text lengths by 1024 times to ensure a timeout.
        for i in range(10):
            a += a
            b += b
        startTime = time.time()
        self.dmp.diff_main(a, b)
        endTime = time.time()
        # Test that we took at least the timeout period.
        self.assertTrue(self.dmp.Diff_Timeout <= endTime - startTime)
        # Test that we didn't take forever (be forgiving).
        # Theoretically this test could fail very occasionally if the
        # OS task swaps or locks up for a second at the wrong moment.
        self.assertTrue(self.dmp.Diff_Timeout * 2 > endTime - startTime)
        self.dmp.Diff_Timeout = 0

        # Test the linemode speedup.
        # Must be long to pass the 100 char cutoff.
        # Simple line-mode.
        a = "1234567890\n" * 13
        b = "abcdefghij\n" * 13
        self.assertEqual(
            self.dmp.diff_main(a, b, False), self.dmp.diff_main(a, b, True)
        )

        # Single line-mode.
        a = "1234567890" * 13
        b = "abcdefghij" * 13
        self.assertEqual(
            self.dmp.diff_main(a, b, False), self.dmp.diff_main(a, b, True)
        )

        # Overlap line-mode.
        a = "1234567890\n" * 13
        b = "abcdefghij\n1234567890\n1234567890\n1234567890\nabcdefghij\n1234567890\n1234567890\n1234567890\nabcdefghij\n1234567890\n1234567890\n1234567890\nabcdefghij\n"
        texts_linemode = self.diff_rebuildtexts(self.dmp.diff_main(a, b, True))
        texts_textmode = self.diff_rebuildtexts(self.dmp.diff_main(a, b, False))
        self.assertEqual(texts_textmode, texts_linemode)

        # Test null inputs.
        try:
            self.dmp.diff_main(None, None)
            self.assertFalse(True)
        except ValueError:
            # Exception expected.
            pass


class MatchTest(DiffMatchPatchTest):
    """MATCH TEST FUNCTIONS"""

    def testMatchAlphabet(self):
        # Initialise the bitmasks for Bitap.
        self.assertEqual({"a": 4, "b": 2, "c": 1}, self.dmp.match_alphabet("abc"))

        self.assertEqual({"a": 37, "b": 18, "c": 8}, self.dmp.match_alphabet("abcaba"))

    def testMatchBitap(self):
        self.dmp.Match_Distance = 100
        self.dmp.Match_Threshold = 0.5
        # Exact matches.
        self.assertEqual(5, self.dmp.match_bitap("abcdefghijk", "fgh", 5))

        self.assertEqual(5, self.dmp.match_bitap("abcdefghijk", "fgh", 0))

        # Fuzzy matches.
        self.assertEqual(4, self.dmp.match_bitap("abcdefghijk", "efxhi", 0))

        self.assertEqual(2, self.dmp.match_bitap("abcdefghijk", "cdefxyhijk", 5))

        self.assertEqual(-1, self.dmp.match_bitap("abcdefghijk", "bxy", 1))

        # Overflow.
        self.assertEqual(2, self.dmp.match_bitap("123456789xx0", "3456789x0", 2))

        self.assertEqual(0, self.dmp.match_bitap("abcdef", "xxabc", 4))

        self.assertEqual(3, self.dmp.match_bitap("abcdef", "defyy", 4))

        self.assertEqual(0, self.dmp.match_bitap("abcdef", "xabcdefy", 0))

        # Threshold test.
        self.dmp.Match_Threshold = 0.4
        self.assertEqual(4, self.dmp.match_bitap("abcdefghijk", "efxyhi", 1))

        self.dmp.Match_Threshold = 0.3
        self.assertEqual(-1, self.dmp.match_bitap("abcdefghijk", "efxyhi", 1))

        self.dmp.Match_Threshold = 0.0
        self.assertEqual(1, self.dmp.match_bitap("abcdefghijk", "bcdef", 1))
        self.dmp.Match_Threshold = 0.5

        # Multiple select.
        self.assertEqual(0, self.dmp.match_bitap("abcdexyzabcde", "abccde", 3))

        self.assertEqual(8, self.dmp.match_bitap("abcdexyzabcde", "abccde", 5))

        # Distance test.
        self.dmp.Match_Distance = 10  # Strict location.
        self.assertEqual(
            -1, self.dmp.match_bitap("abcdefghijklmnopqrstuvwxyz", "abcdefg", 24)
        )

        self.assertEqual(
            0, self.dmp.match_bitap("abcdefghijklmnopqrstuvwxyz", "abcdxxefg", 1)
        )

        self.dmp.Match_Distance = 1000  # Loose location.
        self.assertEqual(
            0, self.dmp.match_bitap("abcdefghijklmnopqrstuvwxyz", "abcdefg", 24)
        )

    def testMatchMain(self):
        # Full match.
        # Shortcut matches.
        self.assertEqual(0, self.dmp.match_main("abcdef", "abcdef", 1000))

        self.assertEqual(-1, self.dmp.match_main("", "abcdef", 1))

        self.assertEqual(3, self.dmp.match_main("abcdef", "", 3))

        self.assertEqual(3, self.dmp.match_main("abcdef", "de", 3))

        self.assertEqual(3, self.dmp.match_main("abcdef", "defy", 4))

        self.assertEqual(0, self.dmp.match_main("abcdef", "abcdefy", 0))

        # Complex match.
        self.dmp.Match_Threshold = 0.7
        self.assertEqual(
            4,
            self.dmp.match_main(
                "I am the very model of a modern major general.", " that berry ", 5
            ),
        )
        self.dmp.Match_Threshold = 0.5

        # Test null inputs.
        try:
            self.dmp.match_main(None, None, 0)
            self.assertFalse(True)
        except ValueError:
            # Exception expected.
            pass


class PatchTest(DiffMatchPatchTest):
    """PATCH TEST FUNCTIONS"""

    def testPatchObj(self):
        # Patch Object.
        p = dmp_module.patch_obj()
        p.start1 = 20
        p.start2 = 21
        p.length1 = 18
        p.length2 = 17
        p.diffs = [
            (self.dmp.DIFF_EQUAL, "jump"),
            (self.dmp.DIFF_DELETE, "s"),
            (self.dmp.DIFF_INSERT, "ed"),
            (self.dmp.DIFF_EQUAL, " over "),
            (self.dmp.DIFF_DELETE, "the"),
            (self.dmp.DIFF_INSERT, "a"),
            (self.dmp.DIFF_EQUAL, "\nlaz"),
        ]
        strp = str(p)
        self.assertEqual(
            "@@ -21,18 +22,17 @@\n jump\n-s\n+ed\n  over \n-the\n+a\n %0Alaz\n", strp
        )

    def testPatchFromText(self):
        self.assertEqual([], self.dmp.patch_fromText(""))

        strp = "@@ -21,18 +22,17 @@\n jump\n-s\n+ed\n  over \n-the\n+a\n %0Alaz\n"
        self.assertEqual(strp, str(self.dmp.patch_fromText(strp)[0]))

        self.assertEqual(
            "@@ -1 +1 @@\n-a\n+b\n",
            str(self.dmp.patch_fromText("@@ -1 +1 @@\n-a\n+b\n")[0]),
        )

        self.assertEqual(
            "@@ -1,3 +0,0 @@\n-abc\n",
            str(self.dmp.patch_fromText("@@ -1,3 +0,0 @@\n-abc\n")[0]),
        )

        self.assertEqual(
            "@@ -0,0 +1,3 @@\n+abc\n",
            str(self.dmp.patch_fromText("@@ -0,0 +1,3 @@\n+abc\n")[0]),
        )

        # Generates error.
        try:
            self.dmp.patch_fromText("Bad\nPatch\n")
            self.assertFalse(True)
        except ValueError:
            # Exception expected.
            pass

    def testPatchToText(self):
        strp = "@@ -21,18 +22,17 @@\n jump\n-s\n+ed\n  over \n-the\n+a\n  laz\n"
        p = self.dmp.patch_fromText(strp)
        self.assertEqual(strp, self.dmp.patch_toText(p))

        strp = (
            "@@ -1,9 +1,9 @@\n-f\n+F\n oo+fooba\n@@ -7,9 +7,9 @@\n obar\n-,\n+.\n tes\n"
        )
        p = self.dmp.patch_fromText(strp)
        self.assertEqual(strp, self.dmp.patch_toText(p))

    def testPatchAddContext(self):
        self.dmp.Patch_Margin = 4
        p = self.dmp.patch_fromText("@@ -21,4 +21,10 @@\n-jump\n+somersault\n")[0]
        self.dmp.patch_addContext(p, "The quick brown fox jumps over the lazy dog.")
        self.assertEqual(
            "@@ -17,12 +17,18 @@\n fox \n-jump\n+somersault\n s ov\n", str(p)
        )

        # Same, but not enough trailing context.
        p = self.dmp.patch_fromText("@@ -21,4 +21,10 @@\n-jump\n+somersault\n")[0]
        self.dmp.patch_addContext(p, "The quick brown fox jumps.")
        self.assertEqual(
            "@@ -17,10 +17,16 @@\n fox \n-jump\n+somersault\n s.\n", str(p)
        )

        # Same, but not enough leading context.
        p = self.dmp.patch_fromText("@@ -3 +3,2 @@\n-e\n+at\n")[0]
        self.dmp.patch_addContext(p, "The quick brown fox jumps.")
        self.assertEqual("@@ -1,7 +1,8 @@\n Th\n-e\n+at\n  qui\n", str(p))

        # Same, but with ambiguity.
        p = self.dmp.patch_fromText("@@ -3 +3,2 @@\n-e\n+at\n")[0]
        self.dmp.patch_addContext(
            p, "The quick brown fox jumps.  The quick brown fox crashes."
        )
        self.assertEqual(
            "@@ -1,27 +1,28 @@\n Th\n-e\n+at\n  quick brown fox jumps. \n", str(p)
        )

    def testPatchMake(self):
        # Null case.
        patches = self.dmp.patch_make("", "")
        self.assertEqual("", self.dmp.patch_toText(patches))

        text1 = "The quick brown fox jumps over the lazy dog."
        text2 = "That quick brown fox jumped over a lazy dog."
        # Text2+Text1 inputs.
        expectedPatch = "@@ -1,8 +1,7 @@\n Th\n-at\n+e\n  qui\n@@ -21,17 +21,18 @@\n jump\n-ed\n+s\n  over \n-a\n+the\n  laz\n"
        # The second patch must be "-21,17 +21,18", not "-22,17 +21,18" due to rolling context.
        patches = self.dmp.patch_make(text2, text1)
        self.assertEqual(expectedPatch, self.dmp.patch_toText(patches))

        # Text1+Text2 inputs.
        expectedPatch = "@@ -1,11 +1,12 @@\n Th\n-e\n+at\n  quick b\n@@ -22,18 +22,17 @@\n jump\n-s\n+ed\n  over \n-the\n+a\n  laz\n"
        patches = self.dmp.patch_make(text1, text2)
        self.assertEqual(expectedPatch, self.dmp.patch_toText(patches))

        # Diff input.
        diffs = self.dmp.diff_main(text1, text2, False)
        patches = self.dmp.patch_make(diffs)
        self.assertEqual(expectedPatch, self.dmp.patch_toText(patches))

        # Text1+Diff inputs.
        patches = self.dmp.patch_make(text1, diffs)
        self.assertEqual(expectedPatch, self.dmp.patch_toText(patches))

        # Text1+Text2+Diff inputs (deprecated).
        patches = self.dmp.patch_make(text1, text2, diffs)
        self.assertEqual(expectedPatch, self.dmp.patch_toText(patches))

        # Character encoding.
        patches = self.dmp.patch_make("`1234567890-=[]\\;',./", '~!@#$%^&*()_+{}|:"<>?')
        self.assertEqual(
            "@@ -1,21 +1,21 @@\n-%601234567890-=%5B%5D%5C;',./\n+~!@#$%25%5E&*()_+%7B%7D%7C:%22%3C%3E?\n",
            self.dmp.patch_toText(patches),
        )

        # Character decoding.
        diffs = [
            (self.dmp.DIFF_DELETE, "`1234567890-=[]\\;',./"),
            (self.dmp.DIFF_INSERT, '~!@#$%^&*()_+{}|:"<>?'),
        ]
        self.assertEqual(
            diffs,
            self.dmp.patch_fromText(
                "@@ -1,21 +1,21 @@\n-%601234567890-=%5B%5D%5C;',./\n+~!@#$%25%5E&*()_+%7B%7D%7C:%22%3C%3E?\n"
            )[0].diffs,
        )

        # Long string with repeats.
        text1 = ""
        for x in range(100):
            text1 += "abcdef"
        text2 = text1 + "123"
        expectedPatch = "@@ -573,28 +573,31 @@\n cdefabcdefabcdefabcdefabcdef\n+123\n"
        patches = self.dmp.patch_make(text1, text2)
        self.assertEqual(expectedPatch, self.dmp.patch_toText(patches))

        # Test null inputs.
        try:
            self.dmp.patch_make(None, None)
            self.assertFalse(True)
        except ValueError:
            # Exception expected.
            pass

    def testPatchSplitMax(self):
        # Assumes that Match_MaxBits is 32.
        patches = self.dmp.patch_make(
            "abcdefghijklmnopqrstuvwxyz01234567890",
            "XabXcdXefXghXijXklXmnXopXqrXstXuvXwxXyzX01X23X45X67X89X0",
        )
        self.dmp.patch_splitMax(patches)
        self.assertEqual(
            "@@ -1,32 +1,46 @@\n+X\n ab\n+X\n cd\n+X\n ef\n+X\n gh\n+X\n ij\n+X\n kl\n+X\n mn\n+X\n op\n+X\n qr\n+X\n st\n+X\n uv\n+X\n wx\n+X\n yz\n+X\n 012345\n@@ -25,13 +39,18 @@\n zX01\n+X\n 23\n+X\n 45\n+X\n 67\n+X\n 89\n+X\n 0\n",
            self.dmp.patch_toText(patches),
        )

        patches = self.dmp.patch_make(
            "abcdef1234567890123456789012345678901234567890123456789012345678901234567890uvwxyz",
            "abcdefuvwxyz",
        )
        oldToText = self.dmp.patch_toText(patches)
        self.dmp.patch_splitMax(patches)
        self.assertEqual(oldToText, self.dmp.patch_toText(patches))

        patches = self.dmp.patch_make(
            "1234567890123456789012345678901234567890123456789012345678901234567890",
            "abc",
        )
        self.dmp.patch_splitMax(patches)
        self.assertEqual(
            "@@ -1,32 +1,4 @@\n-1234567890123456789012345678\n 9012\n@@ -29,32 +1,4 @@\n-9012345678901234567890123456\n 7890\n@@ -57,14 +1,3 @@\n-78901234567890\n+abc\n",
            self.dmp.patch_toText(patches),
        )

        patches = self.dmp.patch_make(
            "abcdefghij , h : 0 , t : 1 abcdefghij , h : 0 , t : 1 abcdefghij , h : 0 , t : 1",
            "abcdefghij , h : 1 , t : 1 abcdefghij , h : 1 , t : 1 abcdefghij , h : 0 , t : 1",
        )
        self.dmp.patch_splitMax(patches)
        self.assertEqual(
            "@@ -2,32 +2,32 @@\n bcdefghij , h : \n-0\n+1\n  , t : 1 abcdef\n@@ -29,32 +29,32 @@\n bcdefghij , h : \n-0\n+1\n  , t : 1 abcdef\n",
            self.dmp.patch_toText(patches),
        )

    def testPatchAddPadding(self):
        # Both edges full.
        patches = self.dmp.patch_make("", "test")
        self.assertEqual("@@ -0,0 +1,4 @@\n+test\n", self.dmp.patch_toText(patches))
        self.dmp.patch_addPadding(patches)
        self.assertEqual(
            "@@ -1,8 +1,12 @@\n %01%02%03%04\n+test\n %01%02%03%04\n",
            self.dmp.patch_toText(patches),
        )

        # Both edges partial.
        patches = self.dmp.patch_make("XY", "XtestY")
        self.assertEqual(
            "@@ -1,2 +1,6 @@\n X\n+test\n Y\n", self.dmp.patch_toText(patches)
        )
        self.dmp.patch_addPadding(patches)
        self.assertEqual(
            "@@ -2,8 +2,12 @@\n %02%03%04X\n+test\n Y%01%02%03\n",
            self.dmp.patch_toText(patches),
        )

        # Both edges none.
        patches = self.dmp.patch_make("XXXXYYYY", "XXXXtestYYYY")
        self.assertEqual(
            "@@ -1,8 +1,12 @@\n XXXX\n+test\n YYYY\n", self.dmp.patch_toText(patches)
        )
        self.dmp.patch_addPadding(patches)
        self.assertEqual(
            "@@ -5,8 +5,12 @@\n XXXX\n+test\n YYYY\n", self.dmp.patch_toText(patches)
        )

    def testPatchApply(self):
        self.dmp.Match_Distance = 1000
        self.dmp.Match_Threshold = 0.5
        self.dmp.Patch_DeleteThreshold = 0.5
        # Null case.
        patches = self.dmp.patch_make("", "")
        results = self.dmp.patch_apply(patches, "Hello world.")
        self.assertEqual(("Hello world.", []), results)

        # Exact match.
        patches = self.dmp.patch_make(
            "The quick brown fox jumps over the lazy dog.",
            "That quick brown fox jumped over a lazy dog.",
        )
        results = self.dmp.patch_apply(
            patches, "The quick brown fox jumps over the lazy dog."
        )
        self.assertEqual(
            ("That quick brown fox jumped over a lazy dog.", [True, True]), results
        )

        # Partial match.
        results = self.dmp.patch_apply(
            patches, "The quick red rabbit jumps over the tired tiger."
        )
        self.assertEqual(
            ("That quick red rabbit jumped over a tired tiger.", [True, True]), results
        )

        # Failed match.
        results = self.dmp.patch_apply(
            patches, "I am the very model of a modern major general."
        )
        self.assertEqual(
            ("I am the very model of a modern major general.", [False, False]), results
        )

        # Big delete, small change.
        patches = self.dmp.patch_make(
            "x1234567890123456789012345678901234567890123456789012345678901234567890y",
            "xabcy",
        )
        results = self.dmp.patch_apply(
            patches,
            "x123456789012345678901234567890-----++++++++++-----123456789012345678901234567890y",
        )
        self.assertEqual(("xabcy", [True, True]), results)

        # Big delete, big change 1.
        patches = self.dmp.patch_make(
            "x1234567890123456789012345678901234567890123456789012345678901234567890y",
            "xabcy",
        )
        results = self.dmp.patch_apply(
            patches,
            "x12345678901234567890---------------++++++++++---------------12345678901234567890y",
        )
        self.assertEqual(
            (
                "xabc12345678901234567890---------------++++++++++---------------12345678901234567890y",
                [False, True],
            ),
            results,
        )

        # Big delete, big change 2.
        self.dmp.Patch_DeleteThreshold = 0.6
        patches = self.dmp.patch_make(
            "x1234567890123456789012345678901234567890123456789012345678901234567890y",
            "xabcy",
        )
        results = self.dmp.patch_apply(
            patches,
            "x12345678901234567890---------------++++++++++---------------12345678901234567890y",
        )
        self.assertEqual(("xabcy", [True, True]), results)
        self.dmp.Patch_DeleteThreshold = 0.5

        # Compensate for failed patch.
        self.dmp.Match_Threshold = 0.0
        self.dmp.Match_Distance = 0
        patches = self.dmp.patch_make(
            "abcdefghijklmnopqrstuvwxyz--------------------1234567890",
            "abcXXXXXXXXXXdefghijklmnopqrstuvwxyz--------------------1234567YYYYYYYYYY890",
        )
        results = self.dmp.patch_apply(
            patches, "ABCDEFGHIJKLMNOPQRSTUVWXYZ--------------------1234567890"
        )
        self.assertEqual(
            (
                "ABCDEFGHIJKLMNOPQRSTUVWXYZ--------------------1234567YYYYYYYYYY890",
                [False, True],
            ),
            results,
        )
        self.dmp.Match_Threshold = 0.5
        self.dmp.Match_Distance = 1000

        # No side effects.
        patches = self.dmp.patch_make("", "test")
        patchstr = self.dmp.patch_toText(patches)
        results = self.dmp.patch_apply(patches, "")
        self.assertEqual(patchstr, self.dmp.patch_toText(patches))

        # No side effects with major delete.
        patches = self.dmp.patch_make(
            "The quick brown fox jumps over the lazy dog.", "Woof"
        )
        patchstr = self.dmp.patch_toText(patches)
        self.dmp.patch_apply(patches, "The quick brown fox jumps over the lazy dog.")
        self.assertEqual(patchstr, self.dmp.patch_toText(patches))

        # Edge exact match.
        patches = self.dmp.patch_make("", "test")
        self.dmp.patch_apply(patches, "")
        self.assertEqual(("test", [True]), results)

        # Near edge exact match.
        patches = self.dmp.patch_make("XY", "XtestY")
        results = self.dmp.patch_apply(patches, "XY")
        self.assertEqual(("XtestY", [True]), results)

        # Edge partial match.
        patches = self.dmp.patch_make("y", "y123")
        results = self.dmp.patch_apply(patches, "x")
        self.assertEqual(("x123", [True]), results)


if __name__ == "__main__":
    unittest.main()
