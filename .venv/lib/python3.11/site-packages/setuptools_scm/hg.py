from __future__ import annotations

import datetime
import logging
import os

from pathlib import Path
from typing import TYPE_CHECKING

from . import Configuration
from ._version_cls import Version
from .integration import data_from_mime
from .scm_workdir import Workdir
from .version import ScmVersion
from .version import meta
from .version import tag_to_version

if TYPE_CHECKING:
    from . import _types as _t

from ._run_cmd import require_command as _require_command
from ._run_cmd import run as _run

log = logging.getLogger(__name__)


class HgWorkdir(Workdir):
    @classmethod
    def from_potential_worktree(cls, wd: _t.PathT) -> HgWorkdir | None:
        res = _run(["hg", "root"], wd)
        if res.returncode:
            return None
        return cls(Path(res.stdout))

    def get_meta(self, config: Configuration) -> ScmVersion | None:
        node: str
        tags_str: str
        node_date_str: str
        node, tags_str, node_date_str = self.hg_log(
            ".", "{node}\n{tag}\n{date|shortdate}"
        ).split("\n")

        # TODO: support bookmarks and topics (but nowadays bookmarks are
        # mainly used to emulate Git branches, which is already supported with
        # the dedicated class GitWorkdirHgClient)

        branch, dirty_str, dirty_date = _run(
            ["hg", "id", "-T", "{branch}\n{if(dirty, 1, 0)}\n{date|shortdate}"],
            cwd=self.path,
            check=True,
        ).stdout.split("\n")
        dirty = bool(int(dirty_str))
        node_date = datetime.date.fromisoformat(dirty_date if dirty else node_date_str)

        if node == "0" * len(node):
            log.debug("initial node %s", self.path)
            return meta(
                Version("0.0"),
                config=config,
                dirty=dirty,
                branch=branch,
                node_date=node_date,
            )

        node = "h" + node[:7]

        tags = tags_str.split()
        if "tip" in tags:
            # tip is not a real tag
            tags.remove("tip")

        if tags:
            tag = tag_to_version(tags[0], config)
            if tag:
                return meta(tag, dirty=dirty, branch=branch, config=config)

        try:
            tag_str = self.get_latest_normalizable_tag()
            if tag_str is None:
                dist = self.get_distance_revs("")
            else:
                dist = self.get_distance_revs(tag_str)

            if tag_str == "null" or tag_str is None:
                tag = Version("0.0")
                dist += 1
            else:
                tag = tag_to_version(tag_str, config=config)
                assert tag is not None

            if self.check_changes_since_tag(tag_str) or dirty:
                return meta(
                    tag,
                    distance=dist,
                    node=node,
                    dirty=dirty,
                    branch=branch,
                    config=config,
                    node_date=node_date,
                )
            else:
                return meta(tag, config=config, node_date=node_date)

        except ValueError as e:
            log.exception("error %s", e)
            pass  # unpacking failed, old hg

        return None

    def hg_log(self, revset: str, template: str) -> str:
        cmd = ["hg", "log", "-r", revset, "-T", template]

        return _run(cmd, cwd=self.path, check=True).stdout

    def get_latest_normalizable_tag(self) -> str | None:
        # Gets all tags containing a '.' (see #229) from oldest to newest
        outlines = self.hg_log(
            revset="ancestors(.) and tag('re:\\.')",
            template="{tags}{if(tags, '\n', '')}",
        ).split()
        if not outlines:
            return None
        tag = outlines[-1].split()[-1]
        return tag

    def get_distance_revs(self, rev1: str, rev2: str = ".") -> int:
        revset = f"({rev1}::{rev2})"
        out = self.hg_log(revset, ".")
        return len(out) - 1

    def check_changes_since_tag(self, tag: str | None) -> bool:
        if tag == "0.0" or tag is None:
            return True

        revset = (
            "(branch(.)"  # look for revisions in this branch only
            f" and tag({tag!r})::."  # after the last tag
            # ignore commits that only modify .hgtags and nothing else:
            " and (merge() or file('re:^(?!\\.hgtags).*$'))"
            f" and not tag({tag!r}))"  # ignore the tagged commit itself
        )

        return bool(self.hg_log(revset, "."))


def parse(root: _t.PathT, config: Configuration) -> ScmVersion | None:
    _require_command("hg")
    if os.path.exists(os.path.join(root, ".hg/git")):
        res = _run(["hg", "path"], root)
        if not res.returncode:
            for line in res.stdout.split("\n"):
                if line.startswith("default ="):
                    path = Path(line.split()[2])
                    if path.name.endswith(".git") or (path / ".git").exists():
                        from .git import _git_parse_inner
                        from .hg_git import GitWorkdirHgClient

                        wd_hggit = GitWorkdirHgClient.from_potential_worktree(root)
                        if wd_hggit:
                            return _git_parse_inner(config, wd_hggit)

    wd = HgWorkdir.from_potential_worktree(config.absolute_root)

    if wd is None:
        return None

    return wd.get_meta(config)


def archival_to_version(data: dict[str, str], config: Configuration) -> ScmVersion:
    log.debug("data %s", data)
    node = data.get("node", "")[:12]
    if node:
        node = "h" + node
    if "tag" in data:
        return meta(data["tag"], config=config)
    elif "latesttag" in data:
        return meta(
            data["latesttag"],
            distance=int(data["latesttagdistance"]),
            node=node,
            branch=data.get("branch"),
            config=config,
        )
    else:
        return meta(config.version_cls("0.0"), node=node, config=config)


def parse_archival(root: _t.PathT, config: Configuration) -> ScmVersion:
    archival = os.path.join(root, ".hg_archival.txt")
    data = data_from_mime(archival)
    return archival_to_version(data, config=config)
