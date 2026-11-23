from aider.coders import Coder
from aider.io import InputOutput
from aider.models import Model
from aider.repo import GitRepo
from aider.utils import make_repo


def test_pretty_diff_uses_selected_repository(tmp_path, monkeypatch, capsys):
    repo_dir = tmp_path / "selected"
    repo_dir.mkdir()
    repo = make_repo(repo_dir)
    path = repo_dir / "sample.txt"
    for text in ("original text", "updated text"):
        path.write_text(text + "\n", encoding="utf-8")
        repo.git.add("sample.txt")
        repo.git.commit("-m", text)

    monkeypatch.chdir(tmp_path)
    io = InputOutput(pretty=False, fancy_input=False, yes=True)
    selected_repo = GitRepo(io, [], str(repo_dir))
    coder = Coder.create(Model("gpt-3.5-turbo"), None, io, repo=selected_repo)
    coder.pretty = True  # Exercise the pretty path despite pytest capturing stdout.
    capsys.readouterr()

    coder.preproc_user_input("/diff")

    output = capsys.readouterr().out
    assert "-original text" in output
    assert "+updated text" in output
