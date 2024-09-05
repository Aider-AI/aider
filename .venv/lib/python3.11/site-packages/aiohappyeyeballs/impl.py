"""Base implementation."""

import asyncio
import collections
import functools
import itertools
import socket
import sys
from asyncio import staggered
from typing import List, Optional, Sequence

from .types import AddrInfoType

if sys.version_info < (3, 8, 2):  # noqa: UP036
    # asyncio.staggered is broken in Python 3.8.0 and 3.8.1
    # so it must be patched:
    # https://github.com/aio-libs/aiohttp/issues/8556
    # https://bugs.python.org/issue39129
    # https://github.com/python/cpython/pull/17693
    import asyncio.futures

    asyncio.futures.TimeoutError = asyncio.TimeoutError  # type: ignore[attr-defined]


async def start_connection(
    addr_infos: Sequence[AddrInfoType],
    *,
    local_addr_infos: Optional[Sequence[AddrInfoType]] = None,
    happy_eyeballs_delay: Optional[float] = None,
    interleave: Optional[int] = None,
    loop: Optional[asyncio.AbstractEventLoop] = None,
) -> socket.socket:
    """
    Connect to a TCP server.

    Create a socket connection to a specified destination.  The
    destination is specified as a list of AddrInfoType tuples as
    returned from getaddrinfo().

    The arguments are, in order:

    * ``family``: the address family, e.g. ``socket.AF_INET`` or
        ``socket.AF_INET6``.
    * ``type``: the socket type, e.g. ``socket.SOCK_STREAM`` or
        ``socket.SOCK_DGRAM``.
    * ``proto``: the protocol, e.g. ``socket.IPPROTO_TCP`` or
        ``socket.IPPROTO_UDP``.
    * ``canonname``: the canonical name of the address, e.g.
        ``"www.python.org"``.
    * ``sockaddr``: the socket address

    This method is a coroutine which will try to establish the connection
    in the background. When successful, the coroutine returns a
    socket.

    The expected use case is to use this method in conjunction with
    loop.create_connection() to establish a connection to a server::

            socket = await start_connection(addr_infos)
            transport, protocol = await loop.create_connection(
                MyProtocol, sock=socket, ...)
    """
    if not (current_loop := loop):
        current_loop = asyncio.get_running_loop()

    single_addr_info = len(addr_infos) == 1

    if happy_eyeballs_delay is not None and interleave is None:
        # If using happy eyeballs, default to interleave addresses by family
        interleave = 1

    if interleave and not single_addr_info:
        addr_infos = _interleave_addrinfos(addr_infos, interleave)

    sock: Optional[socket.socket] = None
    exceptions: List[List[OSError]] = []
    if happy_eyeballs_delay is None or single_addr_info:
        # not using happy eyeballs
        for addrinfo in addr_infos:
            try:
                sock = await _connect_sock(
                    current_loop, exceptions, addrinfo, local_addr_infos
                )
                break
            except OSError:
                continue
    else:  # using happy eyeballs
        sock, _, _ = await staggered.staggered_race(
            (
                functools.partial(
                    _connect_sock, current_loop, exceptions, addrinfo, local_addr_infos
                )
                for addrinfo in addr_infos
            ),
            happy_eyeballs_delay,
            loop=current_loop,
        )

    if sock is None:
        all_exceptions = [exc for sub in exceptions for exc in sub]
        try:
            first_exception = all_exceptions[0]
            if len(all_exceptions) == 1:
                raise first_exception
            else:
                # If they all have the same str(), raise one.
                model = str(first_exception)
                if all(str(exc) == model for exc in all_exceptions):
                    raise first_exception
                # Raise a combined exception so the user can see all
                # the various error messages.
                msg = "Multiple exceptions: {}".format(
                    ", ".join(str(exc) for exc in all_exceptions)
                )
                # If the errno is the same for all exceptions, raise
                # an OSError with that errno.
                first_errno = first_exception.errno
                if all(
                    isinstance(exc, OSError) and exc.errno == first_errno
                    for exc in all_exceptions
                ):
                    raise OSError(first_errno, msg)
                raise OSError(msg)
        finally:
            all_exceptions = None  # type: ignore[assignment]
            exceptions = None  # type: ignore[assignment]

    return sock


async def _connect_sock(
    loop: asyncio.AbstractEventLoop,
    exceptions: List[List[OSError]],
    addr_info: AddrInfoType,
    local_addr_infos: Optional[Sequence[AddrInfoType]] = None,
) -> socket.socket:
    """Create, bind and connect one socket."""
    my_exceptions: list[OSError] = []
    exceptions.append(my_exceptions)
    family, type_, proto, _, address = addr_info
    sock = None
    try:
        sock = socket.socket(family=family, type=type_, proto=proto)
        sock.setblocking(False)
        if local_addr_infos is not None:
            for lfamily, _, _, _, laddr in local_addr_infos:
                # skip local addresses of different family
                if lfamily != family:
                    continue
                try:
                    sock.bind(laddr)
                    break
                except OSError as exc:
                    msg = (
                        f"error while attempting to bind on "
                        f"address {laddr!r}: "
                        f"{exc.strerror.lower()}"
                    )
                    exc = OSError(exc.errno, msg)
                    my_exceptions.append(exc)
            else:  # all bind attempts failed
                if my_exceptions:
                    raise my_exceptions.pop()
                else:
                    raise OSError(f"no matching local address with {family=} found")
        await loop.sock_connect(sock, address)
        return sock
    except OSError as exc:
        my_exceptions.append(exc)
        if sock is not None:
            sock.close()
        raise
    except:
        if sock is not None:
            sock.close()
        raise
    finally:
        exceptions = my_exceptions = None  # type: ignore[assignment]


def _interleave_addrinfos(
    addrinfos: Sequence[AddrInfoType], first_address_family_count: int = 1
) -> List[AddrInfoType]:
    """Interleave list of addrinfo tuples by family."""
    # Group addresses by family
    addrinfos_by_family: collections.OrderedDict[int, List[AddrInfoType]] = (
        collections.OrderedDict()
    )
    for addr in addrinfos:
        family = addr[0]
        if family not in addrinfos_by_family:
            addrinfos_by_family[family] = []
        addrinfos_by_family[family].append(addr)
    addrinfos_lists = list(addrinfos_by_family.values())

    reordered: List[AddrInfoType] = []
    if first_address_family_count > 1:
        reordered.extend(addrinfos_lists[0][: first_address_family_count - 1])
        del addrinfos_lists[0][: first_address_family_count - 1]
    reordered.extend(
        a
        for a in itertools.chain.from_iterable(itertools.zip_longest(*addrinfos_lists))
        if a is not None
    )
    return reordered
