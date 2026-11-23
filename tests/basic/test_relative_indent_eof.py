import pytest

from aider.coders.search_replace import RelativeIndenter
from aider.coders.udiff_coder import flexi_just_search_and_replace


@pytest.mark.parametrize("ending", ["  ", "\t", "\n", ""])
def test_relative_indent_round_trip_at_eof(ending):
    indent = "\t\t" if ending == "\t" else "    "
    original = f"if x:\n{indent}value = 1\n" + ending
    indenter = RelativeIndenter([original])
    assert indenter.make_absolute(indenter.make_relative(original)) == original


@pytest.mark.parametrize("ending", ["  ", "\t"])
def test_outdented_replacement_preserves_whitespace_only_eof(ending):
    indent = "\t\t" if ending == "\t" else "    "
    original = f"if x:\n{indent}a = 1\n{indent}b = 2\n" + ending
    result = flexi_just_search_and_replace(("a = 1\nb = 2\n", "a = 1\nb = 3\n", original))
    assert result == f"if x:\n{indent}a = 1\n{indent}b = 3\n" + ending
