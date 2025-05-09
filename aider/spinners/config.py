from dataclasses import dataclass
from enum import Enum


class SpinnerStyle(Enum):
    DEFAULT = "default"
    KITT = "kitt"
    SNAKE = "snake"
    PUMP = "pump"
    BALL = "ball"


@dataclass
class SpinnerConfig:
    style: SpinnerStyle = SpinnerStyle.DEFAULT
    color: str = "default"  # Color for spinner text, actual application may vary
    width: int = 7  # Width for KITT/BALL spinner, default spinner has fixed frame width
