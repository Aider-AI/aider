from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ._config import Configuration
from .version import ScmVersion


@dataclass()
class Workdir:
    path: Path

    def run_describe(self, config: Configuration) -> ScmVersion:
        raise NotImplementedError(self.run_describe)
