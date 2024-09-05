from __future__ import annotations

import logging
import os

from contextlib import suppress
from datetime import date
from pathlib import Path

from . import _types as _t
from ._run_cmd import CompletedProcess as _CompletedProcess
from ._run_cmd import require_command
from ._run_cmd import run as _run
from .git import GitWorkdir
from .hg import HgWorkdir

log = logging.getLogger(__name__)

_FAKE_GIT_DESCRIBE_ERROR = _CompletedProcess(
    "fake git describe output for hg",
    1,
    "<>hg git failed to describe",
)


class GitWorkdirHgClient(GitWorkdir, HgWorkdir):
    COMMAND = "hg"

    @classmethod
    def from_potential_worktree(cls, wd: _t.PathT) -> GitWorkdirHgClient | None:
        require_command("hg")
        res = _run(["hg", "root"], cwd=wd).parse_success(parse=Path)
        if res is None:
            return None
        return cls(res)

    def is_dirty(self) -> bool:
        res = _run(["hg", "id", "-T", "{dirty}"], cwd=self.path, check=True)
        return bool(res.stdout)

    def get_branch(self) -> str | None:
        res = _run(["hg", "id", "-T", "{bookmarks}"], cwd=self.path)
        if res.returncode:
            log.info("branch err %s", res)
            return None
        return res.stdout

    def get_head_date(self) -> date | None:
        return _run('hg log -r . -T "{shortdate(date)}"', cwd=self.path).parse_success(
            parse=date.fromisoformat, error_msg="head date err"
        )

    def is_shallow(self) -> bool:
        return False

    def fetch_shallow(self) -> None:
        pass

    def get_hg_node(self) -> str | None:
        res = _run('hg log -r . -T "{node}"', cwd=self.path)
        if res.returncode:
            return None
        else:
            return res.stdout

    def _hg2git(self, hg_node: str) -> str | None:
        with suppress(FileNotFoundError):
            with open(os.path.join(self.path, ".hg/git-mapfile")) as map_items:
                for item in map_items:
                    if hg_node in item:
                        git_node, hg_node = item.split()
                        return git_node
        return None

    def node(self) -> str | None:
        hg_node = self.get_hg_node()
        if hg_node is None:
            return None

        git_node = self._hg2git(hg_node)

        if git_node is None:
            # trying again after hg -> git
            _run(["hg", "gexport"], cwd=self.path)
            git_node = self._hg2git(hg_node)

            if git_node is None:
                log.debug("Cannot get git node so we use hg node %s", hg_node)

                if hg_node == "0" * len(hg_node):
                    # mimic Git behavior
                    return None

                return hg_node

        return git_node[:7]

    def count_all_nodes(self) -> int:
        res = _run(["hg", "log", "-r", "ancestors(.)", "-T", "."], cwd=self.path)
        return len(res.stdout)

    def default_describe(self) -> _CompletedProcess:
        """
        Tentative to reproduce the output of

        `git describe --dirty --tags --long --match *[0-9]*`

        """
        res = _run(
            [
                "hg",
                "log",
                "-r",
                "(reverse(ancestors(.)) and tag(r're:v?[0-9].*'))",
                "-T",
                "{tags}{if(tags, ' ', '')}",
            ],
            cwd=self.path,
        )
        if res.returncode:
            return _FAKE_GIT_DESCRIBE_ERROR
        hg_tags: list[str] = res.stdout.split()

        if not hg_tags:
            return _FAKE_GIT_DESCRIBE_ERROR

        with self.path.joinpath(".hg/git-tags").open() as fp:
            git_tags: dict[str, str] = dict(line.split()[::-1] for line in fp)

        tag: str
        for hg_tag in hg_tags:
            if hg_tag in git_tags:
                tag = hg_tag
                break
        else:
            logging.warning("tag not found hg=%s git=%s", hg_tags, git_tags)
            return _FAKE_GIT_DESCRIBE_ERROR

        res = _run(["hg", "log", "-r", f"'{tag}'::.", "-T", "."], cwd=self.path)
        if res.returncode:
            return _FAKE_GIT_DESCRIBE_ERROR
        distance = len(res.stdout) - 1

        node = self.node()
        assert node is not None
        desc = f"{tag}-{distance}-g{node}"

        if self.is_dirty():
            desc += "-dirty"
        log.debug("faked describe %r", desc)
        return _CompletedProcess(
            ["setuptools-scm", "faked", "describe"],
            returncode=0,
            stdout=desc,
            stderr="",
        )
