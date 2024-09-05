"""Disk Cache Recipes
"""

import functools
import math
import os
import random
import threading
import time

from .core import ENOVAL, args_to_key, full_name


class Averager:
    """Recipe for calculating a running average.

    Sometimes known as "online statistics," the running average maintains the
    total and count. The average can then be calculated at any time.

    Assumes the key will not be evicted. Set the eviction policy to 'none' on
    the cache to guarantee the key is not evicted.

    >>> import diskcache
    >>> cache = diskcache.FanoutCache()
    >>> ave = Averager(cache, 'latency')
    >>> ave.add(0.080)
    >>> ave.add(0.120)
    >>> ave.get()
    0.1
    >>> ave.add(0.160)
    >>> ave.pop()
    0.12
    >>> print(ave.get())
    None

    """

    def __init__(self, cache, key, expire=None, tag=None):
        self._cache = cache
        self._key = key
        self._expire = expire
        self._tag = tag

    def add(self, value):
        """Add `value` to average."""
        with self._cache.transact(retry=True):
            total, count = self._cache.get(self._key, default=(0.0, 0))
            total += value
            count += 1
            self._cache.set(
                self._key,
                (total, count),
                expire=self._expire,
                tag=self._tag,
            )

    def get(self):
        """Get current average or return `None` if count equals zero."""
        total, count = self._cache.get(self._key, default=(0.0, 0), retry=True)
        return None if count == 0 else total / count

    def pop(self):
        """Return current average and delete key."""
        total, count = self._cache.pop(self._key, default=(0.0, 0), retry=True)
        return None if count == 0 else total / count


class Lock:
    """Recipe for cross-process and cross-thread lock.

    Assumes the key will not be evicted. Set the eviction policy to 'none' on
    the cache to guarantee the key is not evicted.

    >>> import diskcache
    >>> cache = diskcache.Cache()
    >>> lock = Lock(cache, 'report-123')
    >>> lock.acquire()
    >>> lock.release()
    >>> with lock:
    ...     pass

    """

    def __init__(self, cache, key, expire=None, tag=None):
        self._cache = cache
        self._key = key
        self._expire = expire
        self._tag = tag

    def acquire(self):
        """Acquire lock using spin-lock algorithm."""
        while True:
            added = self._cache.add(
                self._key,
                None,
                expire=self._expire,
                tag=self._tag,
                retry=True,
            )
            if added:
                break
            time.sleep(0.001)

    def release(self):
        """Release lock by deleting key."""
        self._cache.delete(self._key, retry=True)

    def locked(self):
        """Return true if the lock is acquired."""
        return self._key in self._cache

    def __enter__(self):
        self.acquire()

    def __exit__(self, *exc_info):
        self.release()


class RLock:
    """Recipe for cross-process and cross-thread re-entrant lock.

    Assumes the key will not be evicted. Set the eviction policy to 'none' on
    the cache to guarantee the key is not evicted.

    >>> import diskcache
    >>> cache = diskcache.Cache()
    >>> rlock = RLock(cache, 'user-123')
    >>> rlock.acquire()
    >>> rlock.acquire()
    >>> rlock.release()
    >>> with rlock:
    ...     pass
    >>> rlock.release()
    >>> rlock.release()
    Traceback (most recent call last):
      ...
    AssertionError: cannot release un-acquired lock

    """

    def __init__(self, cache, key, expire=None, tag=None):
        self._cache = cache
        self._key = key
        self._expire = expire
        self._tag = tag

    def acquire(self):
        """Acquire lock by incrementing count using spin-lock algorithm."""
        pid = os.getpid()
        tid = threading.get_ident()
        pid_tid = '{}-{}'.format(pid, tid)

        while True:
            with self._cache.transact(retry=True):
                value, count = self._cache.get(self._key, default=(None, 0))
                if pid_tid == value or count == 0:
                    self._cache.set(
                        self._key,
                        (pid_tid, count + 1),
                        expire=self._expire,
                        tag=self._tag,
                    )
                    return
            time.sleep(0.001)

    def release(self):
        """Release lock by decrementing count."""
        pid = os.getpid()
        tid = threading.get_ident()
        pid_tid = '{}-{}'.format(pid, tid)

        with self._cache.transact(retry=True):
            value, count = self._cache.get(self._key, default=(None, 0))
            is_owned = pid_tid == value and count > 0
            assert is_owned, 'cannot release un-acquired lock'
            self._cache.set(
                self._key,
                (value, count - 1),
                expire=self._expire,
                tag=self._tag,
            )

    def __enter__(self):
        self.acquire()

    def __exit__(self, *exc_info):
        self.release()


