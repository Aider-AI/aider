"""Types for aiohappyeyeballs."""

import socket
from typing import Tuple, Union

AddrInfoType = Tuple[
    Union[int, socket.AddressFamily],
    Union[int, socket.SocketKind],
    int,
    str,
    Tuple,  # type: ignore[type-arg]
]
