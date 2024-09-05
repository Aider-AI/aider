from __future__ import annotations

import os
import re

from typing import Any

from . import _config
from . import _log
from . import version
from ._integration.toml import load_toml_or_inline_map

log = _log.log.getChild("overrides")

PRETEND_KEY = "SETUPTOOLS_SCM_PRETEND_VERSION"
PRETEND_KEY_NAMED = PRETEND_KEY + "_FOR_{name}"


def read_named_env(
    *, tool: str = "SETUPTOOLS_SCM", name: str, dist_name: str | None
) -> str | None:
    """ """
    if dist_name is not None:
        # Normalize the dist name as per PEP 503.
        normalized_dist_name = re.sub(r"[-_.]+", "-", dist_name)
        env_var_dist_name = normalized_dist_name.replace("-", "_").upper()
        val = os.environ.get(f"{tool}_{name}_FOR_{env_var_dist_name}")
        if val is not None:
            return val
    return os.environ.get(f"{tool}_{name}")


def _read_pretended_version_for(
    config: _config.Configuration,
) -> version.ScmVersion | None:
    """read a a overridden version from the environment

    tries ``SETUPTOOLS_SCM_PRETEND_VERSION``
    and ``SETUPTOOLS_SCM_PRETEND_VERSION_FOR_$UPPERCASE_DIST_NAME``
    """
    log.debug("dist name: %s", config.dist_name)

    pretended = read_named_env(name="PRETEND_VERSION", dist_name=config.dist_name)

    if pretended:
        # we use meta here since the pretended version
        # must adhere to the pep to begin with
        return version.meta(tag=pretended, preformatted=True, config=config)
    else:
        return None


def read_toml_overrides(dist_name: str | None) -> dict[str, Any]:
    data = read_named_env(name="OVERRIDES", dist_name=dist_name)
    return load_toml_or_inline_map(data)
