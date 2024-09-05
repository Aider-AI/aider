"""Persistent Data Types
"""

import operator as op
from collections import OrderedDict
from collections.abc import (
    ItemsView,
    KeysView,
    MutableMapping,
    Sequence,
    ValuesView,
)
from contextlib import contextmanager
from shutil import rmtree

from .core import ENOVAL, Cache


def _make_compare(seq_op, doc):
    """Make compare method with Sequence semantics."""

    def compare(self, that):
        """Compare method for deque and sequence."""
        if not isinstance(that, Sequence):
            return NotImplemented

        len_self = len(self)
        len_that = len(that)

        if len_self != len_that:
            if seq_op is op.eq:
                return False
            if seq_op is op.ne:
                return True

        for alpha, beta in zip(self, that):
            if alpha != beta:
                return seq_op(alpha, beta)

        return seq_op(len_self, len_that)

    compare.__name__ = '__{0}__'.format(seq_op.__name__)
    doc_str = 'Return True if and only if deque is {0} `that`.'
    compare.__doc__ = doc_str.format(doc)

    return compare


class Deque(Sequence):
    """Persistent sequence with double-ended queue semantics.

    Double-ended queue is an ordered collection with optimized access at its
    endpoints.

    Items are serialized to disk. Deque may be initialized from directory path
    where items are stored.

    >>> deque = Deque()
    >>> deque += range(5)
    >>> list(deque)
    [0, 1, 2, 3, 4]
    >>> for value in range(5):
    ...     deque.appendleft(-value)
    >>> len(deque)
    10
    >>> list(deque)
    [-4, -3, -2, -1, 0, 0, 1, 2, 3, 4]
    >>> deque.pop()
    4
    >>> deque.popleft()
    -4
    >>> deque.reverse()
    >>> list(deque)
    [3, 2, 1, 0, 0, -1, -2, -3]

    """

    def __init__(self, iterable=(), directory=None, maxlen=None):
        """Initialize deque instance.

        If directory is None then temporary directory created. The directory
        will *not* be automatically removed.

        :param iterable: iterable of items to append to deque
        :param directory: deque directory (default None)

        """
        self._cache = Cache(directory, eviction_policy='none')
        self._maxlen = float('inf') if maxlen is None else maxlen
        self._extend(iterable)

    @classmethod
    def fromcache(cls, cache, iterable=(), maxlen=None):
        """Initialize deque using `cache`.

        >>> cache = Cache()
        >>> deque = Deque.fromcache(cache, [5, 6, 7, 8])
        >>> deque.cache is cache
        True
        >>> len(deque)
        4
        >>> 7 in deque
        True
        >>> deque.popleft()
        5

        :param Cache cache: cache to use
        :param iterable: iterable of items
        :return: initialized Deque

        """
        # pylint: disable=no-member,protected-access
        self = cls.__new__(cls)
        self._cache = cache
        self._maxlen = float('inf') if maxlen is None else maxlen
        self._extend(iterable)
        return self

    @property
    def cache(self):
        """Cache used by deque."""
        return self._cache

    @property
    def directory(self):
        """Directory path where deque is stored."""
        return self._cache.directory

    @property
    def maxlen(self):
        """Max length of the deque."""
        return self._maxlen

    @maxlen.setter
    def maxlen(self, value):
        """Set max length of the deque.

        Pops items from left while length greater than max.

        >>> deque = Deque()
        >>> deque.extendleft('abcde')
        >>> deque.maxlen = 3
        >>> list(deque)
        ['c', 'd', 'e']

        :param value: max length

        """
        self._maxlen = value
        with self._cache.transact(retry=True):
            while len(self._cache) > self._maxlen:
                self._popleft()

    def _index(self, index, func):
        len_self = len(self)

        if index >= 0:
            if index >= len_self:
                raise IndexError('deque index out of range')

            for key in self._cache.iterkeys():
                if index == 0:
                    try:
                        return func(key)
                    except KeyError:
                        continue
                index -= 1
        else:
            if index < -len_self:
                raise IndexError('deque index out of range')

            index += 1

            for key in self._cache.iterkeys(reverse=True):
                if index == 0:
                    try:
                        return func(key)
                    except KeyError:
                        continue
                index += 1

        raise IndexError('deque index out of range')

    def __getitem__(self, index):
        """deque.__getitem__(index) <==> deque[index]

        Return corresponding item for `index` in deque.

        See also `Deque.peekleft` and `Deque.peek` for indexing deque at index
        ``0`` or ``-1``.

        >>> deque = Deque()
        >>> deque.extend('abcde')
        >>> deque[1]
        'b'
        >>> deque[-2]
        'd'

        :param int index: index of item
        :return: corresponding item
        :raises IndexError: if index out of range

        """
        return self._index(index, self._cache.__getitem__)

    def __setitem__(self, index, value):
        """deque.__setitem__(index, value) <==> deque[index] = value

        Store `value` in deque at `index`.

        >>> deque = Deque()
        >>> deque.extend([None] * 3)
        >>> deque[0] = 'a'
        >>> deque[1] = 'b'
        >>> deque[-1] = 'c'
        >>> ''.join(deque)
        'abc'

        :param int index: index of value
        :param value: value to store
        :raises IndexError: if index out of range

        """

        def _set_value(key):
            return self._cache.__setitem__(key, value)

        self._index(index, _set_value)

    def __delitem__(self, index):
        """deque.__delitem__(index) <==> del deque[index]

        Delete item in deque at `index`.

        >>> deque = Deque()
        >>> deque.extend([None] * 3)
        >>> del deque[0]
        >>> del deque[1]
        >>> del deque[-1]
        >>> len(deque)
        0

        :param int index: index of item
        :raises IndexError: if index out of range

        """
        self._index(index, self._cache.__delitem__)

    def __repr__(self):
        """deque.__repr__() <==> repr(deque)

        Return string with printable representation of deque.

        """
        name = type(self).__name__
        return '{0}(directory={1!r})'.format(name, self.directory)

    __eq__ = _make_compare(op.eq, 'equal to')
    __ne__ = _make_compare(op.ne, 'not equal to')
    __lt__ = _make_compare(op.lt, 'less than')
    __gt__ = _make_compare(op.gt, 'greater than')
    __le__ = _make_compare(op.le, 'less than or equal to')
    __ge__ = _make_compare(op.ge, 'greater than or equal to')

    def __iadd__(self, iterable):
        """deque.__iadd__(iterable) <==> deque += iterable

        Extend back side of deque with items from iterable.

        :param iterable: iterable of items to append to deque
        :return: deque with added items

        """
        self._extend(iterable)
        return self

    def __iter__(self):
        """deque.__iter__() <==> iter(deque)

        Return iterator of deque from front to back.

        """
        _cache = self._cache

        for key in _cache.iterkeys():
            try:
                yield _cache[key]
            except KeyError:
                pass

    def __len__(self):
        """deque.__len__() <==> len(deque)

        Return length of deque.

        """
        return len(self._cache)

    def __reversed__(self):
        """deque.__reversed__() <==> reversed(deque)

        Return iterator of deque from back to front.

        >>> deque = Deque()
        >>> deque.extend('abcd')
        >>> iterator = reversed(deque)
        >>> next(iterator)
        'd'
        >>> list(iterator)
        ['c', 'b', 'a']

        """
        _cache = self._cache

        for key in _cache.iterkeys(reverse=True):
            try:
                yield _cache[key]
            except KeyError:
                pass

    def __getstate__(self):
        return self.directory, self.maxlen

    def __setstate__(self, state):
        directory, maxlen = state
        self.__init__(directory=directory, maxlen=maxlen)

    def append(self, value):
        """Add `value` to back of deque.

        >>> deque = Deque()
        >>> deque.append('a')
        >>> deque.append('b')
        >>> deque.append('c')
        >>> list(deque)
        ['a', 'b', 'c']

        :param value: value to add to back of deque

        """
        with self._cache.transact(retry=True):
            self._cache.push(value, retry=True)
            if len(self._cache) > self._maxlen:
                self._popleft()

    _append = append

    def appendleft(self, value):
        """Add `value` to front of deque.

        >>> deque = Deque()
        >>> deque.appendleft('a')
        >>> deque.appendleft('b')
        >>> deque.appendleft('c')
        >>> list(deque)
        ['c', 'b', 'a']

        :param value: value to add to front of deque

        """
        with self._cache.transact(retry=True):
            self._cache.push(value, side='front', retry=True)
            if len(self._cache) > self._maxlen:
                self._pop()

    _appendleft = appendleft

    def clear(self):
        """Remove all elements from deque.

        >>> deque = Deque('abc')
        >>> len(deque)
        3
        >>> deque.clear()
        >>> list(deque)
        []

        """
        self._cache.clear(retry=True)

    _clear = clear

    def copy(self):
        """Copy deque with same directory and max length."""
        TypeSelf = type(self)
        return TypeSelf(directory=self.directory, maxlen=self.maxlen)

    def count(self, value):
        """Return number of occurrences of `value` in deque.

        >>> deque = Deque()
        >>> deque += [num for num in range(1, 5) for _ in range(num)]
        >>> deque.count(0)
        0
        >>> deque.count(1)
        1
        >>> deque.count(4)
        4

        :param value: value to count in deque
        :return: count of items equal to value in deque

        """
        return sum(1 for item in self if value == item)

    def extend(self, iterable):
        """Extend back side of deque with values from `iterable`.

        :param iterable: iterable of values

        """
        for value in iterable:
            self._append(value)

    _extend = extend

    def extendleft(self, iterable):
        """Extend front side of deque with value from `iterable`.

        >>> deque = Deque()
        >>> deque.extendleft('abc')
        >>> list(deque)
        ['c', 'b', 'a']

        :param iterable: iterable of values

        """
        for value in iterable:
            self._appendleft(value)

    def peek(self):
        """Peek at value at back of deque.

        Faster than indexing deque at -1.

        If deque is empty then raise IndexError.

        >>> deque = Deque()
        >>> deque.peek()
        Traceback (most recent call last):
            ...
        IndexError: peek from an empty deque
        >>> deque += 'abc'
        >>> deque.peek()
        'c'

        :return: value at back of deque
        :raises IndexError: if deque is empty

        """
        default = None, ENOVAL
        _, value = self._cache.peek(default=default, side='back', retry=True)
        if value is ENOVAL:
            raise IndexError('peek from an empty deque')
        return value

    def peekleft(self):
        """Peek at value at front of deque.

        Faster than indexing deque at 0.

        If deque is empty then raise IndexError.

        >>> deque = Deque()
        >>> deque.peekleft()
        Traceback (most recent call last):
            ...
        IndexError: peek from an empty deque
        >>> deque += 'abc'
        >>> deque.peekleft()
        'a'

        :return: value at front of deque
        :raises IndexError: if deque is empty

        """
        default = None, ENOVAL
        _, value = self._cache.peek(default=default, side='front', retry=True)
        if value is ENOVAL:
            raise IndexError('peek from an empty deque')
        return value

    def pop(self):
        """Remove and return value at back of deque.

        If deque is empty then raise IndexError.

        >>> deque = Deque()
        >>> deque += 'ab'
        >>> deque.pop()
        'b'
        >>> deque.pop()
        'a'
        >>> deque.pop()
        Traceback (most recent call last):
            ...
        IndexError: pop from an empty deque

        :return: value at back of deque
        :raises IndexError: if deque is empty

        """
        default = None, ENOVAL
        _, value = self._cache.pull(default=default, side='back', retry=True)
        if value is ENOVAL:
            raise IndexError('pop from an empty deque')
        return value

    _pop = pop

    def popleft(self):
        """Remove and return value at front of deque.

        >>> deque = Deque()
        >>> deque += 'ab'
        >>> deque.popleft()
        'a'
        >>> deque.popleft()
        'b'
        >>> deque.popleft()
        Traceback (most recent call last):
            ...
        IndexError: pop from an empty deque

        :return: value at front of deque
        :raises IndexError: if deque is empty

        """
        default = None, ENOVAL
        _, value = self._cache.pull(default=default, retry=True)
        if value is ENOVAL:
            raise IndexError('pop from an empty deque')
        return value

    _popleft = popleft

    def remove(self, value):
        """Remove first occurrence of `value` in deque.

        >>> deque = Deque()
        >>> deque += 'aab'
        >>> deque.remove('a')
        >>> list(deque)
        ['a', 'b']
        >>> deque.remove('b')
        >>> list(deque)
        ['a']
        >>> deque.remove('c')
        Traceback (most recent call last):
            ...
        ValueError: deque.remove(value): value not in deque

        :param value: value to remove
        :raises ValueError: if value not in deque

        """
        _cache = self._cache

        for key in _cache.iterkeys():
            try:
                item = _cache[key]
            except KeyError:
                continue
            else:
                if value == item:
                    try:
                        del _cache[key]
                    except KeyError:
                        continue
                    return

        raise ValueError('deque.remove(value): value not in deque')

    def reverse(self):
        """Reverse deque in place.

        >>> deque = Deque()
        >>> deque += 'abc'
        >>> deque.reverse()
        >>> list(deque)
        ['c', 'b', 'a']

        """
        # pylint: disable=protected-access
        # GrantJ 2019-03-22 Consider using an algorithm that swaps the values
        # at two keys. Like self._cache.swap(key1, key2, retry=True) The swap
        # method would exchange the values at two given keys. Then, using a
        # forward iterator and a reverse iterator, the reverse method could
        # avoid making copies of the values.
        temp = Deque(iterable=reversed(self))
        self._clear()
        self._extend(temp)
        directory = temp.directory
        temp._cache.close()
        del temp
        rmtree(directory)

    def rotate(self, steps=1):
        """Rotate deque right by `steps`.

        If steps is negative then rotate left.

        >>> deque = Deque()
        >>> deque += range(5)
        >>> deque.rotate(2)
        >>> list(deque)
        [3, 4, 0, 1, 2]
        >>> deque.rotate(-1)
        >>> list(deque)
        [4, 0, 1, 2, 3]

        :param int steps: number of steps to rotate (default 1)

        """
        if not isinstance(steps, int):
            type_name = type(steps).__name__
            raise TypeError('integer argument expected, got %s' % type_name)

        len_self = len(self)

        if not len_self:
            return

        if steps >= 0:
            steps %= len_self

            for _ in range(steps):
                try:
                    value = self._pop()
                except IndexError:
                    return
                else:
                    self._appendleft(value)
        else:
            steps *= -1
            steps %= len_self

            for _ in range(steps):
                try:
                    value = self._popleft()
                except IndexError:
                    return
                else:
                    self._append(value)

    __hash__ = None  # type: ignore

    @contextmanager
    def transact(self):
        """Context manager to perform a transaction by locking the deque.

        While the deque is locked, no other write operation is permitted.
        Transactions should therefore be as short as possible. Read and write
        operations performed in a transaction are atomic. Read operations may
        occur concurrent to a transaction.

        Transactions may be nested and may not be shared between threads.

        >>> from diskcache import Deque
        >>> deque = Deque()
        >>> deque += range(5)
        >>> with deque.transact():  # Atomically rotate elements.
        ...     value = deque.pop()
        ...     deque.appendleft(value)
        >>> list(deque)
        [4, 0, 1, 2, 3]

        :return: context manager for use in `with` statement

        """
        with self._cache.transact(retry=True):
            yield


