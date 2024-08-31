from setuptools_scm import get_version

try:
    __version__ = get_version(root="..", relative_to=__file__)
except Exception:
    try:
        from aider.__version__ import __version__
    except Exception:
        __version__ = "0.0.0"

__all__ = [__version__]
