import pytest

from aider.coders.patch_coder import PatchCoder
from aider.io import InputOutput
from aider.models import Model


@pytest.mark.parametrize(("replacement", "expected"), [("", b""), ("+\n", b"\n")])
def test_update_removing_only_line(tmp_path, monkeypatch, replacement, expected):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "one.txt"
    path.write_bytes(b"old\n")
    coder = PatchCoder(
        main_model=Model("gpt-3.5-turbo"),
        io=InputOutput(yes=True),
        fnames=[str(path)],
        use_git=False,
    )
    coder.partial_response_content = (
        "*** Begin Patch\n*** Update File: one.txt\n@@\n-old\n" + replacement + "*** End Patch"
    )

    coder.apply_updates()

    assert path.read_bytes() == expected
