from setuptools_scm import get_version

try:
    __version__ = get_version(root="..", relative_to=__file__)
except Exception:
    from aider.__version__ import __version__
