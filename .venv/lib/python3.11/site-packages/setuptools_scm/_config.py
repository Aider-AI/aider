"""configuration"""

from __future__ import annotations

import dataclasses
import os
import re
import warnings

from pathlib import Path
from typing import Any
from typing import Pattern
from typing import Protocol

from . import _log
from . import _types as _t
from ._integration.pyproject_reading import (
    get_args_for_pyproject as _get_args_for_pyproject,
)
from ._integration.pyproject_reading import read_pyproject as _read_pyproject
from ._overrides import read_toml_overrides
from ._version_cls import Version as _Version
from ._version_cls import _validate_version_cls
from ._version_cls import _VersionT

log = _log.log.getChild("config")

DEFAULT_TAG_REGEX = re.compile(
    r"^(?:[\w-]+-)?(?P<version>[vV]?\d+(?:\.\d+){0,2}[^\+]*)(?:\+.*)?$"
)
"""default tag regex that tries to match PEP440 style versions
with prefix consisting of dashed words"""

DEFAULT_VERSION_SCHEME = "guess-next-dev"
DEFAULT_LOCAL_SCHEME = "node-and-date"


def _check_tag_regex(value: str | Pattern[str] | None) -> Pattern[str]:
    if not value:
        regex = DEFAULT_TAG_REGEX
    else:
        regex = re.compile(value)

    group_names = regex.groupindex.keys()
    if regex.groups == 0 or (regex.groups > 1 and "version" not in group_names):
        warnings.warn(
            "Expected tag_regex to contain a single match group or a group named"
            " 'version' to identify the version part of any tag."
        )

    return regex


class ParseFunction(Protocol):
    def __call__(
        self, root: _t.PathT, *, config: Configuration
    ) -> _t.SCMVERSION | None: ...


def _check_absolute_root(root: _t.PathT, relative_to: _t.PathT | None) -> str:
    log.debug("check absolute root=%s relative_to=%s", root, relative_to)
    if relative_to:
        if (
            os.path.isabs(root)
            and os.path.isabs(relative_to)
            and not os.path.commonpath([root, relative_to]) == root
        ):
            warnings.warn(
                f"absolute root path '{root}' overrides relative_to '{relative_to}'"
            )
        if os.path.isdir(relative_to):
            warnings.warn(
                "relative_to is expected to be a file,"
                f" its the directory {relative_to}\n"
                "assuming the parent directory was passed"
            )
            log.debug("dir %s", relative_to)
            root = os.path.join(relative_to, root)
        else:
            log.debug("file %s", relative_to)
            root = os.path.join(os.path.dirname(relative_to), root)
    return os.path.abspath(root)


@dataclasses.dataclass
class Configuration:
    """Global configuration model"""

    relative_to: _t.PathT | None = None
    root: _t.PathT = "."
    version_scheme: _t.VERSION_SCHEME = DEFAULT_VERSION_SCHEME
    local_scheme: _t.VERSION_SCHEME = DEFAULT_LOCAL_SCHEME
    tag_regex: Pattern[str] = DEFAULT_TAG_REGEX
    parentdir_prefix_version: str | None = None
    fallback_version: str | None = None
    fallback_root: _t.PathT = "."
    write_to: _t.PathT | None = None
    write_to_template: str | None = None
    version_file: _t.PathT | None = None
    version_file_template: str | None = None
    parse: ParseFunction | None = None
    git_describe_command: _t.CMD_TYPE | None = None
    dist_name: str | None = None
    version_cls: type[_VersionT] = _Version
    search_parent_directories: bool = False

    parent: _t.PathT | None = None

    @property
    def absolute_root(self) -> str:
        return _check_absolute_root(self.root, self.relative_to)

    @classmethod
    def from_file(
        cls,
        name: str | os.PathLike[str] = "pyproject.toml",
        dist_name: str | None = None,
        _require_section: bool = True,
        **kwargs: Any,
    ) -> Configuration:
        """
        Read Configuration from pyproject.toml (or similar).
        Raises exceptions when file is not found or toml is
        not installed or the file has invalid format or does
        not contain the [tool.setuptools_scm] section.
        """

        pyproject_data = _read_pyproject(Path(name), require_section=_require_section)
        args = _get_args_for_pyproject(pyproject_data, dist_name, kwargs)

        args.update(read_toml_overrides(args["dist_name"]))
        relative_to = args.pop("relative_to", name)
        return cls.from_data(relative_to=relative_to, data=args)

    @classmethod
    def from_data(
        cls, relative_to: str | os.PathLike[str], data: dict[str, Any]
    ) -> Configuration:
        """
        given configuration data
        create a config instance after validating tag regex/version class
        """
        tag_regex = _check_tag_regex(data.pop("tag_regex", None))
        version_cls = _validate_version_cls(
            data.pop("version_cls", None), data.pop("normalize", True)
        )
        return cls(
            relative_to=relative_to,
            version_cls=version_cls,
            tag_regex=tag_regex,
            **data,
        )