class Index(MutableMapping):
    """Persistent mutable mapping with insertion order iteration.

    Items are serialized to disk. Index may be initialized from directory path
    where items are stored.

    Hashing protocol is not used. Keys are looked up by their serialized
    format. See ``diskcache.Disk`` for details.

    >>> index = Index()
    >>> index.update([('a', 1), ('b', 2), ('c', 3)])
    >>> index['a']
    1
    >>> list(index)
    ['a', 'b', 'c']
    >>> len(index)
    3
    >>> del index['b']
    >>> index.popitem()
    ('c', 3)

    """

    def __init__(self, *args, **kwargs):
        """Initialize index in directory and update items.

        Optional first argument may be string specifying directory where items
        are stored. When None or not given, temporary directory is created.

        >>> index = Index({'a': 1, 'b': 2, 'c': 3})
        >>> len(index)
        3
        >>> directory = index.directory
        >>> inventory = Index(directory, d=4)
        >>> inventory['b']
        2
        >>> len(inventory)
        4

        """
        if args and isinstance(args[0], (bytes, str)):
            directory = args[0]
            args = args[1:]
        else:
            if args and args[0] is None:
                args = args[1:]
            directory = None
        self._cache = Cache(directory, eviction_policy='none')
        self._update(*args, **kwargs)

    _update = MutableMapping.update

    @classmethod
    def fromcache(cls, cache, *args, **kwargs):
        """Initialize index using `cache` and update items.

        >>> cache = Cache()
        >>> index = Index.fromcache(cache, {'a': 1, 'b': 2, 'c': 3})
        >>> index.cache is cache
        True
        >>> len(index)
        3
        >>> 'b' in index
        True
        >>> index['c']
        3

        :param Cache cache: cache to use
        :param args: mapping or sequence of items
        :param kwargs: mapping of items
        :return: initialized Index

        """
        # pylint: disable=no-member,protected-access
        self = cls.__new__(cls)
        self._cache = cache
        self._update(*args, **kwargs)
        return self

    @property
    def cache(self):
        """Cache used by index."""
        return self._cache

    @property
    def directory(self):
        """Directory path where items are stored."""
        return self._cache.directory

    def __getitem__(self, key):
        """index.__getitem__(key) <==> index[key]

        Return corresponding value for `key` in index.

        >>> index = Index()
        >>> index.update({'a': 1, 'b': 2})
        >>> index['a']
        1
        >>> index['b']
        2
        >>> index['c']
        Traceback (most recent call last):
            ...
        KeyError: 'c'

        :param key: key for item
        :return: value for item in index with given key
        :raises KeyError: if key is not found

        """
        return self._cache[key]

    def __setitem__(self, key, value):
        """index.__setitem__(key, value) <==> index[key] = value

        Set `key` and `value` item in index.

        >>> index = Index()
        >>> index['a'] = 1
        >>> index[0] = None
        >>> len(index)
        2

        :param key: key for item
        :param value: value for item

        """
        self._cache[key] = value

    def __delitem__(self, key):
        """index.__delitem__(key) <==> del index[key]

        Delete corresponding item for `key` from index.

        >>> index = Index()
        >>> index.update({'a': 1, 'b': 2})
        >>> del index['a']
        >>> del index['b']
        >>> len(index)
        0
        >>> del index['c']
        Traceback (most recent call last):
            ...
        KeyError: 'c'

        :param key: key for item
        :raises KeyError: if key is not found

        """
        del self._cache[key]

    def setdefault(self, key, default=None):
        """Set and get value for `key` in index using `default`.

        If `key` is not in index then set corresponding value to `default`. If
        `key` is in index then ignore `default` and return existing value.

        >>> index = Index()
        >>> index.setdefault('a', 0)
        0
        >>> index.setdefault('a', 1)
        0

        :param key: key for item
        :param default: value if key is missing (default None)
        :return: value for item in index with given key

        """
        _cache = self._cache
        while True:
            try:
                return _cache[key]
            except KeyError:
                _cache.add(key, default, retry=True)

    def peekitem(self, last=True):
        """Peek at key and value item pair in index based on iteration order.

        >>> index = Index()
        >>> for num, letter in enumerate('xyz'):
        ...     index[letter] = num
        >>> index.peekitem()
        ('z', 2)
        >>> index.peekitem(last=False)
        ('x', 0)

        :param bool last: last item in iteration order (default True)
        :return: key and value item pair
        :raises KeyError: if cache is empty

        """
        return self._cache.peekitem(last, retry=True)

    def pop(self, key, default=ENOVAL):
        """Remove corresponding item for `key` from index and return value.

        If `key` is missing then return `default`. If `default` is `ENOVAL`
        then raise KeyError.

        >>> index = Index({'a': 1, 'b': 2})
        >>> index.pop('a')
        1
        >>> index.pop('b')
        2
        >>> index.pop('c', default=3)
        3
        >>> index.pop('d')
        Traceback (most recent call last):
            ...
        KeyError: 'd'

        :param key: key for item
        :param default: return value if key is missing (default ENOVAL)
        :return: value for item if key is found else default
        :raises KeyError: if key is not found and default is ENOVAL

        """
        _cache = self._cache
        value = _cache.pop(key, default=default, retry=True)
        if value is ENOVAL:
            raise KeyError(key)
        return value

    def popitem(self, last=True):
        """Remove and return item pair.

        Item pairs are returned in last-in-first-out (LIFO) order if last is
        True else first-in-first-out (FIFO) order. LIFO order imitates a stack
        and FIFO order imitates a queue.

        >>> index = Index()
        >>> index.update([('a', 1), ('b', 2), ('c', 3)])
        >>> index.popitem()
        ('c', 3)
        >>> index.popitem(last=False)
        ('a', 1)
        >>> index.popitem()
        ('b', 2)
        >>> index.popitem()
        Traceback (most recent call last):
          ...
        KeyError: 'dictionary is empty'

        :param bool last: pop last item pair (default True)
        :return: key and value item pair
        :raises KeyError: if index is empty

        """
        # pylint: disable=arguments-differ,unbalanced-tuple-unpacking
        _cache = self._cache

        with _cache.transact(retry=True):
            key, value = _cache.peekitem(last=last)
            del _cache[key]

        return key, value

    def push(self, value, prefix=None, side='back'):
        """Push `value` onto `side` of queue in index identified by `prefix`.

        When prefix is None, integer keys are used. Otherwise, string keys are
        used in the format "prefix-integer". Integer starts at 500 trillion.

        Defaults to pushing value on back of queue. Set side to 'front' to push
        value on front of queue. Side must be one of 'back' or 'front'.

        See also `Index.pull`.

        >>> index = Index()
        >>> print(index.push('apples'))
        500000000000000
        >>> print(index.push('beans'))
        500000000000001
        >>> print(index.push('cherries', side='front'))
        499999999999999
        >>> index[500000000000001]
        'beans'
        >>> index.push('dates', prefix='fruit')
        'fruit-500000000000000'

        :param value: value for item
        :param str prefix: key prefix (default None, key is integer)
        :param str side: either 'back' or 'front' (default 'back')
        :return: key for item in cache

        """
        return self._cache.push(value, prefix, side, retry=True)

    def pull(self, prefix=None, default=(None, None), side='front'):
        """Pull key and value item pair from `side` of queue in index.

        When prefix is None, integer keys are used. Otherwise, string keys are
        used in the format "prefix-integer". Integer starts at 500 trillion.

        If queue is empty, return default.

        Defaults to pulling key and value item pairs from front of queue. Set
        side to 'back' to pull from back of queue. Side must be one of 'front'
        or 'back'.

        See also `Index.push`.

        >>> index = Index()
        >>> for letter in 'abc':
        ...     print(index.push(letter))
        500000000000000
        500000000000001
        500000000000002
        >>> key, value = index.pull()
        >>> print(key)
        500000000000000
        >>> value
        'a'
        >>> _, value = index.pull(side='back')
        >>> value
        'c'
        >>> index.pull(prefix='fruit')
        (None, None)

        :param str prefix: key prefix (default None, key is integer)
        :param default: value to return if key is missing
            (default (None, None))
        :param str side: either 'front' or 'back' (default 'front')
        :return: key and value item pair or default if queue is empty

        """
        return self._cache.pull(prefix, default, side, retry=True)

    def clear(self):
        """Remove all items from index.

        >>> index = Index({'a': 0, 'b': 1, 'c': 2})
        >>> len(index)
        3
        >>> index.clear()
        >>> dict(index)
        {}

        """
        self._cache.clear(retry=True)

    def __iter__(self):
        """index.__iter__() <==> iter(index)

        Return iterator of index keys in insertion order.

        """
        return iter(self._cache)

    def __reversed__(self):
        """index.__reversed__() <==> reversed(index)

        Return iterator of index keys in reversed insertion order.

        >>> index = Index()
        >>> index.update([('a', 1), ('b', 2), ('c', 3)])
        >>> iterator = reversed(index)
        >>> next(iterator)
        'c'
        >>> list(iterator)
        ['b', 'a']

        """
        return reversed(self._cache)

    def __len__(self):
        """index.__len__() <==> len(index)

        Return length of index.

        """
        return len(self._cache)

    def keys(self):
        """Set-like object providing a view of index keys.

        >>> index = Index()
        >>> index.update({'a': 1, 'b': 2, 'c': 3})
        >>> keys_view = index.keys()
        >>> 'b' in keys_view
        True

        :return: keys view

        """
        return KeysView(self)

    def values(self):
        """Set-like object providing a view of index values.

        >>> index = Index()
        >>> index.update({'a': 1, 'b': 2, 'c': 3})
        >>> values_view = index.values()
        >>> 2 in values_view
        True

        :return: values view

        """
        return ValuesView(self)

    def items(self):
        """Set-like object providing a view of index items.

        >>> index = Index()
        >>> index.update({'a': 1, 'b': 2, 'c': 3})
        >>> items_view = index.items()
        >>> ('b', 2) in items_view
        True

        :return: items view

        """
        return ItemsView(self)

    __hash__ = None  # type: ignore

    def __getstate__(self):
        return self.directory

    def __setstate__(self, state):
        self.__init__(state)

    def __eq__(self, other):
        """index.__eq__(other) <==> index == other

        Compare equality for index and `other`.

        Comparison to another index or ordered dictionary is
        order-sensitive. Comparison to all other mappings is order-insensitive.

        >>> index = Index()
        >>> pairs = [('a', 1), ('b', 2), ('c', 3)]
        >>> index.update(pairs)
        >>> from collections import OrderedDict
        >>> od = OrderedDict(pairs)
        >>> index == od
        True
        >>> index == {'c': 3, 'b': 2, 'a': 1}
        True

        :param other: other mapping in equality comparison
        :return: True if index equals other

        """
        if len(self) != len(other):
            return False

        if isinstance(other, (Index, OrderedDict)):
            alpha = ((key, self[key]) for key in self)
            beta = ((key, other[key]) for key in other)
            pairs = zip(alpha, beta)
            return not any(a != x or b != y for (a, b), (x, y) in pairs)
        else:
            return all(self[key] == other.get(key, ENOVAL) for key in self)

    def __ne__(self, other):
        """index.__ne__(other) <==> index != other

        Compare inequality for index and `other`.

        Comparison to another index or ordered dictionary is
        order-sensitive. Comparison to all other mappings is order-insensitive.

        >>> index = Index()
        >>> index.update([('a', 1), ('b', 2), ('c', 3)])
        >>> from collections import OrderedDict
        >>> od = OrderedDict([('c', 3), ('b', 2), ('a', 1)])
        >>> index != od
        True
        >>> index != {'a': 1, 'b': 2}
        True

        :param other: other mapping in inequality comparison
        :return: True if index does not equal other

        """
        return not self == other

    def memoize(self, name=None, typed=False, ignore=()):
        """Memoizing cache decorator.

        Decorator to wrap callable with memoizing function using cache.
        Repeated calls with the same arguments will lookup result in cache and
        avoid function evaluation.

        If name is set to None (default), the callable name will be determined
        automatically.

        If typed is set to True, function arguments of different types will be
        cached separately. For example, f(3) and f(3.0) will be treated as
        distinct calls with distinct results.

        The original underlying function is accessible through the __wrapped__
        attribute. This is useful for introspection, for bypassing the cache,
        or for rewrapping the function with a different cache.

        >>> from diskcache import Index
        >>> mapping = Index()
        >>> @mapping.memoize()
        ... def fibonacci(number):
        ...     if number == 0:
        ...         return 0
        ...     elif number == 1:
        ...         return 1
        ...     else:
        ...         return fibonacci(number - 1) + fibonacci(number - 2)
        >>> print(fibonacci(100))
        354224848179261915075

        An additional `__cache_key__` attribute can be used to generate the
        cache key used for the given arguments.

        >>> key = fibonacci.__cache_key__(100)
        >>> print(mapping[key])
        354224848179261915075

        Remember to call memoize when decorating a callable. If you forget,
        then a TypeError will occur. Note the lack of parenthenses after
        memoize below:

        >>> @mapping.memoize
        ... def test():
        ...     pass
        Traceback (most recent call last):
            ...
        TypeError: name cannot be callable

        :param str name: name given for callable (default None, automatic)
        :param bool typed: cache different types separately (default False)
        :param set ignore: positional or keyword args to ignore (default ())
        :return: callable decorator

        """
        return self._cache.memoize(name, typed, ignore=ignore)

    @contextmanager
    def transact(self):
        """Context manager to perform a transaction by locking the index.

        While the index is locked, no other write operation is permitted.
        Transactions should therefore be as short as possible. Read and write
        operations performed in a transaction are atomic. Read operations may
        occur concurrent to a transaction.

        Transactions may be nested and may not be shared between threads.

        >>> from diskcache import Index
        >>> mapping = Index()
        >>> with mapping.transact():  # Atomically increment two keys.
        ...     mapping['total'] = mapping.get('total', 0) + 123.4
        ...     mapping['count'] = mapping.get('count', 0) + 1
        >>> with mapping.transact():  # Atomically calculate average.
        ...     average = mapping['total'] / mapping['count']
        >>> average
        123.4

        :return: context manager for use in `with` statement

        """
        with self._cache.transact(retry=True):
            yield

    def __repr__(self):
        """index.__repr__() <==> repr(index)

        Return string with printable representation of index.

        """
        name = type(self).__name__
        return '{0}({1!r})'.format(name, self.directory)
