## Memento in Python

**Memento** is a behavioral design pattern that allows making snapshots
of an object's state and restoring it in future.

The Memento doesn't compromise the internal structure of the object it
works with, as well as data kept inside the snapshots.

## Conceptual Example

This example illustrates the structure of the **Memento** design
pattern. It focuses on answering these questions:

-   What classes does it consist of?
-   What roles do these classes play?
-   In what way the elements of the pattern are related?

#### main.py: Conceptual example

```python
from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import datetime
from random import sample
from string import ascii_letters

class Originator:
    """
    The Originator holds some important state that may change over time. It also
    defines a method for saving the state inside a memento and another method
    for restoring the state from it.
    """

    _state = None
    """
    For the sake of simplicity, the originator's state is stored inside a single
    variable.
    """

    def __init__(self, state: str) -> None:
        self._state = state
        print(f"Originator: My initial state is: {self._state}")

    def do_something(self) -> None:
        """
        The Originator's business logic may affect its internal state.
        Therefore, the client should backup the state before launching methods
        of the business logic via the save() method.
        """

        print("Originator: I'm doing something important.")
        self._state = self._generate_random_string(30)
        print(f"Originator: and my state has changed to: {self._state}")

    @staticmethod
    def _generate_random_string(length: int = 10) -> str:
        return "".join(sample(ascii_letters, length))

    def save(self) -> Memento:
        """
        Saves the current state inside a memento.
        """

        return ConcreteMemento(self._state)

    def restore(self, memento: Memento) -> None:
        """
        Restores the Originator's state from a memento object.
        """

        self._state = memento.get_state()
        print(f"Originator: My state has changed to: {self._state}")

class Memento(ABC):
    """
    The Memento interface provides a way to retrieve the memento's metadata,
    such as creation date or name. However, it doesn't expose the Originator's
    state.
    """

    @abstractmethod
    def get_name(self) -> str:
        pass

    @abstractmethod
    def get_date(self) -> str:
        pass

class ConcreteMemento(Memento):
    def __init__(self, state: str) -> None:
        self._state = state
        self._date = str(datetime.now())[:19]

    def get_state(self) -> str:
        """
        The Originator uses this method when restoring its state.
        """
        return self._state

    def get_name(self) -> str:
        """
        The rest of the methods are used by the Caretaker to display metadata.
        """

        return f"{self._date} / ({self._state[0:9]}...)"

    def get_date(self) -> str:
        return self._date

class Caretaker:
    """
    The Caretaker doesn't depend on the Concrete Memento class. Therefore, it
    doesn't have access to the originator's state, stored inside the memento. It
    works with all mementos via the base Memento interface.
    """

    def __init__(self, originator: Originator) -> None:
        self._mementos = []
        self._originator = originator

    def backup(self) -> None:
        print("\nCaretaker: Saving Originator's state...")
        self._mementos.append(self._originator.save())

    def undo(self) -> None:
        if not len(self._mementos):
            return

        memento = self._mementos.pop()
        print(f"Caretaker: Restoring state to: {memento.get_name()}")
        try:
            self._originator.restore(memento)
        except Exception:
            self.undo()

    def show_history(self) -> None:
        print("Caretaker: Here's the list of mementos:")
        for memento in self._mementos:
            print(memento.get_name())

if __name__ == "__main__":
    originator = Originator("Super-duper-super-puper-super.")
    caretaker = Caretaker(originator)

    caretaker.backup()
    originator.do_something()

    caretaker.backup()
    originator.do_something()

    caretaker.backup()
    originator.do_something()

    print()
    caretaker.show_history()

    print("\nClient: Now, let's rollback!\n")
    caretaker.undo()

    print("\nClient: Once more!\n")
    caretaker.undo()
```

#### Output.txt: Execution result

```plaintext
Originator: My initial state is: Super-duper-super-puper-super.

Caretaker: Saving Originator's state...
Originator: I'm doing something important.
Originator: and my state has changed to: wQAehHYOqVSlpEXjyIcgobrxsZUnat

Caretaker: Saving Originator's state...
Originator: I'm doing something important.
Originator: and my state has changed to: lHxNORKcsgMWYnJqoXjVCbQLEIeiSp

Caretaker: Saving Originator's state...
Originator: I'm doing something important.
Originator: and my state has changed to: cvIYsRilNOtwynaKdEZpDCQkFAXVMf

Caretaker: Here's the list of mementos:
2019-01-26 21:11:24 / (Super-dup...)
2019-01-26 21:11:24 / (wQAehHYOq...)
2019-01-26 21:11:24 / (lHxNORKcs...)

Client: Now, let's rollback!

Caretaker: Restoring state to: 2019-01-26 21:11:24 / (lHxNORKcs...)
Originator: My state has changed to: lHxNORKcsgMWYnJqoXjVCbQLEIeiSp

Client: Once more!

Caretaker: Restoring state to: 2019-01-26 21:11:24 / (wQAehHYOq...)
Originator: My state has changed to: wQAehHYOqVSlpEXjyIcgobrxsZUnat
```
Content attributed to Refactoring Guru - https://refactoring.guru/design-patterns
