import codecs

import pytest

from aider.coders.editblock_coder import EditBlockCoder
from aider.coders.patch_coder import PatchCoder
from aider.coders.udiff_coder import UnifiedDiffCoder
from aider.coders.wholefile_coder import WholeFileCoder
from aider.io import InputOutput
from aider.models import Model

LINES = [b"one", b"two", b"three", b"four"]


def edit(path, old="two", new="TWO", **io_args):
    io = InputOutput(yes=True, **io_args)
    io.write_text(path, io.read_text(path).replace(old, new))


@pytest.mark.parametrize(
    "before",
    [
        b"one\r\ntwo\r\nthree\r\n",
        b"one\ntwo\nthree\n",
        b"one\rtwo\rthree\r",
        b"one\r\ntwo\nthree\r\nfour\n",  # mixed
        b"one\r\ntwo\r\nthree",  # no final newline
        b"one\r\ntwo",  # edited line has no final newline
        codecs.BOM_UTF8 + b"one\r\ntwo\r\n",
        codecs.BOM_UTF16_LE + "one\r\ntwo\r\n".encode("utf-16-le"),
        codecs.BOM_UTF16_BE + "one\r\ntwo\r\n".encode("utf-16-be"),
        b"one \x96 caf\xe9\r\ntwo\r\n\x93three\x94\x85\r\n",  # cp1252
        b"one\x0c\r\ntwo\r\n",  # form feed is not a line break
    ],
)
def test_only_the_edit_changes(tmp_path, before):
    path = tmp_path / "file.txt"
    path.write_bytes(before)
    if before.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        enc = "utf-16-le" if before.startswith(codecs.BOM_UTF16_LE) else "utf-16-be"
        old, new = "two".encode(enc), "TWO".encode(enc)
    else:
        old, new = b"two", b"TWO"

    edit(path)

    assert path.read_bytes() == before.replace(old, new)


@pytest.mark.parametrize(
    "old, new, expected",
    [
        # inserted and removed lines in a mixed file
        ("two\n", "two\nnew\n", b"one\r\ntwo\nnew\nthree\r\nfour\n"),
        ("one\n", "new\none\n", b"new\r\none\r\ntwo\nthree\r\nfour\n"),
        ("two\n", "", b"one\r\nthree\r\nfour\n"),
    ],
)
def test_added_and_removed_lines(tmp_path, old, new, expected):
    path = tmp_path / "file.txt"
    path.write_bytes(b"one\r\ntwo\nthree\r\nfour\n")
    edit(path, old, new)
    assert path.read_bytes() == expected


def test_append_without_final_newline(tmp_path):
    path = tmp_path / "file.txt"
    path.write_bytes(b"one\r\ntwo")
    edit(path, "two", "two\nthree\n")
    assert path.read_bytes() == b"one\r\ntwo\r\nthree"


@pytest.mark.parametrize("line_endings, eol", [("lf", b"\n"), ("crlf", b"\r\n")])
def test_forced_line_endings(tmp_path, line_endings, eol):
    path = tmp_path / "file.txt"
    path.write_bytes(b"one\r\ntwo\n")
    edit(path, line_endings=line_endings)
    assert path.read_bytes() == b"one" + eol + b"TWO" + eol


def test_unencodable_text_leaves_file_alone(tmp_path):
    path = tmp_path / "file.txt"
    before = b"caf\xe9\r\ntwo\r\n"
    path.write_bytes(before)
    with pytest.raises(OSError):
        edit(path, new="✓")
    assert path.read_bytes() == before


def test_binary_data_is_not_guessed(tmp_path):
    path = tmp_path / "file.bin"
    path.write_bytes(b"\x00\xe9\x01")
    assert InputOutput().read_text(path) is None


def test_move_keeps_format(tmp_path):
    source = tmp_path / "old.txt"
    source.write_bytes(b"caf\xe9\r\ntwo\r\n")
    io = InputOutput()
    io.write_text(tmp_path / "new.txt", io.read_text(source), like=source)
    assert (tmp_path / "new.txt").read_bytes() == source.read_bytes()


@pytest.mark.parametrize(
    "coder_class, reply",
    [
        (
            EditBlockCoder,
            "file.txt\n```\n<<<<<<< SEARCH\ntwo\n=======\nTWO\n>>>>>>> REPLACE\n```\n",
        ),
        (
            UnifiedDiffCoder,
            "```diff\n--- file.txt\n+++ file.txt\n@@ ... @@\n one\n-two\n+TWO\n three\n```\n",
        ),
        (
            PatchCoder,
            "*** Begin Patch\n*** Update File: file.txt\n@@\n one\n-two\n+TWO\n three\n"
            "*** End Patch\n",
        ),
        (WholeFileCoder, "file.txt\n```\none\x0c\nTWO\nthree\ncaf\xe9\n```\n"),
    ],
)
def test_coders_only_change_edited_line(tmp_path, monkeypatch, coder_class, reply):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "file.txt"
    before = b"one\x0c\r\ntwo\r\nthree\r\ncaf\xe9\r\n"
    path.write_bytes(before)
    coder = coder_class(Model("gpt-3.5-turbo"), InputOutput(yes=True), fnames=[str(path)])
    coder.partial_response_content = reply

    coder.apply_updates()

    assert path.read_bytes() == before.replace(b"two", b"TWO")
