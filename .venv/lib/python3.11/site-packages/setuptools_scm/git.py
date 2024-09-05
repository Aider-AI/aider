from __future__ import annotations

import dataclasses
import logging
import os
import re
import shlex
import sys
import warnings

from datetime import date
from datetime import datetime
from datetime import timezone
from os.path import samefile
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Callable
from typing import Sequence

from . import Configuration
from . import _types as _t
from . import discover
from ._run_cmd import CompletedProcess as _CompletedProcess
from ._run_cmd import require_command as _require_command
from ._run_cmd import run as _run
from .integration import data_from_mime
from .scm_workdir import Workdir
from .version import ScmVersion
from .version import meta
from .version import tag_to_version

if TYPE_CHECKING:
    from . import hg_git
log = logging.getLogger(__name__)

REF_TAG_RE = re.compile(r"(?<=\btag: )([^,]+)\b")
DESCRIBE_UNSUPPORTED = "%(describe"

# If testing command in shell make sure to quote the match argument like
# '*[0-9]*' as it will expand before being sent to git if there are any matching
# files in current directory.
DEFAULT_DESCRIBE = [
    "git",
    "describe",
    "--dirty",
    "--tags",
    "--long",
    "--match",
    "*[0-9]*",
]


def run_git(
    args: Sequence[str | os.PathLike[str]],
    repo: Path,
    *,
    check: bool = False,
    timeout: int | None = None,
) -> _CompletedProcess:
    return _run(
        ["git", "--git-dir", repo / ".git", *args],
        cwd=repo,
        check=check,
        timeout=timeout,
    )


class GitWorkdir(Workdir):
    """experimental, may change at any time"""

    @classmethod
    def from_potential_worktree(cls, wd: _t.PathT) -> GitWorkdir | None:
        wd = Path(wd).resolve()
        real_wd = run_git(["rev-parse", "--show-prefix"], wd).parse_success(parse=str)
        if real_wd is None:
            return None
        else:
            real_wd = real_wd[:-1]  # remove the trailing pathsep

        if not real_wd:
            real_wd = os.fspath(wd)
        else:
            str_wd = os.fspath(wd)
            assert str_wd.replace("\\", "/").endswith(real_wd)
            # In windows wd contains ``\`` which should be replaced by ``/``
            # for this assertion to work.  Length of string isn't changed by replace
            # ``\\`` is just and escape for `\`
            real_wd = str_wd[: -len(real_wd)]
        log.debug("real root %s", real_wd)
        if not samefile(real_wd, wd):
            return None

        return cls(Path(real_wd))

    def is_dirty(self) -> bool:
        return run_git(
            ["status", "--porcelain", "--untracked-files=no"], self.path
        ).parse_success(
            parse=bool,
            default=False,
        )

    def get_branch(self) -> str | None:
        return run_git(
            ["rev-parse", "--abbrev-ref", "HEAD"],
            self.path,
        ).parse_success(
            parse=str,
            error_msg="branch err (abbrev-err)",
        ) or run_git(
            ["symbolic-ref", "--short", "HEAD"],
            self.path,
        ).parse_success(
            parse=str,
            error_msg="branch err (symbolic-ref)",
        )

    def get_head_date(self) -> date | None:
        def parse_timestamp(timestamp_text: str) -> date | None:
            if "%c" in timestamp_text:
                log.warning("git too old -> timestamp is %r", timestamp_text)
                return None
            if sys.version_info < (3, 11) and timestamp_text.endswith("Z"):
                timestamp_text = timestamp_text[:-1] + "+00:00"
            return datetime.fromisoformat(timestamp_text).date()

        res = run_git(
            [
                *("-c", "log.showSignature=false"),
                *("log", "-n", "1", "HEAD"),
                "--format=%cI",
            ],
            self.path,
        )
        return res.parse_success(
            parse=parse_timestamp,
            error_msg="logging the iso date for head failed",
        )

    def is_shallow(self) -> bool:
        return self.path.joinpath(".git/shallow").is_file()

    def fetch_shallow(self) -> None:
        run_git(["fetch", "--unshallow"], self.path, check=True, timeout=240)

    def node(self) -> str | None:
        def _unsafe_short_node(node: str) -> str:
            return node[:7]

        return run_git(
            ["rev-parse", "--verify", "--quiet", "HEAD"], self.path
        ).parse_success(
            parse=_unsafe_short_node,
        )

    def count_all_nodes(self) -> int:
        res = run_git(["rev-list", "HEAD"], self.path)
        return res.stdout.count("\n") + 1

    def default_describe(self) -> _CompletedProcess:
        return run_git(DEFAULT_DESCRIBE[1:], self.path)


def warn_on_shallow(wd: GitWorkdir) -> None:
    """experimental, may change at any time"""
    if wd.is_shallow():
        warnings.warn(f'"{wd.path}" is shallow and may cause errors')


def fetch_on_shallow(wd: GitWorkdir) -> None:
    """experimental, may change at any time"""
    if wd.is_shallow():
        warnings.warn(f'"{wd.path}" was shallow, git fetch was used to rectify')
        wd.fetch_shallow()


