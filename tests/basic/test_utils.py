import os

from aider.utils import AnsiStripper, safe_abs_path, strip_ansi


def test_safe_abs_path_symlink_loop(tmp_path):
    # Create circular symlink: a -> b -> a
    link_a = tmp_path / "link_a"
    link_b = tmp_path / "link_b"
    link_a.symlink_to(link_b)
    link_b.symlink_to(link_a)

    # safe_abs_path must not raise, and must return an absolute path
    result = safe_abs_path(str(link_a))
    assert os.path.isabs(result)


def test_strip_ansi_csi():
    assert strip_ansi("\x1b[2J\x1b[1;1Hhello") == "hello"
    assert strip_ansi("a\x1b[31mb\x1b[0mc") == "abc"


def test_strip_ansi_osc():
    assert strip_ansi("\x1b]8;;https://example.com\x07link\x1b]8;;\x07") == "link"
    assert strip_ansi("\x1b]8;;https://example.com\x1b\\link") == "link"


def test_strip_ansi_plain_text_unchanged():
    assert strip_ansi("hello\nworld [not an escape]") == "hello\nworld [not an escape]"


def test_ansi_stripper_split_sequence():
    stripper = AnsiStripper()
    out = ""
    for chunk in ["\x1b", "[", "2", "J", "hi", "\x1b]8;;https://example.com", "\x07", "ok"]:
        out += stripper.feed(chunk)
    out += stripper.flush()
    assert out == "hiok"
    assert "\x1b" not in out
