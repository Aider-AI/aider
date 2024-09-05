"""
Expose zipp.Path as .zipfile.Path
"""

import importlib
import sys
import types

import zipp


zipfile = types.SimpleNamespace(**vars(importlib.import_module('zipfile')))
zipfile.Path = zipp.Path
zipfile._path = zipp

sys.modules[__name__ + '.zipfile'] = zipfile  # type: ignore[assignment]