class BoundedSemaphore:
    """Recipe for cross-process and cross-thread bounded semaphore.

    Assumes the key will not be evicted. Set the eviction policy to 'none' on
    the cache to guarantee the key is not evicted.

    >>> import diskcache
    >>> cache = diskcache.Cache()
    >>> semaphore = BoundedSemaphore(cache, 'max-cons', value=2)
    >>> semaphore.acquire()
    >>> semaphore.acquire()
    >>> semaphore.release()
    >>> with semaphore:
    ...     pass
    >>> semaphore.release()
    >>> semaphore.release()
    Traceback (most recent call last):
      ...
    AssertionError: cannot release un-acquired semaphore

    """

    def __init__(self, cache, key, value=1, expire=None, tag=None):
        self._cache = cache
        self._key = key
        self._value = value
        self._expire = expire
        self._tag = tag

    def acquire(self):
        """Acquire semaphore by decrementing value using spin-lock algorithm."""
        while True:
            with self._cache.transact(retry=True):
                value = self._cache.get(self._key, default=self._value)
                if value > 0:
                    self._cache.set(
                        self._key,
                        value - 1,
                        expire=self._expire,
                        tag=self._tag,
                    )
                    return
            time.sleep(0.001)

    def release(self):
        """Release semaphore by incrementing value."""
        with self._cache.transact(retry=True):
            value = self._cache.get(self._key, default=self._value)
            assert self._value > value, 'cannot release un-acquired semaphore'
            value += 1
            self._cache.set(
                self._key,
                value,
                expire=self._expire,
                tag=self._tag,
            )

    def __enter__(self):
        self.acquire()

    def __exit__(self, *exc_info):
        self.release()


def throttle(
    cache,
    count,
    seconds,
    name=None,
    expire=None,
    tag=None,
    time_func=time.time,
    sleep_func=time.sleep,
):
    """Decorator to throttle calls to function.

    Assumes keys will not be evicted. Set the eviction policy to 'none' on the
    cache to guarantee the keys are not evicted.

    >>> import diskcache, time
    >>> cache = diskcache.Cache()
    >>> count = 0
    >>> @throttle(cache, 2, 1)  # 2 calls per 1 second
    ... def increment():
    ...     global count
    ...     count += 1
    >>> start = time.time()
    >>> while (time.time() - start) <= 2:
    ...     increment()
    >>> count in (6, 7)  # 6 or 7 calls depending on CPU load
    True

    """

    def decorator(func):
        rate = count / float(seconds)
        key = full_name(func) if name is None else name
        now = time_func()
        cache.set(key, (now, count), expire=expire, tag=tag, retry=True)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            while True:
                with cache.transact(retry=True):
                    last, tally = cache.get(key)
                    now = time_func()
                    tally += (now - last) * rate
                    delay = 0

                    if tally > count:
                        cache.set(key, (now, count - 1), expire)
                    elif tally >= 1:
                        cache.set(key, (now, tally - 1), expire)
                    else:
                        delay = (1 - tally) / rate

                if delay:
                    sleep_func(delay)
                else:
                    break

            return func(*args, **kwargs)

        return wrapper

    return decorator


def barrier(cache, lock_factory, name=None, expire=None, tag=None):
    """Barrier to calling decorated function.

    Supports different kinds of locks: Lock, RLock, BoundedSemaphore.

    Assumes keys will not be evicted. Set the eviction policy to 'none' on the
    cache to guarantee the keys are not evicted.

    >>> import diskcache, time
    >>> cache = diskcache.Cache()
    >>> @barrier(cache, Lock)
    ... def work(num):
    ...     print('worker started')
    ...     time.sleep(1)
    ...     print('worker finished')
    >>> import multiprocessing.pool
    >>> pool = multiprocessing.pool.ThreadPool(2)
    >>> _ = pool.map(work, range(2))
    worker started
    worker finished
    worker started
    worker finished
    >>> pool.terminate()

    """

    def decorator(func):
        key = full_name(func) if name is None else name
        lock = lock_factory(cache, key, expire=expire, tag=tag)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with lock:
                return func(*args, **kwargs)

        return wrapper

    return decorator


