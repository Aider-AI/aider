from __future__ import annotations

import logging
import os
import warnings

from typing import Any
from typing import Callable

import setuptools

from .. import _config

log = logging.getLogger(__name__)


def read_dist_name_from_setup_cfg(
    input: str | os.PathLike[str] = "setup.cfg",
) -> str | None:
    # minimal effort to read dist_name off setup.cfg metadata
    import configparser

    parser = configparser.ConfigParser()
    parser.read([input], encoding="utf-8")
    dist_name = parser.get("metadata", "name", fallback=None)
    return dist_name


def _warn_on_old_setuptools(_version: str = setuptools.__version__) -> None:
    if int(_version.split(".")[0]) < 61:
        warnings.warn(
            RuntimeWarning(
                f"""
ERROR: setuptools=={_version} is used in combination with setuptools_scm>=8.x

Your build configuration is incomplete and previously worked by accident!
setuptools_scm requires setuptools>=61

Suggested workaround if applicable:
 - migrating from the deprecated setup_requires mechanism to pep517/518
   and using a pyproject.toml to declare build dependencies
   which are reliably pre-installed before running the build tools
"""
            )
        )


def _assign_version(
    dist: setuptools.Distribution, config: _config.Configuration
) -> None:
    from .._get_version_impl import _get_version
    from .._get_version_impl import _version_missing

    # todo: build time plugin
    maybe_version = _get_version(config, force_write_version_files=True)

    if maybe_version is None:
        _version_missing(config)
    else:
        assert dist.metadata.version is None
        dist.metadata.version = maybe_version


_warn_on_old_setuptools()


def _log_hookstart(hook: str, dist: setuptools.Distribution) -> None:
    log.debug("%s %r", hook, vars(dist.metadata))


def version_keyword(
    dist: setuptools.Distribution,
    keyword: str,
    value: bool | dict[str, Any] | Callable[[], dict[str, Any]],
) -> None:
    overrides: dict[str, Any]
    if value is True:
        overrides = {}
    elif callable(value):
        overrides = value()
    else:
        assert isinstance(value, dict), "version_keyword expects a dict or True"
        overrides = value

    assert (
        "dist_name" not in overrides
    ), "dist_name may not be specified in the setup keyword "
    dist_name: str | None = dist.metadata.name
    _log_hookstart("version_keyword", dist)

    if dist.metadata.version is not None:
        warnings.warn(f"version of {dist_name} already set")
        return

    if dist_name is None:
        dist_name = read_dist_name_from_setup_cfg()

    config = _config.Configuration.from_file(
        dist_name=dist_name,
        _require_section=False,
        **overrides,
    )
    _assign_version(dist, config)


def infer_version(dist: setuptools.Distribution) -> None:
    _log_hookstart("infer_version", dist)
    log.debug("dist %s %s", id(dist), id(dist.metadata))
    if dist.metadata.version is not None:
        return  # metadata already added by hook
    dist_name = dist.metadata.name
    if dist_name is None:
        dist_name = read_dist_name_from_setup_cfg()
    if not os.path.isfile("pyproject.toml"):
        return
    if dist_name == "setuptools_scm":
        return
    try:
        config = _config.Configuration.from_file(dist_name=dist_name)
    except LookupError as e:
        log.info(e, exc_info=True)
    else:
        _assign_version(dist, config)
