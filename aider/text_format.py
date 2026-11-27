"""
Keep the on-disk format of a file (encoding, BOM, line endings) intact across edits.

The rest of aider works on text with "\\n" line endings. These helpers convert
between that and the bytes on disk.
"""

import codecs
import re
from collections import Counter
from difflib import SequenceMatcher

# Tried when a file isn't valid UTF-8. Common for older files written on Windows.
FALLBACK_ENCODING = "cp1252"

BOMS = (
    (codecs.BOM_UTF8, "utf-8"),
    (codecs.BOM_UTF16_LE, "utf-16-le"),
    (codecs.BOM_UTF16_BE, "utf-16-be"),
)

LINE_RE = re.compile(r"([^\r\n]*)(\r\n|\r|\n)|([^\r\n]+)\Z")


def decode(data, encoding):
    """
    Decode the bytes of a file, returning (text, encoding, bom).

    Line endings in the returned text are untouched. Raises UnicodeError if the
    bytes can't be decoded.
    """
    codec = codecs.lookup(encoding).name

    if codec in ("utf-8", "utf-8-sig", "utf-16"):
        for bom, bom_encoding in BOMS:
            if data.startswith(bom):
                return data[len(bom) :].decode(bom_encoding), bom_encoding, bom

    try:
        return data.decode(encoding), encoding, b""
    except UnicodeDecodeError as err:
        # Only guess when using the default, and never for what looks like binary data
        if codec != "utf-8" or b"\0" in data:
            raise
        try:
            return data.decode(FALLBACK_ENCODING), FALLBACK_ENCODING, b""
        except UnicodeDecodeError:
            raise err


def normalize_newlines(text):
    return text.replace("\r\n", "\n").replace("\r", "\n")


def split_lines(text):
    """Split into (line, ending) pairs, breaking only on \\r\\n, \\r and \\n."""
    return [(m[1], m[2]) if m[2] else (m[3], "") for m in LINE_RE.finditer(text)]


def apply_line_endings(old_text, new_text, default, force=None):
    """
    Return new_text using the line endings of old_text.

    Each line which is also in old_text keeps its own ending, so files with mixed
    endings are preserved. Changed and added lines take the ending of the line they
    replace or follow. A missing newline at the end of the file stays missing.

    :param default: Ending to use if old_text provides none.
    :param force: If set, use this ending for every line.
    """
    old = split_lines(old_text)
    new = [line for line, _ending in split_lines(normalize_newlines(new_text))]
    if not new:
        return ""

    counts = Counter(ending for _line, ending in old if ending)
    common = counts.most_common(1)[0][0] if counts else default

    if force:
        endings = [force] * len(new)
    else:
        endings = []
        matcher = SequenceMatcher(None, [line for line, _ending in old], new, autojunk=False)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            for offset in range(j2 - j1):
                if tag in ("equal", "replace"):
                    ending = old[min(i1 + offset, i2 - 1)][1]
                elif endings:
                    ending = endings[-1]
                else:
                    ending = old[i1][1] if i1 < len(old) else ""
                endings.append(ending or common)

    missing_final_newline = old and not old[-1][1]
    if missing_final_newline or not new_text.endswith(("\n", "\r")):
        endings[-1] = ""

    return "".join(line + ending for line, ending in zip(new, endings))
