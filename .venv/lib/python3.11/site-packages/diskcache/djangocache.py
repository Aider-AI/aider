"""Django-compatible disk and file backed cache."""

from functools import wraps

from django.core.cache.backends.base import BaseCache

try:
    from django.core.cache.backends.base import DEFAULT_TIMEOUT
except ImportError:  # pragma: no cover
    # For older versions of Django simply use 300 seconds.
    DEFAULT_TIMEOUT = 300

from .core import ENOVAL, args_to_key, full_name
from .fanout import FanoutCache


class DjangoCache(BaseCache):
    """Django-compatible disk and file backed cache."""

    def __init__(self, directory, params):
        """Initialize DjangoCache instance.

        :param str directory: cache directory
        :param dict params: cache parameters

        """
        super().__init__(params)
        shards = params.get('SHARDS', 8)
        timeout = params.get('DATABASE_TIMEOUT', 0.010)
        options = params.get('OPTIONS', {})
        self._cache = FanoutCache(directory, shards, timeout, **options)

    @property
    def directory(self):
        """Cache directory."""
        return self._cache.directory

    def cache(self, name):
        """Return Cache with given `name` in subdirectory.

        :param str name: subdirectory name for Cache
        :return: Cache with given name

        """
        return self._cache.cache(name)

    def deque(self, name, maxlen=None):
        """Return Deque with given `name` in subdirectory.

        :param str name: subdirectory name for Deque
        :param maxlen: max length (default None, no max)
        :return: Deque with given name

        """
        return self._cache.deque(name, maxlen=maxlen)

    def index(self, name):
        """Return Index with given `name` in subdirectory.

        :param str name: subdirectory name for Index
        :return: Index with given name

        """
        return self._cache.index(name)

    def add(
        self,
        key,
        value,
        timeout=DEFAULT_TIMEOUT,
        version=None,
        read=False,
        tag=None,
        retry=True,
    ):
        """Set a value in the cache if the key does not already exist. If
        timeout is given, that timeout will be used for the key; otherwise the
        default cache timeout will be used.

        Return True if the value was stored, False otherwise.

        :param key: key for item
        :param value: value for item
        :param float timeout: seconds until the item expires
            (default 300 seconds)
        :param int version: key version number (default None, cache parameter)
        :param bool read: read value as bytes from file (default False)
        :param str tag: text to associate with key (default None)
        :param bool retry: retry if database timeout occurs (default True)
        :return: True if item was added

        """
        # pylint: disable=arguments-differ
        key = self.make_key(key, version=version)
        timeout = self.get_backend_timeout(timeout=timeout)
        return self._cache.add(key, value, timeout, read, tag, retry)

    def get(
        self,
        key,
        default=None,
        version=None,
        read=False,
        expire_time=False,
        tag=False,
        retry=False,
    ):
        """Fetch a given key from the cache. If the key does not exist, return
        default, which itself defaults to None.

        :param key: key for item
        :param default: return value if key is missing (default None)
        :param int version: key version number (default None, cache parameter)
        :param bool read: if True, return file handle to value
            (default False)
        :param float expire_time: if True, return expire_time in tuple
            (default False)
        :param tag: if True, return tag in tuple (default False)
        :param bool retry: retry if database timeout occurs (default False)
        :return: value for item if key is found else default

        """
        # pylint: disable=arguments-differ
        key = self.make_key(key, version=version)
        return self._cache.get(key, default, read, expire_time, tag, retry)

    def read(self, key, version=None):
        """Return file handle corresponding to `key` from Cache.

        :param key: Python key to retrieve
        :param int version: key version number (default None, cache parameter)
        :return: file open for reading in binary mode
        :raises KeyError: if key is not found

        """
        key = self.make_key(key, version=version)
        return self._cache.read(key)

    def set(
        self,
        key,
        value,
        timeout=DEFAULT_TIMEOUT,
        version=None,
        read=False,
        tag=None,
        retry=True,
    ):
        """Set a value in the cache. If timeout is given, that timeout will be
        used for the key; otherwise the default cache timeout will be used.

        :param key: key for item
        :param value: value for item
        :param float timeout: seconds until the item expires
            (default 300 seconds)
        :param int version: key version number (default None, cache parameter)
        :param bool read: read value as bytes from file (default False)
        :param str tag: text to associate with key (default None)
        :param bool retry: retry if database timeout occurs (default True)
        :return: True if item was set

        """
        # pylint: disable=arguments-differ
        key = self.make_key(key, version=version)
        timeout = self.get_backend_timeout(timeout=timeout)
        return self._cache.set(key, value, timeout, read, tag, retry)

    def touch(self, key, timeout=DEFAULT_TIMEOUT, version=None, retry=True):
        """Touch a key in the cache. If timeout is given, that timeout will be
        used for the key; otherwise the default cache timeout will be used.

        :param key: key for item
        :param float timeout: seconds until the item expires
            (default 300 seconds)
        :param int version: key version number (default None, cache parameter)
        :param bool retry: retry if database timeout occurs (default True)
        :return: True if key was touched

        """
        # pylint: disable=arguments-differ
        key = self.make_key(key, version=version)
        timeout = self.get_backend_timeout(timeout=timeout)
        return self._cache.touch(key, timeout, retry)

    def pop(
        self,
        key,
        default=None,
        version=None,
        expire_time=False,
        tag=False,
        retry=True,
    ):
        """Remove corresponding item for `key` from cache and return value.

        If `key` is missing, return `default`.

        Operation is atomic. Concurrent operations will be serialized.

        :param key: key for item
        :param default: return value if key is missing (default None)
        :param int version: key version number (default None, cache parameter)
        :param float expire_time: if True, return expire_time in tuple
            (default False)
        :param tag: if True, return tag in tuple (default False)
        :param bool retry: retry if database timeout occurs (default True)
        :return: value for item if key is found else default

        """
        key = self.make_key(key, version=version)
        return self._cache.pop(key, default, expire_time, tag, retry)

    def delete(self, key, version=None, retry=True):
        """Delete a key from the cache, failing silently.

        :param key: key for item
        :param int version: key version number (default None, cache parameter)
        :param bool retry: retry if database timeout occurs (default True)
        :return: True if item was deleted

        """
        # pylint: disable=arguments-differ
        key = self.make_key(key, version=version)
        return self._cache.delete(key, retry)

    def incr(self, key, delta=1, version=None, default=None, retry=True):
        """Increment value by delta for item with key.

        If key is missing and default is None then raise KeyError. Else if key
        is missing and default is not None then use default for value.

        Operation is atomic. All concurrent increment operations will be
        counted individually.

        Assumes value may be stored in a SQLite column. Most builds that target
        machines with 64-bit pointer widths will support 64-bit signed
        integers.

        :param key: key for item
        :param int delta: amount to increment (default 1)
        :param int version: key version number (default None, cache parameter)
        :param int default: value if key is missing (default None)
        :param bool retry: retry if database timeout occurs (default True)
        :return: new value for item on success else None
        :raises ValueError: if key is not found and default is None

        """
        # pylint: disable=arguments-differ
        key = self.make_key(key, version=version)
        try:
            return self._cache.incr(key, delta, default, retry)
        except KeyError:
            raise ValueError("Key '%s' not found" % key) from None

    def decr(self, key, delta=1, version=None, default=None, retry=True):
        """Decrement value by delta for item with key.

        If key is missing and default is None then raise KeyError. Else if key
        is missing and default is not None then use default for value.

        Operation is atomic. All concurrent decrement operations will be
        counted individually.

        Unlike Memcached, negative values are supported. Value may be
        decremented below zero.

        Assumes value may be stored in a SQLite column. Most builds that target
        machines with 64-bit pointer widths will support 64-bit signed
        integers.

        :param key: key for item
        :param int delta: amount to decrement (default 1)
        :param int version: key version number (default None, cache parameter)
        :param int default: value if key is missing (default None)
        :param bool retry: retry if database timeout occurs (default True)
        :return: new value for item on success else None
        :raises ValueError: if key is not found and default is None

        """
        # pylint: disable=arguments-differ
        return self.incr(key, -delta, version, default, retry)

    def has_key(self, key, version=None):
        """Returns True if the key is in the cache and has not expired.

        :param key: key for item
        :param int version: key version number (default None, cache parameter)
        :return: True if key is found

        """
        key = self.make_key(key, version=version)
        return key in self._cache

    def expire(self):
        """Remove expired items from cache.

        :return: count of items removed

        """
        return self._cache.expire()

    def stats(self, enable=True, reset=False):
        """Return cache statistics hits and misses.

        :param bool enable: enable collecting statistics (default True)
        :param bool reset: reset hits and misses to 0 (default False)
        :return: (hits, misses)

        """
        return self._cache.stats(enable=enable, reset=reset)

    def create_tag_index(self):
        """Create tag index on cache database.

        Better to initialize cache with `tag_index=True` than use this.

        :raises Timeout: if database timeout occurs

        """
        self._cache.create_tag_index()

    def drop_tag_index(self):
        """Drop tag index on cache database.

        :raises Timeout: if database timeout occurs

        """
        self._cache.drop_tag_index()

    def evict(self, tag):
        """Remove items with matching `tag` from cache.

        :param str tag: tag identifying items
        :return: count of items removed

        """
        return self._cache.evict(tag)

    def cull(self):
        """Cull items from cache until volume is less than size limit.

        :return: count of items removed

        """
        return self._cache.cull()

    def clear(self):
        """Remove *all* values from the cache at once."""
        return self._cache.clear()

    def close(self, **kwargs):
        """Close the cache connection."""
        # pylint: disable=unused-argument
        self._cache.close()

    def get_backend_timeout(self, timeout=DEFAULT_TIMEOUT):
        """Return seconds to expiration.

        :param float timeout: seconds until the item expires
            (default 300 seconds)

        """
        if timeout == DEFAULT_TIMEOUT:
            timeout = self.default_timeout
        elif timeout == 0:
            # ticket 21147 - avoid time.time() related precision issues
            timeout = -1
        return None if timeout is None else timeout

    def memoize(
        self,
        name=None,
        timeout=DEFAULT_TIMEOUT,
        version=None,
        typed=False,
        tag=None,
        ignore=(),
    ):
        """Memoizing cache decorator.

        Decorator to wrap callable with memoizing function using cache.
        Repeated calls with the same arguments will lookup result in cache and
        avoid function evaluation.

        If name is set to None (default), the callable name will be determined
        automatically.

        When timeout is set to zero, function results will not be set in the
        cache. Cache lookups still occur, however. Read
        :doc:`case-study-landing-page-caching` for example usage.

        If typed is set to True, function arguments of different types will be
        cached separately. For example, f(3) and f(3.0) will be treated as
        distinct calls with distinct results.

        The original underlying function is accessible through the __wrapped__
        attribute. This is useful for introspection, for bypassing the cache,
        or for rewrapping the function with a different cache.

        An additional `__cache_key__` attribute can be used to generate the
        cache key used for the given arguments.

        Remember to call memoize when decorating a callable. If you forget,
        then a TypeError will occur.

        :param str name: name given for callable (default None, automatic)
        :param float timeout: seconds until the item expires
            (default 300 seconds)
        :param int version: key version number (default None, cache parameter)
        :param bool typed: cache different types separately (default False)
        :param str tag: text to associate with arguments (default None)
        :param set ignore: positional or keyword args to ignore (default ())
        :return: callable decorator

        """
        # Caution: Nearly identical code exists in Cache.memoize
        if callable(name):
            raise TypeError('name cannot be callable')

        def decorator(func):
            """Decorator created by memoize() for callable `func`."""
            base = (full_name(func),) if name is None else (name,)

            @wraps(func)
            def wrapper(*args, **kwargs):
                """Wrapper for callable to cache arguments and return values."""
                key = wrapper.__cache_key__(*args, **kwargs)
                result = self.get(key, ENOVAL, version, retry=True)

                if result is ENOVAL:
                    result = func(*args, **kwargs)
                    valid_timeout = (
                        timeout is None
                        or timeout == DEFAULT_TIMEOUT
                        or timeout > 0
                    )
                    if valid_timeout:
                        self.set(
                            key,
                            result,
                            timeout,
                            version,
                            tag=tag,
                            retry=True,
                        )

                return result

            def __cache_key__(*args, **kwargs):
                """Make key for cache given function arguments."""
                return args_to_key(base, args, kwargs, typed, ignore)

            wrapper.__cache_key__ = __cache_key__
            return wrapper

        return decorator
