"""
The _compat module is used for code which requires branching between different
Python environments. It is excluded from the code coverage checks.
"""

import re
import ssl
import sys
from types import ModuleType
from typing import Optional

# Brotli support is optional
# The C bindings in `brotli` are recommended for CPython.
# The CFFI bindings in `brotlicffi` are recommended for PyPy and everything else.
try:
    import brotlicffi as brotli
except ImportError:  # pragma: no cover
    try:
        import brotli
    except ImportError:
        brotli = None

# Zstandard support is optional
zstd: Optional[ModuleType] = None
try:
    import zstandard as zstd
except (AttributeError, ImportError, ValueError):  # Defensive:
    zstd = None
else:
    # The package 'zstandard' added the 'eof' property starting
    # in v0.18.0 which we require to ensure a complete and
    # valid zstd stream was fed into the ZstdDecoder.
    # See: https://github.com/urllib3/urllib3/pull/2624
    _zstd_version = tuple(
        map(int, re.search(r"^([0-9]+)\.([0-9]+)", zstd.__version__).groups())  # type: ignore[union-attr]
    )
    if _zstd_version < (0, 18):  # Defensive:
        zstd = None


if sys.version_info >= (3, 10) or ssl.OPENSSL_VERSION_INFO >= (1, 1, 0, 7):

    def set_minimum_tls_version_1_2(context: ssl.SSLContext) -> None:
        # The OP_NO_SSL* and OP_NO_TLS* become deprecated in favor of
        # 'SSLContext.minimum_version' from Python 3.7 onwards, however
        # this attribute is not available unless the ssl module is compiled
        # with OpenSSL 1.1.0g or newer.
        # https://docs.python.org/3.10/library/ssl.html#ssl.SSLContext.minimum_version
        # https://docs.python.org/3.7/library/ssl.html#ssl.SSLContext.minimum_version
        context.minimum_version = ssl.TLSVersion.TLSv1_2

else:

    def set_minimum_tls_version_1_2(context: ssl.SSLContext) -> None:
        # If 'minimum_version' isn't available, we configure these options with
        # the older deprecated variants.
        context.options |= ssl.OP_NO_SSLv2
        context.options |= ssl.OP_NO_SSLv3
        context.options |= ssl.OP_NO_TLSv1
        context.options |= ssl.OP_NO_TLSv1_1


__all__ = ["brotli", "set_minimum_tls_version_1_2"]
