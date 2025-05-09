from dataclasses import dataclass
from enum import Enum


class SpinnerStyle(Enum):
    DEFAULT = "default"
    KITT = "kitt"


@dataclass
class SpinnerConfig:
    style: SpinnerStyle = SpinnerStyle.DEFAULT
    color: str = "default"  # Color for spinner text, actual application may vary
    width: int = 7  # Width for KITT/ILOVECANDY spinner, default spinner has fixed frame width
