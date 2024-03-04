## Iterator in Python

**Iterator** is a behavioral design pattern that allows sequential
traversal through a complex data structure without exposing its internal
details.

Thanks to the Iterator, clients can go over elements of different
collections in a similar fashion using a single iterator interface.

**Complexity:**

**Popularity:**

**Usage examples:** The pattern is very common in Python code. Many
frameworks and libraries use it to provide a standard way for traversing
their collections.

**Identification:** Iterator is easy to recognize by the navigation
methods (such as `next`, `previous` and others). Client code that uses
iterators might not have direct access to the collection being
traversed.

## Conceptual Example

This example illustrates the structure of the **Iterator** design
pattern. It focuses on answering these questions:

-   What classes does it consist of?
-   What roles do these classes play?
-   In what way the elements of the pattern are related?

#### **main.py:** Conceptual example

```python
from __future__ import annotations
from collections.abc import Iterable, Iterator
from typing import Any

class AlphabeticalOrderIterator(Iterator):
    """
    Concrete Iterators implement various traversal algorithms. These classes
    store the current traversal position at all times.
    """

    _position: int = None
    _reverse: bool = False

    def __init__(self, collection: WordsCollection, reverse: bool = False) -> None:
        self._collection = collection
        self._reverse = reverse
        self._position = -1 if reverse else 0

    def __next__(self) -> Any:
        """
        The __next__() method must return the next item in the sequence. On
        reaching the end, and in subsequent calls, it must raise StopIteration.
        """
        try:
            value = self._collection[self._position]
            self._position += -1 if self._reverse else 1
        except IndexError:
            raise StopIteration()

        return value

class WordsCollection(Iterable):
    """
    Concrete Collections provide one or several methods for retrieving fresh
    iterator instances, compatible with the collection class.
    """

    def __init__(self, collection: list[Any] | None = None) -> None:
        self._collection = collection or []

    def __getitem__(self, index: int) -> Any:
        return self._collection[index]

    def __iter__(self) -> AlphabeticalOrderIterator:
        """
        The __iter__() method returns the iterator object itself, by default we
        return the iterator in ascending order.
        """
        return AlphabeticalOrderIterator(self)

    def get_reverse_iterator(self) -> AlphabeticalOrderIterator:
        return AlphabeticalOrderIterator(self, True)

    def add_item(self, item: Any) -> None:
        self._collection.append(item)

if __name__ == "__main__":
    collection = WordsCollection()
    collection.add_item("First")
    collection.add_item("Second")
    collection.add_item("Third")

    print("Straight traversal:")
    print("\n".join(collection))
    print("")

    print("Reverse traversal:")
    print("\n".join(collection.get_reverse_iterator()), end="")
```

#### **Output.txt:** Execution result

```plaintext
Straight traversal:
First
Second
Third

Reverse traversal:
Third
Second
First
```
Content attributed to Refactoring Guru - https://refactoring.guru/design-patterns
