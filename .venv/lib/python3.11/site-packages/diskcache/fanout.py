"""Fanout cache automatically shards keys and values."""

import contextlib as cl
import functools
import itertools as it
import operator
import os.path as op
import sqlite3
import tempfile
import time

from .core import DEFAULT_SETTINGS, ENOVAL, Cache, Disk, Timeout
from .persistent import Deque, Index


class FanoutCache:
    """Cache that shards keys and values."""

    def __init__(
        self, directory=None, shards=8, timeout=0.010, disk=Disk, **settings
    ):
        """Initialize cache instance.

        :param str directory: cache directory
        :param int shards: number of shards to distribute writes
        :param float timeout: SQLite connection timeout
        :param disk: `Disk` instance for serialization
        :param settings: any of `DEFAULT_SETTINGS`

        """
        if directory is None:
            directory = tempfile.mkdtemp(prefix='diskcache-')
        directory = str(directory)
        directory = op.expanduser(directory)
        directory = op.expandvars(directory)

        default_size_limit = DEFAULT_SETTINGS['size_limit']
        size_limit = settings.pop('size_limit', default_size_limit) / shards

        self._count = shards
        self._directory = directory
        self._disk = disk
        self._shards = tuple(
            Cache(
                directory=op.join(directory, '%03d' % num),
                timeout=timeout,
                disk=disk,
                size_limit=size_limit,
                **settings,
            )
            for num in range(shards)
        )
        self._hash = self._shards[0].disk.hash
        self._caches = {}
        self._deques = {}
        self._indexes = {}

    @property
    def directory(self):
        """Cache directory."""
        return self._directory

    def __getattr__(self, name):
        safe_names = {'timeout', 'disk'}
        valid_name = name in DEFAULT_SETTINGS or name in safe_names
        assert valid_name, 'cannot access {} in cache shard'.format(name)
        return getattr(self._shards[0], name)

    @cl.contextmanager
    def transact(self, retry=True):
        """Context manager to perform a transaction by locking the cache.

        While the cache is locked, no other write operation is permitted.
        Transactions should therefore be as short as possible. Read and write
        operations performed in a transaction are atomic. Read operations may
        occur concurrent to a transaction.

        Transactions may be nested and may not be shared between threads.

        Blocks until transactions are held on all cache shards by retrying as
        necessary.

        >>> cache = FanoutCache()
        >>> with cache.transact():  # Atomically increment two keys.
        ...     _ = cache.incr('total', 123.4)
        ...     _ = cache.incr('count', 1)
        >>> with cache.transact():  # Atomically calculate average.
        ...     average = cache['total'] / cache['count']
        >>> average
        123.4

        :return: context manager for use in `with` statement

        """
        assert retry, 'retry must be True in FanoutCache'
        with cl.ExitStack() as stack:
            for shard in self._shards:
                shard_transaction = shard.transact(retry=True)
                stack.enter_context(shard_transaction)
            yield

    def set(self, key, value, expire=None, read=False, tag=None, retry=False):
        """Set `key` and `value` item in cache.

        When `read` is `True`, `value` should be a file-like object opened
        for reading in binary mode.

        If database timeout occurs then fails silently unless `retry` is set to
        `True` (default `False`).

        :param key: key for item
        :param value: value for item
        :param float expire: seconds until the key expires
            (default None, no expiry)
        :param bool read: read value as raw bytes from file (default False)
        :param str tag: text to associate with key (default None)
        :param bool retry: retry if database timeout occurs (default False)
        :return: True if item was set

        """
        index = self._hash(key) % self._count
        shard = self._shards[index]
        try:
            return shard.set(key, value, expire, read, tag, retry)
        except Timeout:
            return False

    def __setitem__(self, key, value):
        """Set `key` and `value` item in cache.

        Calls :func:`FanoutCache.set` internally with `retry` set to `True`.

        :param key: key for item
        :param value: value for item

        """
        index = self._hash(key) % self._count
        shard = self._shards[index]
        shard[key] = value

    def touch(self, key, expire=None, retry=False):
        """Touch `key` in cache and update `expire` time.

        If database timeout occurs then fails silently unless `retry` is set to
        `True` (default `False`).

        :param key: key for item
        :param float expire: seconds until the key expires
            (default None, no expiry)
        :param bool retry: retry if database timeout occurs (default False)
        :return: True if key was touched

        """
        index = self._hash(key) % self._count
        shard = self._shards[index]
        try:
            return shard.touch(key, expire, retry)
        except Timeout:
            return False

    def add(self, key, value, expire=None, read=False, tag=None, retry=False):
        """Add `key` and `value` item to cache.

        Similar to `set`, but only add to cache if key not present.

        This operation is atomic. Only one concurrent add operation for given
        key from separate threads or processes will succeed.

        When `read` is `True`, `value` should be a file-like object opened
        for reading in binary mode.

        If database timeout occurs then fails silently unless `retry` is set to
        `True` (default `False`).

        :param key: key for item
        :param value: value for item
        :param float expire: seconds until the key expires
            (default None, no expiry)
        :param bool read: read value as bytes from file (default False)
        :param str tag: text to associate with key (default None)
        :param bool retry: retry if database timeout occurs (default False)
        :return: True if item was added

        """
        index = self._hash(key) % self._count
        shard = self._shards[index]
        try:
            return shard.add(key, value, expire, read, tag, retry)
        except Timeout:
            return False

    def incr(self, key, delta=1, default=0, retry=False):
        """Increment value by delta for item with key.

        If key is missing and default is None then raise KeyError. Else if key
        is missing and default is not None then use default for value.

        Operation is atomic. All concurrent increment operations will be
        counted individually.

        Assumes value may be stored in a SQLite column. Most builds that target
        machines with 64-bit pointer widths will support 64-bit signed
        integers.

        If database timeout occurs then fails silently unless `retry` is set to
        `True` (default `False`).

        :param key: key for item
        :param int delta: amount to increment (default 1)
        :param int default: value if key is missing (default 0)
        :param bool retry: retry if database timeout occurs (default False)
        :return: new value for item on success else None
        :raises KeyError: if key is not found and default is None

        """
        index = self._hash(key) % self._count
        shard = self._shards[index]
        try:
            return shard.incr(key, delta, default, retry)
        except Timeout:
            return None

    def decr(self, key, delta=1, default=0, retry=False):
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

        If database timeout occurs then fails silently unless `retry` is set to
        `True` (default `False`).

        :param key: key for item
        :param int delta: amount to decrement (default 1)
        :param int default: value if key is missing (default 0)
        :param bool retry: retry if database timeout occurs (default False)
        :return: new value for item on success else None
        :raises KeyError: if key is not found and default is None

        """
        index = self._hash(key) % self._count
        shard = self._shards[index]
        try:
            return shard.decr(key, delta, default, retry)
        except Timeout:
            return None

    def get(
        self,
        key,
        default=None,
        read=False,
        expire_time=False,
        tag=False,
        retry=False,
    ):
        """Retrieve value from cache. If `key` is missing, return `default`.

        If database timeout occurs then returns `default` unless `retry` is set
        to `True` (default `False`).

        :param key: key for item
        :param default: return value if key is missing (default None)
        :param bool read: if True, return file handle to value
            (default False)
        :param float expire_time: if True, return expire_time in tuple
            (default False)
        :param tag: if True, return tag in tuple (default False)
        :param bool retry: retry if database timeout occurs (default False)
        :return: value for item if key is found else default

        """
        index = self._hash(key) % self._count
        shard = self._shards[index]
        try:
            return shard.get(key, default, read, expire_time, tag, retry)
        except (Timeout, sqlite3.OperationalError):
            return default

    def __getitem__(self, key):
        """Return corresponding value for `key` from cache.

        Calls :func:`FanoutCache.get` internally with `retry` set to `True`.

        :param key: key for item
        :return: value for item
        :raises KeyError: if key is not found

        """
        index = self._hash(key) % self._count
        shard = self._shards[index]
        return shard[key]

    def read(self, key):
        """Return file handle corresponding to `key` from cache.

        :param key: key for item
        :return: file open for reading in binary mode
        :raises KeyError: if key is not found

        """
        handle = self.get(key, default=ENOVAL, read=True, retry=True)
        if handle is ENOVAL:
            raise KeyError(key)
        return handle

    def __contains__(self, key):
        """Return `True` if `key` matching item is found in cache.

        :param key: key for item
        :return: True if key is found

        """
        index = self._hash(key) % self._count
        shard = self._shards[index]
        return key in shard

    def pop(
        self, key, default=None, expire_time=False, tag=False, retry=False
    ):  # noqa: E501
        """Remove corresponding item for `key` from cache and return value.

        If `key` is missing, return `default`.

        Operation is atomic. Concurrent operations will be serialized.

        If database timeout occurs then fails silently unless `retry` is set to
        `True` (default `False`).

        :param key: key for item
        :param default: return value if key is missing (default None)
        :param float expire_time: if True, return expire_time in tuple
            (default False)
        :param tag: if True, return tag in tuple (default False)
        :param bool retry: retry if database timeout occurs (default False)
        :return: value for item if key is found else default

        """
        index = self._hash(key) % self._count
        shard = self._shards[index]
        try:
            return shard.pop(key, default, expire_time, tag, retry)
        except Timeout:
            return default

    def delete(self, key, retry=False):
        """Delete corresponding item for `key` from cache.

        Missing keys are ignored.

        If database timeout occurs then fails silently unless `retry` is set to
        `True` (default `False`).

        :param key: key for item
        :param bool retry: retry if database timeout occurs (default False)
        :return: True if item was deleted

        """
        index = self._hash(key) % self._count
        shard = self._shards[index]
        try:
            return shard.delete(key, retry)
        except Timeout:
            return False

    def __delitem__(self, key):
        """Delete corresponding item for `key` from cache.

        Calls :func:`FanoutCache.delete` internally with `retry` set to `True`.

        :param key: key for item
        :raises KeyError: if key is not found

        """
        index = self._hash(key) % self._count
        shard = self._shards[index]
        del shard[key]

    def check(self, fix=False, retry=False):
        """Check database and file system consistency.

        Intended for use in testing and post-mortem error analysis.

        While checking the cache table for consistency, a writer lock is held
        on the database. The lock blocks other cache clients from writing to
        the database. For caches with many file references, the lock may be
        held for a long time. For example, local benchmarking shows that a
        cache with 1,000 file references takes ~60ms to check.

        If database timeout occurs then fails silently unless `retry` is set to
        `True` (default `False`).

        :param bool fix: correct inconsistencies
        :param bool retry: retry if database timeout occurs (default False)
        :return: list of warnings
        :raises Timeout: if database timeout occurs

        """
        warnings = (shard.check(fix, retry) for shard in self._shards)
        return functools.reduce(operator.iadd, warnings, [])

    def expire(self, retry=False):
        """Remove expired items from cache.

        If database timeout occurs then fails silently unless `retry` is set to
        `True` (default `False`).

        :param bool retry: retry if database timeout occurs (default False)
        :return: count of items removed

        """
        return self._remove('expire', args=(time.time(),), retry=retry)

    def create_tag_index(self):
        """Create tag index on cache database.

        Better to initialize cache with `tag_index=True` than use this.

        :raises Timeout: if database timeout occurs

        """
        for shard in self._shards:
            shard.create_tag_index()

    def drop_tag_index(self):
        """Drop tag index on cache database.

        :raises Timeout: if database timeout occurs

        """
        for shard in self._shards:
            shard.drop_tag_index()

    def evict(self, tag, retry=False):
        """Remove items with matching `tag` from cache.

        If database timeout occurs then fails silently unless `retry` is set to
        `True` (default `False`).

        :param str tag: tag identifying items
        :param bool retry: retry if database timeout occurs (default False)
        :return: count of items removed

        """
        return self._remove('evict', args=(tag,), retry=retry)

    def cull(self, retry=False):
        """Cull items from cache until volume is less than size limit.

        If database timeout occurs then fails silently unless `retry` is set to
        `True` (default `False`).

        :param bool retry: retry if database timeout occurs (default False)
        :return: count of items removed

        """
        return self._remove('cull', retry=retry)

    def clear(self, retry=False):
        """Remove all items from cache.

        If database timeout occurs then fails silently unless `retry` is set to
        `True` (default `False`).

        :param bool retry: retry if database timeout occurs (default False)
        :return: count of items removed

        """
        return self._remove('clear', retry=retry)

    def _remove(self, name, args=(), retry=False):
        total = 0
        for shard in self._shards:
            method = getattr(shard, name)
            while True:
                try:
                    count = method(*args, retry=retry)
                    total += count
                except Timeout as timeout:
                    total += timeout.args[0]
                else:
                    break
        return total

    def stats(self, enable=True, reset=False):
        """Return cache statistics hits and misses.

        :param bool enable: enable collecting statistics (default True)
        :param bool reset: reset hits and misses to 0 (default False)
        :return: (hits, misses)

        """
        results = [shard.stats(enable, reset) for shard in self._shards]
        total_hits = sum(hits for hits, _ in results)
        total_misses = sum(misses for _, misses in results)
        return total_hits, total_misses

    def volume(self):
        """Return estimated total size of cache on disk.

        :return: size in bytes

        """
        return sum(shard.volume() for shard in self._shards)

    def close(self):
        """Close database connection."""
        for shard in self._shards:
            shard.close()
        self._caches.clear()
        self._deques.clear()
        self._indexes.clear()

    def __enter__(self):
        return self

    def __exit__(self, *exception):
        self.close()

    def __getstate__(self):
        return (self._directory, self._count, self.timeout, type(self.disk))

    def __setstate__(self, state):
        self.__init__(*state)

    def __iter__(self):
        """Iterate keys in cache including expired items."""
        iterators = (iter(shard) for shard in self._shards)
        return it.chain.from_iterable(iterators)

    def __reversed__(self):
        """Reverse iterate keys in cache including expired items."""
        iterators = (reversed(shard) for shard in reversed(self._shards))
        return it.chain.from_iterable(iterators)

    def __len__(self):
        """Count of items in cache including expired items."""
        return sum(len(shard) for shard in self._shards)

    def reset(self, key, value=ENOVAL):
        """Reset `key` and `value` item from Settings table.

        If `value` is not given, it is reloaded from the Settings
        table. Otherwise, the Settings table is updated.

        Settings attributes on cache objects are lazy-loaded and
        read-only. Use `reset` to update the value.

        Settings with the ``sqlite_`` prefix correspond to SQLite
        pragmas. Updating the value will execute the corresponding PRAGMA
        statement.

        :param str key: Settings key for item
        :param value: value for item (optional)
        :return: updated value for item

        """
        for shard in self._shards:
            while True:
                try:
                    result = shard.reset(key, value)
                except Timeout:
                    pass
                else:
                    break
        return result

    def cache(self, name, timeout=60, disk=None, **settings):
        """Return Cache with given `name` in subdirectory.

        If disk is none (default), uses the fanout cache disk.

        >>> fanout_cache = FanoutCache()
        >>> cache = fanout_cache.cache('test')
        >>> cache.set('abc', 123)
        True
        >>> cache.get('abc')
        123
        >>> len(cache)
        1
        >>> cache.delete('abc')
        True

        :param str name: subdirectory name for Cache
        :param float timeout: SQLite connection timeout
        :param disk: Disk type or subclass for serialization
        :param settings: any of DEFAULT_SETTINGS
        :return: Cache with given name

        """
        _caches = self._caches

        try:
            return _caches[name]
        except KeyError:
            parts = name.split('/')
            directory = op.join(self._directory, 'cache', *parts)
            temp = Cache(
                directory=directory,
                timeout=timeout,
                disk=self._disk if disk is None else Disk,
                **settings,
            )
            _caches[name] = temp
            return temp

    def deque(self, name, maxlen=None):
        """Return Deque with given `name` in subdirectory.

        >>> cache = FanoutCache()
        >>> deque = cache.deque('test')
        >>> deque.extend('abc')
        >>> deque.popleft()
        'a'
        >>> deque.pop()
        'c'
        >>> len(deque)
        1

        :param str name: subdirectory name for Deque
        :param maxlen: max length (default None, no max)
        :return: Deque with given name

        """
        _deques = self._deques

        try:
            return _deques[name]
        except KeyError:
            parts = name.split('/')
            directory = op.join(self._directory, 'deque', *parts)
            cache = Cache(
                directory=directory,
                disk=self._disk,
                eviction_policy='none',
            )
            deque = Deque.fromcache(cache, maxlen=maxlen)
            _deques[name] = deque
            return deque

    def index(self, name):
        """Return Index with given `name` in subdirectory.

        >>> cache = FanoutCache()
        >>> index = cache.index('test')
        >>> index['abc'] = 123
        >>> index['def'] = 456
        >>> index['ghi'] = 789
        >>> index.popitem()
        ('ghi', 789)
        >>> del index['abc']
        >>> len(index)
        1
        >>> index['def']
        456

        :param str name: subdirectory name for Index
        :return: Index with given name

        """
        _indexes = self._indexes

        try:
            return _indexes[name]
        except KeyError:
            parts = name.split('/')
            directory = op.join(self._directory, 'index', *parts)
            cache = Cache(
                directory=directory,
                disk=self._disk,
                eviction_policy='none',
            )
            index = Index.fromcache(cache)
            _indexes[name] = index
            return index


FanoutCache.memoize = Cache.memoize  # type: ignore