def memoize_stampede(
    cache, expire, name=None, typed=False, tag=None, beta=1, ignore=()
):
    """Memoizing cache decorator with cache stampede protection.

    Cache stampedes are a type of system overload that can occur when parallel
    computing systems using memoization come under heavy load. This behaviour
    is sometimes also called dog-piling, cache miss storm, cache choking, or
    the thundering herd problem.

    The memoization decorator implements cache stampede protection through
    early recomputation. Early recomputation of function results will occur
    probabilistically before expiration in a background thread of
    execution. Early probabilistic recomputation is based on research by
    Vattani, A.; Chierichetti, F.; Lowenstein, K. (2015), Optimal Probabilistic
    Cache Stampede Prevention, VLDB, pp. 886-897, ISSN 2150-8097

    If name is set to None (default), the callable name will be determined
    automatically.

    If typed is set to True, function arguments of different types will be
    cached separately. For example, f(3) and f(3.0) will be treated as distinct
    calls with distinct results.

    The original underlying function is accessible through the `__wrapped__`
    attribute. This is useful for introspection, for bypassing the cache, or
    for rewrapping the function with a different cache.

    >>> from diskcache import Cache
    >>> cache = Cache()
    >>> @memoize_stampede(cache, expire=1)
    ... def fib(number):
    ...     if number == 0:
    ...         return 0
    ...     elif number == 1:
    ...         return 1
    ...     else:
    ...         return fib(number - 1) + fib(number - 2)
    >>> print(fib(100))
    354224848179261915075

    An additional `__cache_key__` attribute can be used to generate the cache
    key used for the given arguments.

    >>> key = fib.__cache_key__(100)
    >>> del cache[key]

    Remember to call memoize when decorating a callable. If you forget, then a
    TypeError will occur.

    :param cache: cache to store callable arguments and return values
    :param float expire: seconds until arguments expire
    :param str name: name given for callable (default None, automatic)
    :param bool typed: cache different types separately (default False)
    :param str tag: text to associate with arguments (default None)
    :param set ignore: positional or keyword args to ignore (default ())
    :return: callable decorator

    """
    # Caution: Nearly identical code exists in Cache.memoize
    def decorator(func):
        """Decorator created by memoize call for callable."""
        base = (full_name(func),) if name is None else (name,)

        def timer(*args, **kwargs):
            """Time execution of `func` and return result and time delta."""
            start = time.time()
            result = func(*args, **kwargs)
            delta = time.time() - start
            return result, delta

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            """Wrapper for callable to cache arguments and return values."""
            key = wrapper.__cache_key__(*args, **kwargs)
            pair, expire_time = cache.get(
                key,
                default=ENOVAL,
                expire_time=True,
                retry=True,
            )

            if pair is not ENOVAL:
                result, delta = pair
                now = time.time()
                ttl = expire_time - now

                if (-delta * beta * math.log(random.random())) < ttl:
                    return result  # Cache hit.

                # Check whether a thread has started for early recomputation.

                thread_key = key + (ENOVAL,)
                thread_added = cache.add(
                    thread_key,
                    None,
                    expire=delta,
                    retry=True,
                )

                if thread_added:
                    # Start thread for early recomputation.
                    def recompute():
                        with cache:
                            pair = timer(*args, **kwargs)
                            cache.set(
                                key,
                                pair,
                                expire=expire,
                                tag=tag,
                                retry=True,
                            )

                    thread = threading.Thread(target=recompute)
                    thread.daemon = True
                    thread.start()

                return result

            pair = timer(*args, **kwargs)
            cache.set(key, pair, expire=expire, tag=tag, retry=True)
            return pair[0]

        def __cache_key__(*args, **kwargs):
            """Make key for cache given function arguments."""
            return args_to_key(base, args, kwargs, typed, ignore)

        wrapper.__cache_key__ = __cache_key__
        return wrapper

    return decorator
