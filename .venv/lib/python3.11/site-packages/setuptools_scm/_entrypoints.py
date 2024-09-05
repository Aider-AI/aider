from __future__ import annotations

import sys

from typing import TYPE_CHECKING
from typing import Any
from typing import Callable
from typing import Iterator
from typing import cast
from typing import overload

from . import _log
from . import version

if TYPE_CHECKING:
    from . import _types as _t
    from ._config import Configuration
    from ._config import ParseFunction


from importlib.metadata import EntryPoint as EntryPoint

if sys.version_info[:2] < (3, 10):
    from importlib.metadata import entry_points as legacy_entry_points

    class EntryPoints:
        _groupdata: list[EntryPoint]

        def __init__(self, groupdata: list[EntryPoint]) -> None:
            self._groupdata = groupdata

        def select(self, name: str) -> EntryPoints:
            return EntryPoints([x for x in self._groupdata if x.name == name])

        def __iter__(self) -> Iterator[EntryPoint]:
            return iter(self._groupdata)

    def entry_points(group: str) -> EntryPoints:
        return EntryPoints(legacy_entry_points()[group])

else:
    from importlib.metadata import EntryPoints
    from importlib.metadata import entry_points


log = _log.log.getChild("entrypoints")


def version_from_entrypoint(
    config: Configuration, *, entrypoint: str, root: _t.PathT
) -> version.ScmVersion | None:
    from .discover import iter_matching_entrypoints

    log.debug("version_from_ep %s in %s", entrypoint, root)
    for ep in iter_matching_entrypoints(root, entrypoint, config):
        fn: ParseFunction = ep.load()
        maybe_version: version.ScmVersion | None = fn(root, config=config)
        log.debug("%s found %r", ep, maybe_version)
        if maybe_version is not None:
            return maybe_version
    return None


def iter_entry_points(group: str, name: str | None = None) -> Iterator[EntryPoint]:
    eps: EntryPoints = entry_points(group=group)
    res = eps if name is None else eps.select(name=name)

    return iter(res)


def _get_ep(group: str, name: str) -> Any | None:
    for ep in iter_entry_points(group, name):
        log.debug("ep found: %s", ep.name)
        return ep.load()
    else:
        return None


def _get_from_object_reference_str(path: str, group: str) -> Any | None:
    # todo: remove for importlib native spelling
    ep = EntryPoint(path, path, group)
    try:
        return ep.load()
    except (AttributeError, ModuleNotFoundError):
        return None


def _iter_version_schemes(
    entrypoint: str,
    scheme_value: _t.VERSION_SCHEMES,
    _memo: set[object] | None = None,
) -> Iterator[Callable[[version.ScmVersion], str]]:
    if _memo is None:
        _memo = set()
    if isinstance(scheme_value, str):
        scheme_value = cast(
            "_t.VERSION_SCHEMES",
            _get_ep(entrypoint, scheme_value)
            or _get_from_object_reference_str(scheme_value, entrypoint),
        )

    if isinstance(scheme_value, (list, tuple)):
        for variant in scheme_value:
            if variant not in _memo:
                _memo.add(variant)
                yield from _iter_version_schemes(entrypoint, variant, _memo=_memo)
    elif callable(scheme_value):
        yield scheme_value


@overload
def _call_version_scheme(
    version: version.ScmVersion,
    entrypoint: str,
    given_value: _t.VERSION_SCHEMES,
    default: str,
) -> str: ...


@overload
def _call_version_scheme(
    version: version.ScmVersion,
    entrypoint: str,
    given_value: _t.VERSION_SCHEMES,
    default: None,
) -> str | None: ...


def _call_version_scheme(
    version: version.ScmVersion,
    entrypoint: str,
    given_value: _t.VERSION_SCHEMES,
    default: str | None,
) -> str | None:
    for scheme in _iter_version_schemes(entrypoint, given_value):
        result = scheme(version)
        if result is not None:
            return result
    return default