def fail_on_shallow(wd: GitWorkdir) -> None:
    """experimental, may change at any time"""
    if wd.is_shallow():
        raise ValueError(
            f'{wd.path} is shallow, please correct with "git fetch --unshallow"'
        )


def get_working_directory(config: Configuration, root: _t.PathT) -> GitWorkdir | None:
    """
    Return the working directory (``GitWorkdir``).
    """

    if config.parent:  # todo broken
        return GitWorkdir.from_potential_worktree(config.parent)

    for potential_root in discover.walk_potential_roots(
        root, search_parents=config.search_parent_directories
    ):
        potential_wd = GitWorkdir.from_potential_worktree(potential_root)
        if potential_wd is not None:
            return potential_wd

    return GitWorkdir.from_potential_worktree(root)


def parse(
    root: _t.PathT,
    config: Configuration,
    describe_command: str | list[str] | None = None,
    pre_parse: Callable[[GitWorkdir], None] = warn_on_shallow,
) -> ScmVersion | None:
    """
    :param pre_parse: experimental pre_parse action, may change at any time
    """
    _require_command("git")
    wd = get_working_directory(config, root)
    if wd:
        return _git_parse_inner(
            config, wd, describe_command=describe_command, pre_parse=pre_parse
        )
    else:
        return None


def version_from_describe(
    wd: GitWorkdir | hg_git.GitWorkdirHgClient,
    config: Configuration,
    describe_command: _t.CMD_TYPE | None,
) -> ScmVersion | None:
    pass

    if config.git_describe_command is not None:
        describe_command = config.git_describe_command

    if describe_command is not None:
        if isinstance(describe_command, str):
            describe_command = shlex.split(describe_command)
            # todo: figure how to ensure git with gitdir gets correctly invoked
        if describe_command[0] == "git":
            describe_res = run_git(describe_command[1:], wd.path)
        else:
            describe_res = _run(describe_command, wd.path)
    else:
        describe_res = wd.default_describe()

    def parse_describe(output: str) -> ScmVersion:
        tag, distance, node, dirty = _git_parse_describe(output)
        return meta(tag=tag, distance=distance, dirty=dirty, node=node, config=config)

    return describe_res.parse_success(parse=parse_describe)


def _git_parse_inner(
    config: Configuration,
    wd: GitWorkdir | hg_git.GitWorkdirHgClient,
    pre_parse: None | (Callable[[GitWorkdir | hg_git.GitWorkdirHgClient], None]) = None,
    describe_command: _t.CMD_TYPE | None = None,
) -> ScmVersion:
    if pre_parse:
        pre_parse(wd)

    version = version_from_describe(wd, config, describe_command)

    if version is None:
        # If 'git git_describe_command' failed, try to get the information otherwise.
        tag = config.version_cls("0.0")
        node = wd.node()
        if node is None:
            distance = 0
            dirty = True
        else:
            distance = wd.count_all_nodes()
            node = "g" + node
            dirty = wd.is_dirty()
        version = meta(
            tag=tag, distance=distance, dirty=dirty, node=node, config=config
        )
    branch = wd.get_branch()
    node_date = wd.get_head_date() or datetime.now(timezone.utc).date()
    return dataclasses.replace(version, branch=branch, node_date=node_date)


def _git_parse_describe(
    describe_output: str,
) -> tuple[str, int, str | None, bool]:
    # 'describe_output' looks e.g. like 'v1.5.0-0-g4060507' or
    # 'v1.15.1rc1-37-g9bd1298-dirty'.
    # It may also just be a bare tag name if this is a tagged commit and we are
    # parsing a .git_archival.txt file.

    if describe_output.endswith("-dirty"):
        dirty = True
        describe_output = describe_output[:-6]
    else:
        dirty = False

    split = describe_output.rsplit("-", 2)
    if len(split) < 3:  # probably a tagged commit
        tag = describe_output
        number = 0
        node = None
    else:
        tag, number_, node = split
        number = int(number_)
    return tag, number, node, dirty


def archival_to_version(
    data: dict[str, str], config: Configuration
) -> ScmVersion | None:
    node: str | None
    log.debug("data %s", data)
    archival_describe = data.get("describe-name", DESCRIBE_UNSUPPORTED)
    if DESCRIBE_UNSUPPORTED in archival_describe:
        warnings.warn("git archive did not support describe output")
    else:
        tag, number, node, _ = _git_parse_describe(archival_describe)
        return meta(
            tag,
            config=config,
            distance=number,
            node=node,
        )

    for ref in REF_TAG_RE.findall(data.get("ref-names", "")):
        version = tag_to_version(ref, config)
        if version is not None:
            return meta(version, config=config)
    else:
        node = data.get("node")
        if node is None:
            return None
        elif "$FORMAT" in node.upper():
            warnings.warn("unprocessed git archival found (no export subst applied)")
            return None
        else:
            return meta("0.0", node=node, config=config)


def parse_archival(root: _t.PathT, config: Configuration) -> ScmVersion | None:
    archival = os.path.join(root, ".git_archival.txt")
    data = data_from_mime(archival)
    return archival_to_version(data, config=config)
