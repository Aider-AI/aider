from __future__ import annotations

import warnings

from pathlib import Path
from typing import NamedTuple

from .. import _log
from .setuptools import read_dist_name_from_setup_cfg
from .toml import TOML_RESULT
from .toml import read_toml_content

log = _log.log.getChild("pyproject_reading")

_ROOT = "root"


class PyProjectData(NamedTuple):
    path: Path
    tool_name: str
    project: TOML_RESULT
    section: TOML_RESULT

    @property
    def project_name(self) -> str | None:
        return self.project.get("name")


def read_pyproject(
    path: Path = Path("pyproject.toml"),
    tool_name: str = "setuptools_scm",
    require_section: bool = True,
) -> PyProjectData:
    defn = read_toml_content(path, None if require_section else {})
    try:
        section = defn.get("tool", {})[tool_name]
    except LookupError as e:
        error = f"{path} does not contain a tool.{tool_name} section"
        if require_section:
            raise LookupError(error) from e
        else:
            log.warning("toml section missing %r", error, exc_info=True)
            section = {}

    project = defn.get("project", {})
    return PyProjectData(path, tool_name, project, section)


def get_args_for_pyproject(
    pyproject: PyProjectData,
    dist_name: str | None,
    kwargs: TOML_RESULT,
) -> TOML_RESULT:
    """drops problematic details and figures the distribution name"""
    section = pyproject.section.copy()
    kwargs = kwargs.copy()
    if "relative_to" in section:
        relative = section.pop("relative_to")
        warnings.warn(
            f"{pyproject.path}: at [tool.{pyproject.tool_name}]\n"
            f"ignoring value relative_to={relative!r}"
            " as its always relative to the config file"
        )
    if "dist_name" in section:
        if dist_name is None:
            dist_name = section.pop("dist_name")
        else:
            assert dist_name == section["dist_name"]
            section.pop("dist_name")
    if dist_name is None:
        # minimal pep 621 support for figuring the pretend keys
        dist_name = pyproject.project_name
    if dist_name is None:
        dist_name = read_dist_name_from_setup_cfg()
    if _ROOT in kwargs:
        if kwargs[_ROOT] is None:
            kwargs.pop(_ROOT, None)
        elif _ROOT in section:
            if section[_ROOT] != kwargs[_ROOT]:
                warnings.warn(
                    f"root {section[_ROOT]} is overridden"
                    f" by the cli arg {kwargs[_ROOT]}"
                )
            section.pop(_ROOT, None)
    return {"dist_name": dist_name, **section, **kwargs}
