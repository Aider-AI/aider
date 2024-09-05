# Taken from https://github.com/mlflow/mlflow/pull/10119
#
# DO NOT use this function for security purposes (e.g., password hashing).
#
# In Python >= 3.9, insecure hashing algorithms such as MD5 fail in FIPS-compliant
# environments unless `usedforsecurity=False` is explicitly passed.
#
# References:
# - https://github.com/mlflow/mlflow/issues/9905
# - https://github.com/mlflow/mlflow/pull/10119
# - https://docs.python.org/3/library/hashlib.html
# - https://github.com/huggingface/transformers/pull/27038
#
# Usage:
#     ```python
#     # Use
#     from huggingface_hub.utils.insecure_hashlib import sha256
#     # instead of
#     from hashlib import sha256
#
#     # Use
#     from huggingface_hub.utils import insecure_hashlib
#     # instead of
#     import hashlib
#     ```
import functools
import hashlib
import sys


_kwargs = {"usedforsecurity": False} if sys.version_info >= (3, 9) else {}
md5 = functools.partial(hashlib.md5, **_kwargs)
sha1 = functools.partial(hashlib.sha1, **_kwargs)
sha256 = functools.partial(hashlib.sha256, **_kwargs)
