from __future__ import annotations

import os

from typing import TYPE_CHECKING
from typing import Callable
from typing import List
from typing import Sequence
from typing import Tuple
from typing import Union

if TYPE_CHECKING:
    import sys

    if sys.version_info >= (3, 10):
        from typing import TypeAlias
    else:
        from typing_extensions import TypeAlias

    from . import version

PathT: TypeAlias = Union["os.PathLike[str]", str]

CMD_TYPE: TypeAlias = Union[Sequence[PathT], str]

VERSION_SCHEME: TypeAlias = Union[str, Callable[["version.ScmVersion"], str]]
VERSION_SCHEMES: TypeAlias = Union[List[str], Tuple[str, ...], VERSION_SCHEME]
SCMVERSION: TypeAlias = "version.ScmVersion"
