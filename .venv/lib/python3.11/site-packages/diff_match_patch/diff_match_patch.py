#!/usr/bin/python3

"""Diff Match and Patch
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

"""Functions for diff, match and patch.

Computes the difference between two texts to create a patch.
Applies the patch onto another text, allowing for errors.
"""

__author__ = "fraser@google.com (Neil Fraser)"

import re
import sys
import time
import urllib.parse


class diff_match_patch:
    """Class containing the diff, match and patch methods.

    Also contains the behaviour settings.
    """

    def __init__(self):
        """Inits a diff_match_patch object with default settings.
        Redefine these in your program to override the defaults.
        """

        # Number of seconds to map a diff before giving up (0 for infinity).
        self.Diff_Timeout = 1.0
        # Cost of an empty edit operation in terms of edit characters.
        self.Diff_EditCost = 4
        # At what point is no match declared (0.0 = perfection, 1.0 = very loose).
        self.Match_Threshold = 0.5
        # How far to search for a match (0 = exact location, 1000+ = broad match).
        # A match this many characters away from the expected location will add
        # 1.0 to the score (0.0 is a perfect match).
        self.Match_Distance = 1000
        # When deleting a large block of text (over ~64 characters), how close do
        # the contents have to be to match the expected contents. (0.0 = perfection,
        # 1.0 = very loose).  Note that Match_Threshold controls how closely the
        # end points of a delete need to match.
        self.Patch_DeleteThreshold = 0.5
        # Chunk size for context length.
        self.Patch_Margin = 4

        # The number of bits in an int.
        # Python has no maximum, thus to disable patch splitting set to 0.
        # However to avoid long patches in certain pathological cases, use 32.
        # Multiple short patches (using native ints) are much faster than long ones.
        self.Match_MaxBits = 32

    #  DIFF FUNCTIONS

    # The data structure representing a diff is an array of tuples:
    # [(DIFF_DELETE, "Hello"), (DIFF_INSERT, "Goodbye"), (DIFF_EQUAL, " world.")]
    # which means: delete "Hello", add "Goodbye" and keep " world."
    DIFF_DELETE = -1
    DIFF_INSERT = 1
    DIFF_EQUAL = 0

    def diff_main(self, text1, text2, checklines=True, deadline=None):
        """Find the differences between two texts.  Simplifies the problem by
          stripping any common prefix or suffix off the texts before diffing.

        Args:
          text1: Old string to be diffed.
          text2: New string to be diffed.
          checklines: Optional speedup flag.  If present and false, then don't run
            a line-level diff first to identify the changed areas.
            Defaults to true, which does a faster, slightly less optimal diff.
          deadline: Optional time when the diff should be complete by.  Used
            internally for recursive calls.  Users should set DiffTimeout instead.

        Returns:
          Array of changes.
        """
        # Set a deadline by which time the diff must be complete.
        if deadline == None:
            # Unlike in most languages, Python counts time in seconds.
            if self.Diff_Timeout <= 0:
                deadline = sys.maxsize
            else:
                deadline = time.time() + self.Diff_Timeout

        # Check for null inputs.
        if text1 == None or text2 == None:
            raise ValueError("Null inputs. (diff_main)")

        # Check for equality (speedup).
        if text1 == text2:
            if text1:
                return [(self.DIFF_EQUAL, text1)]
            return []

        # Trim off common prefix (speedup).
        commonlength = self.diff_commonPrefix(text1, text2)
        commonprefix = text1[:commonlength]
        text1 = text1[commonlength:]
        text2 = text2[commonlength:]

        # Trim off common suffix (speedup).
        commonlength = self.diff_commonSuffix(text1, text2)
        if commonlength == 0:
            commonsuffix = ""
        else:
            commonsuffix = text1[-commonlength:]
            text1 = text1[:-commonlength]
            text2 = text2[:-commonlength]

        # Compute the diff on the middle block.
        diffs = self.diff_compute(text1, text2, checklines, deadline)

        # Restore the prefix and suffix.
        if commonprefix:
            diffs[:0] = [(self.DIFF_EQUAL, commonprefix)]
        if commonsuffix:
            diffs.append((self.DIFF_EQUAL, commonsuffix))
        self.diff_cleanupMerge(diffs)
        return diffs

    def diff_compute(self, text1, text2, checklines, deadline):
        """Find the differences between two texts.  Assumes that the texts do not
          have any common prefix or suffix.

        Args:
          text1: Old string to be diffed.
          text2: New string to be diffed.
          checklines: Speedup flag.  If false, then don't run a line-level diff
            first to identify the changed areas.
            If true, then run a faster, slightly less optimal diff.
          deadline: Time when the diff should be complete by.

        Returns:
          Array of changes.
        """
        if not text1:
            # Just add some text (speedup).
            return [(self.DIFF_INSERT, text2)]

        if not text2:
            # Just delete some text (speedup).
            return [(self.DIFF_DELETE, text1)]

        if len(text1) > len(text2):
            (longtext, shorttext) = (text1, text2)
        else:
            (shorttext, longtext) = (text1, text2)
        i = longtext.find(shorttext)
        if i != -1:
            # Shorter text is inside the longer text (speedup).
            diffs = [
                (self.DIFF_INSERT, longtext[:i]),
                (self.DIFF_EQUAL, shorttext),
                (self.DIFF_INSERT, longtext[i + len(shorttext) :]),
            ]
            # Swap insertions for deletions if diff is reversed.
            if len(text1) > len(text2):
                diffs[0] = (self.DIFF_DELETE, diffs[0][1])
                diffs[2] = (self.DIFF_DELETE, diffs[2][1])
            return diffs

        if len(shorttext) == 1:
            # Single character string.
            # After the previous speedup, the character can't be an equality.
            return [(self.DIFF_DELETE, text1), (self.DIFF_INSERT, text2)]

        # Check to see if the problem can be split in two.
        hm = self.diff_halfMatch(text1, text2)
        if hm:
            # A half-match was found, sort out the return data.
            (text1_a, text1_b, text2_a, text2_b, mid_common) = hm
            # Send both pairs off for separate processing.
            diffs_a = self.diff_main(text1_a, text2_a, checklines, deadline)
            diffs_b = self.diff_main(text1_b, text2_b, checklines, deadline)
            # Merge the results.
            return diffs_a + [(self.DIFF_EQUAL, mid_common)] + diffs_b

        if checklines and len(text1) > 100 and len(text2) > 100:
            return self.diff_lineMode(text1, text2, deadline)

        return self.diff_bisect(text1, text2, deadline)

    def diff_lineMode(self, text1, text2, deadline):
        """Do a quick line-level diff on both strings, then rediff the parts for
          greater accuracy.
          This speedup can produce non-minimal diffs.

        Args:
          text1: Old string to be diffed.
          text2: New string to be diffed.
          deadline: Time when the diff should be complete by.

        Returns:
          Array of changes.
        """

        # Scan the text on a line-by-line basis first.
        (text1, text2, linearray) = self.diff_linesToChars(text1, text2)

        diffs = self.diff_main(text1, text2, False, deadline)

        # Convert the diff back to original text.
        self.diff_charsToLines(diffs, linearray)
        # Eliminate freak matches (e.g. blank lines)
        self.diff_cleanupSemantic(diffs)

        # Rediff any replacement blocks, this time character-by-character.
        # Add a dummy entry at the end.
        diffs.append((self.DIFF_EQUAL, ""))
        pointer = 0
        count_delete = 0
        count_insert = 0
        text_delete = ""
        text_insert = ""
        while pointer < len(diffs):
            if diffs[pointer][0] == self.DIFF_INSERT:
                count_insert += 1
                text_insert += diffs[pointer][1]
            elif diffs[pointer][0] == self.DIFF_DELETE:
                count_delete += 1
                text_delete += diffs[pointer][1]
            elif diffs[pointer][0] == self.DIFF_EQUAL:
                # Upon reaching an equality, check for prior redundancies.
                if count_delete >= 1 and count_insert >= 1:
                    # Delete the offending records and add the merged ones.
                    subDiff = self.diff_main(text_delete, text_insert, False, deadline)
                    diffs[pointer - count_delete - count_insert : pointer] = subDiff
                    pointer = pointer - count_delete - count_insert + len(subDiff)
                count_insert = 0
                count_delete = 0
                text_delete = ""
                text_insert = ""

            pointer += 1

        diffs.pop()  # Remove the dummy entry at the end.

        return diffs

    def diff_bisect(self, text1, text2, deadline):
        """Find the 'middle snake' of a diff, split the problem in two
          and return the recursively constructed diff.
          See Myers 1986 paper: An O(ND) Difference Algorithm and Its Variations.

        Args:
          text1: Old string to be diffed.
          text2: New string to be diffed.
          deadline: Time at which to bail if not yet complete.

        Returns:
          Array of diff tuples.
        """

        # Cache the text lengths to prevent multiple calls.
        text1_length = len(text1)
        text2_length = len(text2)
        max_d = (text1_length + text2_length + 1) // 2
        v_offset = max_d
        v_length = 2 * max_d
        v1 = [-1] * v_length
        v1[v_offset + 1] = 0
        v2 = v1[:]
        delta = text1_length - text2_length
        # If the total number of characters is odd, then the front path will
        # collide with the reverse path.
        front = delta % 2 != 0
        # Offsets for start and end of k loop.
        # Prevents mapping of space beyond the grid.
        k1start = 0
        k1end = 0
        k2start = 0
        k2end = 0
        for d in range(max_d):
            # Bail out if deadline is reached.
            if time.time() > deadline:
                break

            # Walk the front path one step.
            for k1 in range(-d + k1start, d + 1 - k1end, 2):
                k1_offset = v_offset + k1
                if k1 == -d or (k1 != d and v1[k1_offset - 1] < v1[k1_offset + 1]):
                    x1 = v1[k1_offset + 1]
                else:
                    x1 = v1[k1_offset - 1] + 1
                y1 = x1 - k1
                while (
                    x1 < text1_length and y1 < text2_length and text1[x1] == text2[y1]
                ):
                    x1 += 1
                    y1 += 1
                v1[k1_offset] = x1
                if x1 > text1_length:
                    # Ran off the right of the graph.
                    k1end += 2
                elif y1 > text2_length:
                    # Ran off the bottom of the graph.
                    k1start += 2
                elif front:
                    k2_offset = v_offset + delta - k1
                    if k2_offset >= 0 and k2_offset < v_length and v2[k2_offset] != -1:
                        # Mirror x2 onto top-left coordinate system.
                        x2 = text1_length - v2[k2_offset]
                        if x1 >= x2:
                            # Overlap detected.
                            return self.diff_bisectSplit(text1, text2, x1, y1, deadline)

            # Walk the reverse path one step.
            for k2 in range(-d + k2start, d + 1 - k2end, 2):
                k2_offset = v_offset + k2
                if k2 == -d or (k2 != d and v2[k2_offset - 1] < v2[k2_offset + 1]):
                    x2 = v2[k2_offset + 1]
                else:
                    x2 = v2[k2_offset - 1] + 1
                y2 = x2 - k2
                while (
                    x2 < text1_length
                    and y2 < text2_length
                    and text1[-x2 - 1] == text2[-y2 - 1]
                ):
                    x2 += 1
                    y2 += 1
                v2[k2_offset] = x2
                if x2 > text1_length:
                    # Ran off the left of the graph.
                    k2end += 2
                elif y2 > text2_length:
                    # Ran off the top of the graph.
                    k2start += 2
                elif not front:
                    k1_offset = v_offset + delta - k2
                    if k1_offset >= 0 and k1_offset < v_length and v1[k1_offset] != -1:
                        x1 = v1[k1_offset]
                        y1 = v_offset + x1 - k1_offset
                        # Mirror x2 onto top-left coordinate system.
                        x2 = text1_length - x2
                        if x1 >= x2:
                            # Overlap detected.
                            return self.diff_bisectSplit(text1, text2, x1, y1, deadline)

        # Diff took too long and hit the deadline or
        # number of diffs equals number of characters, no commonality at all.
        return [(self.DIFF_DELETE, text1), (self.DIFF_INSERT, text2)]

    def diff_bisectSplit(self, text1, text2, x, y, deadline):
        """Given the location of the 'middle snake', split the diff in two parts
        and recurse.

        Args:
          text1: Old string to be diffed.
          text2: New string to be diffed.
          x: Index of split point in text1.
          y: Index of split point in text2.
          deadline: Time at which to bail if not yet complete.

        Returns:
          Array of diff tuples.
        """
        text1a = text1[:x]
        text2a = text2[:y]
        text1b = text1[x:]
        text2b = text2[y:]

        # Compute both diffs serially.
        diffs = self.diff_main(text1a, text2a, False, deadline)
        diffsb = self.diff_main(text1b, text2b, False, deadline)

        return diffs + diffsb

    def diff_linesToChars(self, text1, text2):
        """Split two texts into an array of strings.  Reduce the texts to a string
        of hashes where each Unicode character represents one line.

        Args:
          text1: First string.
          text2: Second string.

        Returns:
          Three element tuple, containing the encoded text1, the encoded text2 and
          the array of unique strings.  The zeroth element of the array of unique
          strings is intentionally blank.
        """
        lineArray = []  # e.g. lineArray[4] == "Hello\n"
        lineHash = {}  # e.g. lineHash["Hello\n"] == 4

        # "\x00" is a valid character, but various debuggers don't like it.
        # So we'll insert a junk entry to avoid generating a null character.
        lineArray.append("")

        def diff_linesToCharsMunge(text):
            """Split a text into an array of strings.  Reduce the texts to a string
            of hashes where each Unicode character represents one line.
            Modifies linearray and linehash through being a closure.

            Args:
              text: String to encode.

            Returns:
              Encoded string.
            """
            chars = []
            # Walk the text, pulling out a substring for each line.
            # text.split('\n') would would temporarily double our memory footprint.
            # Modifying text would create many large strings to garbage collect.
            lineStart = 0
            lineEnd = -1
            while lineEnd < len(text) - 1:
                lineEnd = text.find("\n", lineStart)
                if lineEnd == -1:
                    lineEnd = len(text) - 1
                line = text[lineStart : lineEnd + 1]

                if line in lineHash:
                    chars.append(chr(lineHash[line]))
                else:
                    if len(lineArray) == maxLines:
                        # Bail out at 1114111 because chr(1114112) throws.
                        line = text[lineStart:]
                        lineEnd = len(text)
                    lineArray.append(line)
                    lineHash[line] = len(lineArray) - 1
                    chars.append(chr(len(lineArray) - 1))
                lineStart = lineEnd + 1
            return "".join(chars)

        # Allocate 2/3rds of the space for text1, the rest for text2.
        maxLines = 666666
        chars1 = diff_linesToCharsMunge(text1)
        maxLines = 1114111
        chars2 = diff_linesToCharsMunge(text2)
        return (chars1, chars2, lineArray)

    def diff_charsToLines(self, diffs, lineArray):
        """Rehydrate the text in a diff from a string of line hashes to real lines
        of text.

        Args:
          diffs: Array of diff tuples.
          lineArray: Array of unique strings.
        """
        for i in range(len(diffs)):
            text = []
            for char in diffs[i][1]:
                text.append(lineArray[ord(char)])
            diffs[i] = (diffs[i][0], "".join(text))

    def diff_commonPrefix(self, text1, text2):
        """Determine the common prefix of two strings.

        Args:
          text1: First string.
          text2: Second string.

        Returns:
          The number of characters common to the start of each string.
        """
        # Quick check for common null cases.
        if not text1 or not text2 or text1[0] != text2[0]:
            return 0
        # Binary search.
        # Performance analysis: https://neil.fraser.name/news/2007/10/09/
        pointermin = 0
        pointermax = min(len(text1), len(text2))
        pointermid = pointermax
        pointerstart = 0
        while pointermin < pointermid:
            if text1[pointerstart:pointermid] == text2[pointerstart:pointermid]:
                pointermin = pointermid
                pointerstart = pointermin
            else:
                pointermax = pointermid
            pointermid = (pointermax - pointermin) // 2 + pointermin
        return pointermid

    def diff_commonSuffix(self, text1, text2):
        """Determine the common suffix of two strings.

        Args:
          text1: First string.
          text2: Second string.

        Returns:
          The number of characters common to the end of each string.
        """
        # Quick check for common null cases.
        if not text1 or not text2 or text1[-1] != text2[-1]:
            return 0
        # Binary search.
        # Performance analysis: https://neil.fraser.name/news/2007/10/09/
        pointermin = 0
        pointermax = min(len(text1), len(text2))
        pointermid = pointermax
        pointerend = 0
        while pointermin < pointermid:
            if (
                text1[-pointermid : len(text1) - pointerend]
                == text2[-pointermid : len(text2) - pointerend]
            ):
                pointermin = pointermid
                pointerend = pointermin
            else:
                pointermax = pointermid
            pointermid = (pointermax - pointermin) // 2 + pointermin
        return pointermid

    def diff_commonOverlap(self, text1, text2):
        """Determine if the suffix of one string is the prefix of another.

        Args:
          text1 First string.
          text2 Second string.

        Returns:
          The number of characters common to the end of the first
          string and the start of the second string.
        """
        # Cache the text lengths to prevent multiple calls.
        text1_length = len(text1)
        text2_length = len(text2)
        # Eliminate the null case.
        if text1_length == 0 or text2_length == 0:
            return 0
        # Truncate the longer string.
        if text1_length > text2_length:
            text1 = text1[-text2_length:]
        elif text1_length < text2_length:
            text2 = text2[:text1_length]
        text_length = min(text1_length, text2_length)
        # Quick check for the worst case.
        if text1 == text2:
            return text_length

        # Start by looking for a single character match
        # and increase length until no match is found.
        # Performance analysis: https://neil.fraser.name/news/2010/11/04/
        best = 0
        length = 1
        while True:
            pattern = text1[-length:]
            found = text2.find(pattern)
            if found == -1:
                return best
            length += found
            if found == 0 or text1[-length:] == text2[:length]:
                best = length
                length += 1

    def diff_halfMatch(self, text1, text2):
        """Do the two texts share a substring which is at least half the length of
        the longer text?
        This speedup can produce non-minimal diffs.

        Args:
          text1: First string.
          text2: Second string.

        Returns:
          Five element Array, containing the prefix of text1, the suffix of text1,
          the prefix of text2, the suffix of text2 and the common middle.  Or None
          if there was no match.
        """
        if self.Diff_Timeout <= 0:
            # Don't risk returning a non-optimal diff if we have unlimited time.
            return None
        if len(text1) > len(text2):
            (longtext, shorttext) = (text1, text2)
        else:
            (shorttext, longtext) = (text1, text2)
        if len(longtext) < 4 or len(shorttext) * 2 < len(longtext):
            return None  # Pointless.

        def diff_halfMatchI(longtext, shorttext, i):
            """Does a substring of shorttext exist within longtext such that the
            substring is at least half the length of longtext?
            Closure, but does not reference any external variables.

            Args:
              longtext: Longer string.
              shorttext: Shorter string.
              i: Start index of quarter length substring within longtext.

            Returns:
              Five element Array, containing the prefix of longtext, the suffix of
              longtext, the prefix of shorttext, the suffix of shorttext and the
              common middle.  Or None if there was no match.
            """
            seed = longtext[i : i + len(longtext) // 4]
            best_common = ""
            j = shorttext.find(seed)
            while j != -1:
                prefixLength = self.diff_commonPrefix(longtext[i:], shorttext[j:])
                suffixLength = self.diff_commonSuffix(longtext[:i], shorttext[:j])
                if len(best_common) < suffixLength + prefixLength:
                    best_common = (
                        shorttext[j - suffixLength : j]
                        + shorttext[j : j + prefixLength]
                    )
                    best_longtext_a = longtext[: i - suffixLength]
                    best_longtext_b = longtext[i + prefixLength :]
                    best_shorttext_a = shorttext[: j - suffixLength]
                    best_shorttext_b = shorttext[j + prefixLength :]
                j = shorttext.find(seed, j + 1)

            if len(best_common) * 2 >= len(longtext):
                return (
                    best_longtext_a,
                    best_longtext_b,
                    best_shorttext_a,
                    best_shorttext_b,
                    best_common,
                )
            else:
                return None

        # First check if the second quarter is the seed for a half-match.
        hm1 = diff_halfMatchI(longtext, shorttext, (len(longtext) + 3) // 4)
        # Check again based on the third quarter.
        hm2 = diff_halfMatchI(longtext, shorttext, (len(longtext) + 1) // 2)
        if not hm1 and not hm2:
            return None
        elif not hm2:
            hm = hm1
        elif not hm1:
            hm = hm2
        else:
            # Both matched.  Select the longest.
            if len(hm1[4]) > len(hm2[4]):
                hm = hm1
            else:
                hm = hm2

        # A half-match was found, sort out the return data.
        if len(text1) > len(text2):
            (text1_a, text1_b, text2_a, text2_b, mid_common) = hm
        else:
            (text2_a, text2_b, text1_a, text1_b, mid_common) = hm
        return (text1_a, text1_b, text2_a, text2_b, mid_common)

    def diff_cleanupSemantic(self, diffs):
        """Reduce the number of edits by eliminating semantically trivial
        equalities.

        Args:
          diffs: Array of diff tuples.
        """
        changes = False
        equalities = []  # Stack of indices where equalities are found.
        lastEquality = None  # Always equal to diffs[equalities[-1]][1]
        pointer = 0  # Index of current position.
        # Number of chars that changed prior to the equality.
        length_insertions1, length_deletions1 = 0, 0
        # Number of chars that changed after the equality.
        length_insertions2, length_deletions2 = 0, 0
        while pointer < len(diffs):
            if diffs[pointer][0] == self.DIFF_EQUAL:  # Equality found.
                equalities.append(pointer)
                length_insertions1, length_insertions2 = length_insertions2, 0
                length_deletions1, length_deletions2 = length_deletions2, 0
                lastEquality = diffs[pointer][1]
            else:  # An insertion or deletion.
                if diffs[pointer][0] == self.DIFF_INSERT:
                    length_insertions2 += len(diffs[pointer][1])
                else:
                    length_deletions2 += len(diffs[pointer][1])
                # Eliminate an equality that is smaller or equal to the edits on both
                # sides of it.
                if (
                    lastEquality
                    and (
                        len(lastEquality) <= max(length_insertions1, length_deletions1)
                    )
                    and (
                        len(lastEquality) <= max(length_insertions2, length_deletions2)
                    )
                ):
                    # Duplicate record.
                    diffs.insert(equalities[-1], (self.DIFF_DELETE, lastEquality))
                    # Change second copy to insert.
                    diffs[equalities[-1] + 1] = (
                        self.DIFF_INSERT,
                        diffs[equalities[-1] + 1][1],
                    )
                    # Throw away the equality we just deleted.
                    equalities.pop()
                    # Throw away the previous equality (it needs to be reevaluated).
                    if len(equalities):
                        equalities.pop()
                    if len(equalities):
                        pointer = equalities[-1]
                    else:
                        pointer = -1
                    # Reset the counters.
                    length_insertions1, length_deletions1 = 0, 0
                    length_insertions2, length_deletions2 = 0, 0
                    lastEquality = None
                    changes = True
            pointer += 1

        # Normalize the diff.
        if changes:
            self.diff_cleanupMerge(diffs)
        self.diff_cleanupSemanticLossless(diffs)

        # Find any overlaps between deletions and insertions.
        # e.g: <del>abcxxx</del><ins>xxxdef</ins>
        #   -> <del>abc</del>xxx<ins>def</ins>
        # e.g: <del>xxxabc</del><ins>defxxx</ins>
        #   -> <ins>def</ins>xxx<del>abc</del>
        # Only extract an overlap if it is as big as the edit ahead or behind it.
        pointer = 1
        while pointer < len(diffs):
            if (
                diffs[pointer - 1][0] == self.DIFF_DELETE
                and diffs[pointer][0] == self.DIFF_INSERT
            ):
                deletion = diffs[pointer - 1][1]
                insertion = diffs[pointer][1]
                overlap_length1 = self.diff_commonOverlap(deletion, insertion)
                overlap_length2 = self.diff_commonOverlap(insertion, deletion)
                if overlap_length1 >= overlap_length2:
                    if (
                        overlap_length1 >= len(deletion) / 2.0
                        or overlap_length1 >= len(insertion) / 2.0
                    ):
                        # Overlap found.  Insert an equality and trim the surrounding edits.
                        diffs.insert(
                            pointer, (self.DIFF_EQUAL, insertion[:overlap_length1])
                        )
                        diffs[pointer - 1] = (
                            self.DIFF_DELETE,
                            deletion[: len(deletion) - overlap_length1],
                        )
                        diffs[pointer + 1] = (
                            self.DIFF_INSERT,
                            insertion[overlap_length1:],
                        )
                        pointer += 1
                else:
                    if (
                        overlap_length2 >= len(deletion) / 2.0
                        or overlap_length2 >= len(insertion) / 2.0
                    ):
                        # Reverse overlap found.
                        # Insert an equality and swap and trim the surrounding edits.
                        diffs.insert(
                            pointer, (self.DIFF_EQUAL, deletion[:overlap_length2])
                        )
                        diffs[pointer - 1] = (
                            self.DIFF_INSERT,
                            insertion[: len(insertion) - overlap_length2],
                        )
                        diffs[pointer + 1] = (
                            self.DIFF_DELETE,
                            deletion[overlap_length2:],
                        )
                        pointer += 1
                pointer += 1
            pointer += 1

    def diff_cleanupSemanticLossless(self, diffs):
        """Look for single edits surrounded on both sides by equalities
        which can be shifted sideways to align the edit to a word boundary.
        e.g: The c<ins>at c</ins>ame. -> The <ins>cat </ins>came.

        Args:
          diffs: Array of diff tuples.
        """

        def diff_cleanupSemanticScore(one, two):
            """Given two strings, compute a score representing whether the
            internal boundary falls on logical boundaries.
            Scores range from 6 (best) to 0 (worst).
            Closure, but does not reference any external variables.

            Args:
              one: First string.
              two: Second string.

            Returns:
              The score.
            """
            if not one or not two:
                # Edges are the best.
                return 6

            # Each port of this function behaves slightly differently due to
            # subtle differences in each language's definition of things like
            # 'whitespace'.  Since this function's purpose is largely cosmetic,
            # the choice has been made to use each language's native features
            # rather than force total conformity.
            char1 = one[-1]
            char2 = two[0]
            nonAlphaNumeric1 = not char1.isalnum()
            nonAlphaNumeric2 = not char2.isalnum()
            whitespace1 = nonAlphaNumeric1 and char1.isspace()
            whitespace2 = nonAlphaNumeric2 and char2.isspace()
            lineBreak1 = whitespace1 and (char1 == "\r" or char1 == "\n")
            lineBreak2 = whitespace2 and (char2 == "\r" or char2 == "\n")
            blankLine1 = lineBreak1 and self.BLANKLINEEND.search(one)
            blankLine2 = lineBreak2 and self.BLANKLINESTART.match(two)

            if blankLine1 or blankLine2:
                # Five points for blank lines.
                return 5
            elif lineBreak1 or lineBreak2:
                # Four points for line breaks.
                return 4
            elif nonAlphaNumeric1 and not whitespace1 and whitespace2:
                # Three points for end of sentences.
                return 3
            elif whitespace1 or whitespace2:
                # Two points for whitespace.
                return 2
            elif nonAlphaNumeric1 or nonAlphaNumeric2:
                # One point for non-alphanumeric.
                return 1
            return 0

        pointer = 1
        # Intentionally ignore the first and last element (don't need checking).
        while pointer < len(diffs) - 1:
            if (
                diffs[pointer - 1][0] == self.DIFF_EQUAL
                and diffs[pointer + 1][0] == self.DIFF_EQUAL
            ):
                # This is a single edit surrounded by equalities.
                equality1 = diffs[pointer - 1][1]
                edit = diffs[pointer][1]
                equality2 = diffs[pointer + 1][1]

                # First, shift the edit as far left as possible.
                commonOffset = self.diff_commonSuffix(equality1, edit)
                if commonOffset:
                    commonString = edit[-commonOffset:]
                    equality1 = equality1[:-commonOffset]
                    edit = commonString + edit[:-commonOffset]
                    equality2 = commonString + equality2

                # Second, step character by character right, looking for the best fit.
                bestEquality1 = equality1
                bestEdit = edit
                bestEquality2 = equality2
                bestScore = diff_cleanupSemanticScore(
                    equality1, edit
                ) + diff_cleanupSemanticScore(edit, equality2)
                while edit and equality2 and edit[0] == equality2[0]:
                    equality1 += edit[0]
                    edit = edit[1:] + equality2[0]
                    equality2 = equality2[1:]
                    score = diff_cleanupSemanticScore(
                        equality1, edit
                    ) + diff_cleanupSemanticScore(edit, equality2)
                    # The >= encourages trailing rather than leading whitespace on edits.
                    if score >= bestScore:
                        bestScore = score
                        bestEquality1 = equality1
                        bestEdit = edit
                        bestEquality2 = equality2

                if diffs[pointer - 1][1] != bestEquality1:
                    # We have an improvement, save it back to the diff.
                    if bestEquality1:
                        diffs[pointer - 1] = (diffs[pointer - 1][0], bestEquality1)
                    else:
                        del diffs[pointer - 1]
                        pointer -= 1
                    diffs[pointer] = (diffs[pointer][0], bestEdit)
                    if bestEquality2:
                        diffs[pointer + 1] = (diffs[pointer + 1][0], bestEquality2)
                    else:
                        del diffs[pointer + 1]
                        pointer -= 1
            pointer += 1

    # Define some regex patterns for matching boundaries.
    BLANKLINEEND = re.compile(r"\n\r?\n$")
    BLANKLINESTART = re.compile(r"^\r?\n\r?\n")

    def diff_cleanupEfficiency(self, diffs):
        """Reduce the number of edits by eliminating operationally trivial
        equalities.

        Args:
          diffs: Array of diff tuples.
        """
        changes = False
        equalities = []  # Stack of indices where equalities are found.
        lastEquality = None  # Always equal to diffs[equalities[-1]][1]
        pointer = 0  # Index of current position.
        pre_ins = False  # Is there an insertion operation before the last equality.
        pre_del = False  # Is there a deletion operation before the last equality.
        post_ins = False  # Is there an insertion operation after the last equality.
        post_del = False  # Is there a deletion operation after the last equality.
        while pointer < len(diffs):
            if diffs[pointer][0] == self.DIFF_EQUAL:  # Equality found.
                if len(diffs[pointer][1]) < self.Diff_EditCost and (
                    post_ins or post_del
                ):
                    # Candidate found.
                    equalities.append(pointer)
                    pre_ins = post_ins
                    pre_del = post_del
                    lastEquality = diffs[pointer][1]
                else:
                    # Not a candidate, and can never become one.
                    equalities = []
                    lastEquality = None

                post_ins = post_del = False
            else:  # An insertion or deletion.
                if diffs[pointer][0] == self.DIFF_DELETE:
                    post_del = True
                else:
                    post_ins = True

                # Five types to be split:
                # <ins>A</ins><del>B</del>XY<ins>C</ins><del>D</del>
                # <ins>A</ins>X<ins>C</ins><del>D</del>
                # <ins>A</ins><del>B</del>X<ins>C</ins>
                # <ins>A</del>X<ins>C</ins><del>D</del>
                # <ins>A</ins><del>B</del>X<del>C</del>

                if lastEquality and (
                    (pre_ins and pre_del and post_ins and post_del)
                    or (
                        (len(lastEquality) < self.Diff_EditCost / 2)
                        and (pre_ins + pre_del + post_ins + post_del) == 3
                    )
                ):
                    # Duplicate record.
                    diffs.insert(equalities[-1], (self.DIFF_DELETE, lastEquality))
                    # Change second copy to insert.
                    diffs[equalities[-1] + 1] = (
                        self.DIFF_INSERT,
                        diffs[equalities[-1] + 1][1],
                    )
                    equalities.pop()  # Throw away the equality we just deleted.
                    lastEquality = None
                    if pre_ins and pre_del:
                        # No changes made which could affect previous entry, keep going.
                        post_ins = post_del = True
                        equalities = []
                    else:
                        if len(equalities):
                            equalities.pop()  # Throw away the previous equality.
                        if len(equalities):
                            pointer = equalities[-1]
                        else:
                            pointer = -1
                        post_ins = post_del = False
                    changes = True
            pointer += 1

        if changes:
            self.diff_cleanupMerge(diffs)

    def diff_cleanupMerge(self, diffs):
        """Reorder and merge like edit sections.  Merge equalities.
        Any edit section can move as long as it doesn't cross an equality.

        Args:
          diffs: Array of diff tuples.
        """
        diffs.append((self.DIFF_EQUAL, ""))  # Add a dummy entry at the end.
        pointer = 0
        count_delete = 0
        count_insert = 0
        text_delete = ""
        text_insert = ""
        while pointer < len(diffs):
            if diffs[pointer][0] == self.DIFF_INSERT:
                count_insert += 1
                text_insert += diffs[pointer][1]
                pointer += 1
            elif diffs[pointer][0] == self.DIFF_DELETE:
                count_delete += 1
                text_delete += diffs[pointer][1]
                pointer += 1
            elif diffs[pointer][0] == self.DIFF_EQUAL:
                # Upon reaching an equality, check for prior redundancies.
                if count_delete + count_insert > 1:
                    if count_delete != 0 and count_insert != 0:
                        # Factor out any common prefixies.
                        commonlength = self.diff_commonPrefix(text_insert, text_delete)
                        if commonlength != 0:
                            x = pointer - count_delete - count_insert - 1
                            if x >= 0 and diffs[x][0] == self.DIFF_EQUAL:
                                diffs[x] = (
                                    diffs[x][0],
                                    diffs[x][1] + text_insert[:commonlength],
                                )
                            else:
                                diffs.insert(
                                    0, (self.DIFF_EQUAL, text_insert[:commonlength])
                                )
                                pointer += 1
                            text_insert = text_insert[commonlength:]
                            text_delete = text_delete[commonlength:]
                        # Factor out any common suffixies.
                        commonlength = self.diff_commonSuffix(text_insert, text_delete)
                        if commonlength != 0:
                            diffs[pointer] = (
                                diffs[pointer][0],
                                text_insert[-commonlength:] + diffs[pointer][1],
                            )
                            text_insert = text_insert[:-commonlength]
                            text_delete = text_delete[:-commonlength]
                    # Delete the offending records and add the merged ones.
                    new_ops = []
                    if len(text_delete) != 0:
                        new_ops.append((self.DIFF_DELETE, text_delete))
                    if len(text_insert) != 0:
                        new_ops.append((self.DIFF_INSERT, text_insert))
                    pointer -= count_delete + count_insert
                    diffs[pointer : pointer + count_delete + count_insert] = new_ops
                    pointer += len(new_ops) + 1
                elif pointer != 0 and diffs[pointer - 1][0] == self.DIFF_EQUAL:
                    # Merge this equality with the previous one.
                    diffs[pointer - 1] = (
                        diffs[pointer - 1][0],
                        diffs[pointer - 1][1] + diffs[pointer][1],
                    )
                    del diffs[pointer]
                else:
                    pointer += 1

                count_insert = 0
                count_delete = 0
                text_delete = ""
                text_insert = ""

        if diffs[-1][1] == "":
            diffs.pop()  # Remove the dummy entry at the end.

        # Second pass: look for single edits surrounded on both sides by equalities
        # which can be shifted sideways to eliminate an equality.
        # e.g: A<ins>BA</ins>C -> <ins>AB</ins>AC
        changes = False
        pointer = 1
        # Intentionally ignore the first and last element (don't need checking).
        while pointer < len(diffs) - 1:
            if (
                diffs[pointer - 1][0] == self.DIFF_EQUAL
                and diffs[pointer + 1][0] == self.DIFF_EQUAL
            ):
                # This is a single edit surrounded by equalities.
                if diffs[pointer][1].endswith(diffs[pointer - 1][1]):
                    # Shift the edit over the previous equality.
                    if diffs[pointer - 1][1] != "":
                        diffs[pointer] = (
                            diffs[pointer][0],
                            diffs[pointer - 1][1]
                            + diffs[pointer][1][: -len(diffs[pointer - 1][1])],
                        )
                        diffs[pointer + 1] = (
                            diffs[pointer + 1][0],
                            diffs[pointer - 1][1] + diffs[pointer + 1][1],
                        )
                    del diffs[pointer - 1]
                    changes = True
                elif diffs[pointer][1].startswith(diffs[pointer + 1][1]):
                    # Shift the edit over the next equality.
                    diffs[pointer - 1] = (
                        diffs[pointer - 1][0],
                        diffs[pointer - 1][1] + diffs[pointer + 1][1],
                    )
                    diffs[pointer] = (
                        diffs[pointer][0],
                        diffs[pointer][1][len(diffs[pointer + 1][1]) :]
                        + diffs[pointer + 1][1],
                    )
                    del diffs[pointer + 1]
                    changes = True
            pointer += 1

        # If shifts were made, the diff needs reordering and another shift sweep.
        if changes:
            self.diff_cleanupMerge(diffs)

    def diff_xIndex(self, diffs, loc):
        """loc is a location in text1, compute and return the equivalent location
        in text2.  e.g. "The cat" vs "The big cat", 1->1, 5->8

        Args:
          diffs: Array of diff tuples.
          loc: Location within text1.

        Returns:
          Location within text2.
        """
        chars1 = 0
        chars2 = 0
        last_chars1 = 0
        last_chars2 = 0
        for x in range(len(diffs)):
            (op, text) = diffs[x]
            if op != self.DIFF_INSERT:  # Equality or deletion.
                chars1 += len(text)
            if op != self.DIFF_DELETE:  # Equality or insertion.
                chars2 += len(text)
            if chars1 > loc:  # Overshot the location.
                break
            last_chars1 = chars1
            last_chars2 = chars2

        if len(diffs) != x and diffs[x][0] == self.DIFF_DELETE:
            # The location was deleted.
            return last_chars2
        # Add the remaining len(character).
        return last_chars2 + (loc - last_chars1)

    def diff_prettyHtml(self, diffs):
        """Convert a diff array into a pretty HTML report.

        Args:
          diffs: Array of diff tuples.

        Returns:
          HTML representation.
        """
        html = []
        for op, data in diffs:
            text = (
                data.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\n", "&para;<br>")
            )
            if op == self.DIFF_INSERT:
                html.append('<ins style="background:#e6ffe6;">%s</ins>' % text)
            elif op == self.DIFF_DELETE:
                html.append('<del style="background:#ffe6e6;">%s</del>' % text)
            elif op == self.DIFF_EQUAL:
                html.append("<span>%s</span>" % text)
        return "".join(html)

    def diff_text1(self, diffs):
        """Compute and return the source text (all equalities and deletions).

        Args:
          diffs: Array of diff tuples.

        Returns:
          Source text.
        """
        text = []
        for op, data in diffs:
            if op != self.DIFF_INSERT:
                text.append(data)
        return "".join(text)

    def diff_text2(self, diffs):
        """Compute and return the destination text (all equalities and insertions).

        Args:
          diffs: Array of diff tuples.

        Returns:
          Destination text.
        """
        text = []
        for op, data in diffs:
            if op != self.DIFF_DELETE:
                text.append(data)
        return "".join(text)

    def diff_levenshtein(self, diffs):
        """Compute the Levenshtein distance; the number of inserted, deleted or
        substituted characters.

        Args:
          diffs: Array of diff tuples.

        Returns:
          Number of changes.
        """
        levenshtein = 0
        insertions = 0
        deletions = 0
        for op, data in diffs:
            if op == self.DIFF_INSERT:
                insertions += len(data)
            elif op == self.DIFF_DELETE:
                deletions += len(data)
            elif op == self.DIFF_EQUAL:
                # A deletion and an insertion is one substitution.
                levenshtein += max(insertions, deletions)
                insertions = 0
                deletions = 0
        levenshtein += max(insertions, deletions)
        return levenshtein

    def diff_toDelta(self, diffs):
        """Crush the diff into an encoded string which describes the operations
        required to transform text1 into text2.
        E.g. =3\t-2\t+ing  -> Keep 3 chars, delete 2 chars, insert 'ing'.
        Operations are tab-separated.  Inserted text is escaped using %xx notation.

        Args:
          diffs: Array of diff tuples.

        Returns:
          Delta text.
        """
        text = []
        for op, data in diffs:
            if op == self.DIFF_INSERT:
                # High ascii will raise UnicodeDecodeError.  Use Unicode instead.
                data = data.encode("utf-8")
                text.append("+" + urllib.parse.quote(data, "!~*'();/?:@&=+$,# "))
            elif op == self.DIFF_DELETE:
                text.append("-%d" % len(data))
            elif op == self.DIFF_EQUAL:
                text.append("=%d" % len(data))
        return "\t".join(text)

    def diff_fromDelta(self, text1, delta):
        """Given the original text1, and an encoded string which describes the
        operations required to transform text1 into text2, compute the full diff.

        Args:
          text1: Source string for the diff.
          delta: Delta text.

        Returns:
          Array of diff tuples.

        Raises:
          ValueError: If invalid input.
        """
        diffs = []
        pointer = 0  # Cursor in text1
        tokens = delta.split("\t")
        for token in tokens:
            if token == "":
                # Blank tokens are ok (from a trailing \t).
                continue
            # Each token begins with a one character parameter which specifies the
            # operation of this token (delete, insert, equality).
            param = token[1:]
            if token[0] == "+":
                param = urllib.parse.unquote(param)
                diffs.append((self.DIFF_INSERT, param))
            elif token[0] == "-" or token[0] == "=":
                try:
                    n = int(param)
                except ValueError:
                    raise ValueError("Invalid number in diff_fromDelta: " + param)
                if n < 0:
                    raise ValueError("Negative number in diff_fromDelta: " + param)
                text = text1[pointer : pointer + n]
                pointer += n
                if token[0] == "=":
                    diffs.append((self.DIFF_EQUAL, text))
                else:
                    diffs.append((self.DIFF_DELETE, text))
            else:
                # Anything else is an error.
                raise ValueError(
                    "Invalid diff operation in diff_fromDelta: " + token[0]
                )
        if pointer != len(text1):
            raise ValueError(
                "Delta length (%d) does not equal source text length (%d)."
                % (pointer, len(text1))
            )
        return diffs

    #  MATCH FUNCTIONS

    def match_main(self, text, pattern, loc):
        """Locate the best instance of 'pattern' in 'text' near 'loc'.

        Args:
          text: The text to search.
          pattern: The pattern to search for.
          loc: The location to search around.

        Returns:
          Best match index or -1.
        """
        # Check for null inputs.
        if text == None or pattern == None:
            raise ValueError("Null inputs. (match_main)")

        loc = max(0, min(loc, len(text)))
        if text == pattern:
            # Shortcut (potentially not guaranteed by the algorithm)
            return 0
        elif not text:
            # Nothing to match.
            return -1
        elif text[loc : loc + len(pattern)] == pattern:
            # Perfect match at the perfect spot!  (Includes case of null pattern)
            return loc
        else:
            # Do a fuzzy compare.
            match = self.match_bitap(text, pattern, loc)
            return match

    def match_bitap(self, text, pattern, loc):
        """Locate the best instance of 'pattern' in 'text' near 'loc' using the
        Bitap algorithm.

        Args:
          text: The text to search.
          pattern: The pattern to search for.
          loc: The location to search around.

        Returns:
          Best match index or -1.
        """
        # Python doesn't have a maxint limit, so ignore this check.
        # if self.Match_MaxBits != 0 and len(pattern) > self.Match_MaxBits:
        #  raise ValueError("Pattern too long for this application.")

        # Initialise the alphabet.
        s = self.match_alphabet(pattern)

        def match_bitapScore(e, x):
            """Compute and return the score for a match with e errors and x location.
            Accesses loc and pattern through being a closure.

            Args:
              e: Number of errors in match.
              x: Location of match.

            Returns:
              Overall score for match (0.0 = good, 1.0 = bad).
            """
            accuracy = float(e) / len(pattern)
            proximity = abs(loc - x)
            if not self.Match_Distance:
                # Dodge divide by zero error.
                return proximity and 1.0 or accuracy
            return accuracy + (proximity / float(self.Match_Distance))

        # Highest score beyond which we give up.
        score_threshold = self.Match_Threshold
        # Is there a nearby exact match? (speedup)
        best_loc = text.find(pattern, loc)
        if best_loc != -1:
            score_threshold = min(match_bitapScore(0, best_loc), score_threshold)
            # What about in the other direction? (speedup)
            best_loc = text.rfind(pattern, loc + len(pattern))
            if best_loc != -1:
                score_threshold = min(match_bitapScore(0, best_loc), score_threshold)

        # Initialise the bit arrays.
        matchmask = 1 << (len(pattern) - 1)
        best_loc = -1

        bin_max = len(pattern) + len(text)
        # Empty initialization added to appease pychecker.
        last_rd = None
        for d in range(len(pattern)):
            # Scan for the best match each iteration allows for one more error.
            # Run a binary search to determine how far from 'loc' we can stray at
            # this error level.
            bin_min = 0
            bin_mid = bin_max
            while bin_min < bin_mid:
                if match_bitapScore(d, loc + bin_mid) <= score_threshold:
                    bin_min = bin_mid
                else:
                    bin_max = bin_mid
                bin_mid = (bin_max - bin_min) // 2 + bin_min

            # Use the result from this iteration as the maximum for the next.
            bin_max = bin_mid
            start = max(1, loc - bin_mid + 1)
            finish = min(loc + bin_mid, len(text)) + len(pattern)

            rd = [0] * (finish + 2)
            rd[finish + 1] = (1 << d) - 1
            for j in range(finish, start - 1, -1):
                if len(text) <= j - 1:
                    # Out of range.
                    charMatch = 0
                else:
                    charMatch = s.get(text[j - 1], 0)
                if d == 0:  # First pass: exact match.
                    rd[j] = ((rd[j + 1] << 1) | 1) & charMatch
                else:  # Subsequent passes: fuzzy match.
                    rd[j] = (
                        (((rd[j + 1] << 1) | 1) & charMatch)
                        | (((last_rd[j + 1] | last_rd[j]) << 1) | 1)
                        | last_rd[j + 1]
                    )
                if rd[j] & matchmask:
                    score = match_bitapScore(d, j - 1)
                    # This match will almost certainly be better than any existing match.
                    # But check anyway.
                    if score <= score_threshold:
                        # Told you so.
                        score_threshold = score
                        best_loc = j - 1
                        if best_loc > loc:
                            # When passing loc, don't exceed our current distance from loc.
                            start = max(1, 2 * loc - best_loc)
                        else:
                            # Already passed loc, downhill from here on in.
                            break
            # No hope for a (better) match at greater error levels.
            if match_bitapScore(d + 1, loc) > score_threshold:
                break
            last_rd = rd
        return best_loc

    def match_alphabet(self, pattern):
        """Initialise the alphabet for the Bitap algorithm.

        Args:
          pattern: The text to encode.

        Returns:
          Hash of character locations.
        """
        s = {}
        for char in pattern:
            s[char] = 0
        for i in range(len(pattern)):
            s[pattern[i]] |= 1 << (len(pattern) - i - 1)
        return s

    #  PATCH FUNCTIONS

    def patch_addContext(self, patch, text):
        """Increase the context until it is unique,
        but don't let the pattern expand beyond Match_MaxBits.

        Args:
          patch: The patch to grow.
          text: Source text.
        """
        if len(text) == 0:
            return
        pattern = text[patch.start2 : patch.start2 + patch.length1]
        padding = 0

        # Look for the first and last matches of pattern in text.  If two different
        # matches are found, increase the pattern length.
        while text.find(pattern) != text.rfind(pattern) and (
            self.Match_MaxBits == 0
            or len(pattern) < self.Match_MaxBits - self.Patch_Margin - self.Patch_Margin
        ):
            padding += self.Patch_Margin
            pattern = text[
                max(0, patch.start2 - padding) : patch.start2 + patch.length1 + padding
            ]
        # Add one chunk for good luck.
        padding += self.Patch_Margin

        # Add the prefix.
        prefix = text[max(0, patch.start2 - padding) : patch.start2]
        if prefix:
            patch.diffs[:0] = [(self.DIFF_EQUAL, prefix)]
        # Add the suffix.
        suffix = text[
            patch.start2 + patch.length1 : patch.start2 + patch.length1 + padding
        ]
        if suffix:
            patch.diffs.append((self.DIFF_EQUAL, suffix))

        # Roll back the start points.
        patch.start1 -= len(prefix)
        patch.start2 -= len(prefix)
        # Extend lengths.
        patch.length1 += len(prefix) + len(suffix)
        patch.length2 += len(prefix) + len(suffix)

    def patch_make(self, a, b=None, c=None):
        """Compute a list of patches to turn text1 into text2.
        Use diffs if provided, otherwise compute it ourselves.
        There are four ways to call this function, depending on what data is
        available to the caller:
        Method 1:
        a = text1, b = text2
        Method 2:
        a = diffs
        Method 3 (optimal):
        a = text1, b = diffs
        Method 4 (deprecated, use method 3):
        a = text1, b = text2, c = diffs

        Args:
          a: text1 (methods 1,3,4) or Array of diff tuples for text1 to
              text2 (method 2).
          b: text2 (methods 1,4) or Array of diff tuples for text1 to
              text2 (method 3) or undefined (method 2).
          c: Array of diff tuples for text1 to text2 (method 4) or
              undefined (methods 1,2,3).

        Returns:
          Array of Patch objects.
        """
        text1 = None
        diffs = None
        if isinstance(a, str) and isinstance(b, str) and c is None:
            # Method 1: text1, text2
            # Compute diffs from text1 and text2.
            text1 = a
            diffs = self.diff_main(text1, b, True)
            if len(diffs) > 2:
                self.diff_cleanupSemantic(diffs)
                self.diff_cleanupEfficiency(diffs)
        elif isinstance(a, list) and b is None and c is None:
            # Method 2: diffs
            # Compute text1 from diffs.
            diffs = a
            text1 = self.diff_text1(diffs)
        elif isinstance(a, str) and isinstance(b, list) and c is None:
            # Method 3: text1, diffs
            text1 = a
            diffs = b
        elif isinstance(a, str) and isinstance(b, str) and isinstance(c, list):
            # Method 4: text1, text2, diffs
            # text2 is not used.
            text1 = a
            diffs = c
        else:
            raise ValueError("Unknown call format to patch_make.")

        if not diffs:
            return []  # Get rid of the None case.
        patches = []
        patch = patch_obj()
        char_count1 = 0  # Number of characters into the text1 string.
        char_count2 = 0  # Number of characters into the text2 string.
        prepatch_text = text1  # Recreate the patches to determine context info.
        postpatch_text = text1
        for x in range(len(diffs)):
            (diff_type, diff_text) = diffs[x]
            if len(patch.diffs) == 0 and diff_type != self.DIFF_EQUAL:
                # A new patch starts here.
                patch.start1 = char_count1
                patch.start2 = char_count2
            if diff_type == self.DIFF_INSERT:
                # Insertion
                patch.diffs.append(diffs[x])
                patch.length2 += len(diff_text)
                postpatch_text = (
                    postpatch_text[:char_count2]
                    + diff_text
                    + postpatch_text[char_count2:]
                )
            elif diff_type == self.DIFF_DELETE:
                # Deletion.
                patch.length1 += len(diff_text)
                patch.diffs.append(diffs[x])
                postpatch_text = (
                    postpatch_text[:char_count2]
                    + postpatch_text[char_count2 + len(diff_text) :]
                )
            elif (
                diff_type == self.DIFF_EQUAL
                and len(diff_text) <= 2 * self.Patch_Margin
                and len(patch.diffs) != 0
                and len(diffs) != x + 1
            ):
                # Small equality inside a patch.
                patch.diffs.append(diffs[x])
                patch.length1 += len(diff_text)
                patch.length2 += len(diff_text)

            if diff_type == self.DIFF_EQUAL and len(diff_text) >= 2 * self.Patch_Margin:
                # Time for a new patch.
                if len(patch.diffs) != 0:
                    self.patch_addContext(patch, prepatch_text)
                    patches.append(patch)
                    patch = patch_obj()
                    # Unlike Unidiff, our patch lists have a rolling context.
                    # https://github.com/google/diff-match-patch/wiki/Unidiff
                    # Update prepatch text & pos to reflect the application of the
                    # just completed patch.
                    prepatch_text = postpatch_text
                    char_count1 = char_count2

            # Update the current character count.
            if diff_type != self.DIFF_INSERT:
                char_count1 += len(diff_text)
            if diff_type != self.DIFF_DELETE:
                char_count2 += len(diff_text)

        # Pick up the leftover patch if not empty.
        if len(patch.diffs) != 0:
            self.patch_addContext(patch, prepatch_text)
            patches.append(patch)
        return patches

    def patch_deepCopy(self, patches):
        """Given an array of patches, return another array that is identical.

        Args:
          patches: Array of Patch objects.

        Returns:
          Array of Patch objects.
        """
        patchesCopy = []
        for patch in patches:
            patchCopy = patch_obj()
            # No need to deep copy the tuples since they are immutable.
            patchCopy.diffs = patch.diffs[:]
            patchCopy.start1 = patch.start1
            patchCopy.start2 = patch.start2
            patchCopy.length1 = patch.length1
            patchCopy.length2 = patch.length2
            patchesCopy.append(patchCopy)
        return patchesCopy

    def patch_apply(self, patches, text):
        """Merge a set of patches onto the text.  Return a patched text, as well
        as a list of true/false values indicating which patches were applied.

        Args:
          patches: Array of Patch objects.
          text: Old text.

        Returns:
          Two element Array, containing the new text and an array of boolean values.
        """
        if not patches:
            return (text, [])

        # Deep copy the patches so that no changes are made to originals.
        patches = self.patch_deepCopy(patches)

        nullPadding = self.patch_addPadding(patches)
        text = nullPadding + text + nullPadding
        self.patch_splitMax(patches)

        # delta keeps track of the offset between the expected and actual location
        # of the previous patch.  If there are patches expected at positions 10 and
        # 20, but the first patch was found at 12, delta is 2 and the second patch
        # has an effective expected position of 22.
        delta = 0
        results = []
        for patch in patches:
            expected_loc = patch.start2 + delta
            text1 = self.diff_text1(patch.diffs)
            end_loc = -1
            if len(text1) > self.Match_MaxBits:
                # patch_splitMax will only provide an oversized pattern in the case of
                # a monster delete.
                start_loc = self.match_main(
                    text, text1[: self.Match_MaxBits], expected_loc
                )
                if start_loc != -1:
                    end_loc = self.match_main(
                        text,
                        text1[-self.Match_MaxBits :],
                        expected_loc + len(text1) - self.Match_MaxBits,
                    )
                    if end_loc == -1 or start_loc >= end_loc:
                        # Can't find valid trailing context.  Drop this patch.
                        start_loc = -1
            else:
                start_loc = self.match_main(text, text1, expected_loc)
            if start_loc == -1:
                # No match found.  :(
                results.append(False)
                # Subtract the delta for this failed patch from subsequent patches.
                delta -= patch.length2 - patch.length1
            else:
                # Found a match.  :)
                results.append(True)
                delta = start_loc - expected_loc
                if end_loc == -1:
                    text2 = text[start_loc : start_loc + len(text1)]
                else:
                    text2 = text[start_loc : end_loc + self.Match_MaxBits]
                if text1 == text2:
                    # Perfect match, just shove the replacement text in.
                    text = (
                        text[:start_loc]
                        + self.diff_text2(patch.diffs)
                        + text[start_loc + len(text1) :]
                    )
                else:
                    # Imperfect match.
                    # Run a diff to get a framework of equivalent indices.
                    diffs = self.diff_main(text1, text2, False)
                    if (
                        len(text1) > self.Match_MaxBits
                        and self.diff_levenshtein(diffs) / float(len(text1))
                        > self.Patch_DeleteThreshold
                    ):
                        # The end points match, but the content is unacceptably bad.
                        results[-1] = False
                    else:
                        self.diff_cleanupSemanticLossless(diffs)
                        index1 = 0
                        for op, data in patch.diffs:
                            if op != self.DIFF_EQUAL:
                                index2 = self.diff_xIndex(diffs, index1)
                            if op == self.DIFF_INSERT:  # Insertion
                                text = (
                                    text[: start_loc + index2]
                                    + data
                                    + text[start_loc + index2 :]
                                )
                            elif op == self.DIFF_DELETE:  # Deletion
                                text = (
                                    text[: start_loc + index2]
                                    + text[
                                        start_loc
                                        + self.diff_xIndex(diffs, index1 + len(data)) :
                                    ]
                                )
                            if op != self.DIFF_DELETE:
                                index1 += len(data)
        # Strip the padding off.
        text = text[len(nullPadding) : -len(nullPadding)]
        return (text, results)

    def patch_addPadding(self, patches):
        """Add some padding on text start and end so that edges can match
        something.  Intended to be called only from within patch_apply.

        Args:
          patches: Array of Patch objects.

        Returns:
          The padding string added to each side.
        """
        paddingLength = self.Patch_Margin
        nullPadding = ""
        for x in range(1, paddingLength + 1):
            nullPadding += chr(x)

        # Bump all the patches forward.
        for patch in patches:
            patch.start1 += paddingLength
            patch.start2 += paddingLength

        # Add some padding on start of first diff.
        patch = patches[0]
        diffs = patch.diffs
        if not diffs or diffs[0][0] != self.DIFF_EQUAL:
            # Add nullPadding equality.
            diffs.insert(0, (self.DIFF_EQUAL, nullPadding))
            patch.start1 -= paddingLength  # Should be 0.
            patch.start2 -= paddingLength  # Should be 0.
            patch.length1 += paddingLength
            patch.length2 += paddingLength
        elif paddingLength > len(diffs[0][1]):
            # Grow first equality.
            extraLength = paddingLength - len(diffs[0][1])
            newText = nullPadding[len(diffs[0][1]) :] + diffs[0][1]
            diffs[0] = (diffs[0][0], newText)
            patch.start1 -= extraLength
            patch.start2 -= extraLength
            patch.length1 += extraLength
            patch.length2 += extraLength

        # Add some padding on end of last diff.
        patch = patches[-1]
        diffs = patch.diffs
        if not diffs or diffs[-1][0] != self.DIFF_EQUAL:
            # Add nullPadding equality.
            diffs.append((self.DIFF_EQUAL, nullPadding))
            patch.length1 += paddingLength
            patch.length2 += paddingLength
        elif paddingLength > len(diffs[-1][1]):
            # Grow last equality.
            extraLength = paddingLength - len(diffs[-1][1])
            newText = diffs[-1][1] + nullPadding[:extraLength]
            diffs[-1] = (diffs[-1][0], newText)
            patch.length1 += extraLength
            patch.length2 += extraLength

        return nullPadding

    def patch_splitMax(self, patches):
        """Look through the patches and break up any which are longer than the
        maximum limit of the match algorithm.
        Intended to be called only from within patch_apply.

        Args:
          patches: Array of Patch objects.
        """
        patch_size = self.Match_MaxBits
        if patch_size == 0:
            # Python has the option of not splitting strings due to its ability
            # to handle integers of arbitrary precision.
            return
        for x in range(len(patches)):
            if patches[x].length1 <= patch_size:
                continue
            bigpatch = patches[x]
            # Remove the big old patch.
            del patches[x]
            x -= 1
            start1 = bigpatch.start1
            start2 = bigpatch.start2
            precontext = ""
            while len(bigpatch.diffs) != 0:
                # Create one of several smaller patches.
                patch = patch_obj()
                empty = True
                patch.start1 = start1 - len(precontext)
                patch.start2 = start2 - len(precontext)
                if precontext:
                    patch.length1 = patch.length2 = len(precontext)
                    patch.diffs.append((self.DIFF_EQUAL, precontext))

                while (
                    len(bigpatch.diffs) != 0
                    and patch.length1 < patch_size - self.Patch_Margin
                ):
                    (diff_type, diff_text) = bigpatch.diffs[0]
                    if diff_type == self.DIFF_INSERT:
                        # Insertions are harmless.
                        patch.length2 += len(diff_text)
                        start2 += len(diff_text)
                        patch.diffs.append(bigpatch.diffs.pop(0))
                        empty = False
                    elif (
                        diff_type == self.DIFF_DELETE
                        and len(patch.diffs) == 1
                        and patch.diffs[0][0] == self.DIFF_EQUAL
                        and len(diff_text) > 2 * patch_size
                    ):
                        # This is a large deletion.  Let it pass in one chunk.
                        patch.length1 += len(diff_text)
                        start1 += len(diff_text)
                        empty = False
                        patch.diffs.append((diff_type, diff_text))
                        del bigpatch.diffs[0]
                    else:
                        # Deletion or equality.  Only take as much as we can stomach.
                        diff_text = diff_text[
                            : patch_size - patch.length1 - self.Patch_Margin
                        ]
                        patch.length1 += len(diff_text)
                        start1 += len(diff_text)
                        if diff_type == self.DIFF_EQUAL:
                            patch.length2 += len(diff_text)
                            start2 += len(diff_text)
                        else:
                            empty = False

                        patch.diffs.append((diff_type, diff_text))
                        if diff_text == bigpatch.diffs[0][1]:
                            del bigpatch.diffs[0]
                        else:
                            bigpatch.diffs[0] = (
                                bigpatch.diffs[0][0],
                                bigpatch.diffs[0][1][len(diff_text) :],
                            )

                # Compute the head context for the next patch.
                precontext = self.diff_text2(patch.diffs)
                precontext = precontext[-self.Patch_Margin :]
                # Append the end context for this patch.
                postcontext = self.diff_text1(bigpatch.diffs)[: self.Patch_Margin]
                if postcontext:
                    patch.length1 += len(postcontext)
                    patch.length2 += len(postcontext)
                    if len(patch.diffs) != 0 and patch.diffs[-1][0] == self.DIFF_EQUAL:
                        patch.diffs[-1] = (
                            self.DIFF_EQUAL,
                            patch.diffs[-1][1] + postcontext,
                        )
                    else:
                        patch.diffs.append((self.DIFF_EQUAL, postcontext))

                if not empty:
                    x += 1
                    patches.insert(x, patch)

    def patch_toText(self, patches):
        """Take a list of patches and return a textual representation.

        Args:
          patches: Array of Patch objects.

        Returns:
          Text representation of patches.
        """
        text = []
        for patch in patches:
            text.append(str(patch))
        return "".join(text)

    def patch_fromText(self, textline):
        """Parse a textual representation of patches and return a list of patch
        objects.

        Args:
          textline: Text representation of patches.

        Returns:
          Array of Patch objects.

        Raises:
          ValueError: If invalid input.
        """
        patches = []
        if not textline:
            return patches
        text = textline.split("\n")
        while len(text) != 0:
            m = re.match(r"^@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@$", text[0])
            if not m:
                raise ValueError("Invalid patch string: " + text[0])
            patch = patch_obj()
            patches.append(patch)
            patch.start1 = int(m.group(1))
            if m.group(2) == "":
                patch.start1 -= 1
                patch.length1 = 1
            elif m.group(2) == "0":
                patch.length1 = 0
            else:
                patch.start1 -= 1
                patch.length1 = int(m.group(2))

            patch.start2 = int(m.group(3))
            if m.group(4) == "":
                patch.start2 -= 1
                patch.length2 = 1
            elif m.group(4) == "0":
                patch.length2 = 0
            else:
                patch.start2 -= 1
                patch.length2 = int(m.group(4))

            del text[0]

            while len(text) != 0:
                if text[0]:
                    sign = text[0][0]
                else:
                    sign = ""
                line = urllib.parse.unquote(text[0][1:])
                if sign == "+":
                    # Insertion.
                    patch.diffs.append((self.DIFF_INSERT, line))
                elif sign == "-":
                    # Deletion.
                    patch.diffs.append((self.DIFF_DELETE, line))
                elif sign == " ":
                    # Minor equality.
                    patch.diffs.append((self.DIFF_EQUAL, line))
                elif sign == "@":
                    # Start of next patch.
                    break
                elif sign == "":
                    # Blank line?  Whatever.
                    pass
                else:
                    # WTF?
                    raise ValueError("Invalid patch mode: '%s'\n%s" % (sign, line))
                del text[0]
        return patches


class patch_obj:
    """Class representing one patch operation."""

    def __init__(self):
        """Initializes with an empty list of diffs."""
        self.diffs = []
        self.start1 = None
        self.start2 = None
        self.length1 = 0
        self.length2 = 0

    def __str__(self):
        """Emulate GNU diff's format.
        Header: @@ -382,8 +481,9 @@
        Indices are printed as 1-based, not 0-based.

        Returns:
          The GNU diff string.
        """
        if self.length1 == 0:
            coords1 = str(self.start1) + ",0"
        elif self.length1 == 1:
            coords1 = str(self.start1 + 1)
        else:
            coords1 = str(self.start1 + 1) + "," + str(self.length1)
        if self.length2 == 0:
            coords2 = str(self.start2) + ",0"
        elif self.length2 == 1:
            coords2 = str(self.start2 + 1)
        else:
            coords2 = str(self.start2 + 1) + "," + str(self.length2)
        text = ["@@ -", coords1, " +", coords2, " @@\n"]
        # Escape the body of the patch with %xx notation.
        for op, data in self.diffs:
            if op == diff_match_patch.DIFF_INSERT:
                text.append("+")
            elif op == diff_match_patch.DIFF_DELETE:
                text.append("-")
            elif op == diff_match_patch.DIFF_EQUAL:
                text.append(" ")
            # High ascii will raise UnicodeDecodeError.  Use Unicode instead.
            data = data.encode("utf-8")
            text.append(urllib.parse.quote(data, "!~*'();/?:@&=+$,# ") + "\n")
        return "".join(text)
