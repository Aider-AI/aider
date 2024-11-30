from packaging import version

__version__ = "0.65.2.dev"
safe_version = __version__

try:
    from aider.__version__ import __version__
except Exception:
    __version__ = safe_version + ".import"

try:
    if version.parse(__version__) < version.parse(safe_version):
        __version__ = safe_version + ".less"
except Exception:
    __version__ = safe_version + ".parse"

__all__ = [__version__]
