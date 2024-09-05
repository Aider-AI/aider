from __future__ import annotations

import logging
import re
import warnings

from pathlib import Path
from typing import Any
from typing import NoReturn
from typing import Pattern

from . import _config
from . import _entrypoints
from . import _run_cmd
from . import _types as _t
from ._config import Configuration
from ._overrides import _read_pretended_version_for
from ._version_cls import _validate_version_cls
from .version import ScmVersion
from .version import format_version as _format_version

EMPTY_TAG_REGEX_DEPRECATION = DeprecationWarning(
    "empty regex for tag regex is invalid, using default"
)

_log = logging.getLogger(__name__)


def parse_scm_version(config: Configuration) -> ScmVersion | None:
    try:
        if config.parse is not None:
            parse_result = config.parse(config.absolute_root, config=config)
            if parse_result is not None and not isinstance(parse_result, ScmVersion):
                raise TypeError(
                    f"version parse result was {str!r}\n"
                    "please return a parsed version (ScmVersion)"
                )
            return parse_result
        else:
            return _entrypoints.version_from_entrypoint(
                config,
                entrypoint="setuptools_scm.parse_scm",
                root=config.absolute_root,
            )
    except _run_cmd.CommandNotFoundError as e:
        _log.exception("command %s not found while parsing the scm, using fallbacks", e)
        return None


def parse_fallback_version(config: Configuration) -> ScmVersion | None:
    return _entrypoints.version_from_entrypoint(
        config,
        entrypoint="setuptools_scm.parse_scm_fallback",
        root=config.fallback_root,
    )


def parse_version(config: Configuration) -> ScmVersion | None:
    return (
        _read_pretended_version_for(config)
        or parse_scm_version(config)
        or parse_fallback_version(config)
    )


def write_version_files(
    config: Configuration, version: str, scm_version: ScmVersion
) -> None:
    if config.write_to is not None:
        from ._integration.dump_version import dump_version

        dump_version(
            root=config.root,
            version=version,
            scm_version=scm_version,
            write_to=config.write_to,
            template=config.write_to_template,
        )
    if config.version_file:
        from ._integration.dump_version import write_version_to_path

        version_file = Path(config.version_file)
        assert not version_file.is_absolute(), f"{version_file=}"
        # todo: use a better name than fallback root
        assert config.relative_to is not None
        target = Path(config.relative_to).parent.joinpath(version_file)
        write_version_to_path(
            target,
            template=config.version_file_template,
            version=version,
            scm_version=scm_version,
        )


def _get_version(
    config: Configuration, force_write_version_files: bool | None = None
) -> str | None:
    parsed_version = parse_version(config)
    if parsed_version is None:
        return None
    version_string = _format_version(parsed_version)
    if force_write_version_files is None:
        force_write_version_files = True
        warnings.warn(
            "force_write_version_files ought to be set,"
            " presuming the legacy True value",
            DeprecationWarning,
        )

    if force_write_version_files:
        write_version_files(config, version=version_string, scm_version=parsed_version)

    return version_string


def _version_missing(config: Configuration) -> NoReturn:
    raise LookupError(
        f"setuptools-scm was unable to detect version for {config.absolute_root}.\n\n"
        "Make sure you're either building from a fully intact git repository "
        "or PyPI tarballs. Most other sources (such as GitHub's tarballs, a "
        "git checkout without the .git folder) don't contain the necessary "
        "metadata and will not work.\n\n"
        "For example, if you're using pip, instead of "
        "https://github.com/user/proj/archive/master.zip "
        "use git+https://github.com/user/proj.git#egg=proj"
    )


def get_version(
    root: _t.PathT = ".",
    version_scheme: _t.VERSION_SCHEME = _config.DEFAULT_VERSION_SCHEME,
    local_scheme: _t.VERSION_SCHEME = _config.DEFAULT_LOCAL_SCHEME,
    write_to: _t.PathT | None = None,
    write_to_template: str | None = None,
    version_file: _t.PathT | None = None,
    version_file_template: str | None = None,
    relative_to: _t.PathT | None = None,
    tag_regex: str | Pattern[str] = _config.DEFAULT_TAG_REGEX,
    parentdir_prefix_version: str | None = None,
    fallback_version: str | None = None,
    fallback_root: _t.PathT = ".",
    parse: Any | None = None,
    git_describe_command: _t.CMD_TYPE | None = None,
    dist_name: str | None = None,
    version_cls: Any | None = None,
    normalize: bool = True,
    search_parent_directories: bool = False,
) -> str:
    """
    If supplied, relative_to should be a file from which root may
    be resolved. Typically called by a script or module that is not
    in the root of the repository to direct setuptools_scm to the
    root of the repository by supplying ``__file__``.
    """

    version_cls = _validate_version_cls(version_cls, normalize)
    del normalize
    tag_regex = parse_tag_regex(tag_regex)
    config = Configuration(**locals())
    maybe_version = _get_version(config, force_write_version_files=True)

    if maybe_version is None:
        _version_missing(config)
    return maybe_version


def parse_tag_regex(tag_regex: str | Pattern[str]) -> Pattern[str]:
    if isinstance(tag_regex, str):
        if tag_regex == "":
            warnings.warn(EMPTY_TAG_REGEX_DEPRECATION)
            return _config.DEFAULT_TAG_REGEX
        else:
            return re.compile(tag_regex)
    else:
        return tag_regex
