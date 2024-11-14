try:
    from aider.__version__ import __version__
except Exception:
    __version__ = "0.63.1.dev"

from .api import create_app

__all__ = [__version__, 'create_app']
