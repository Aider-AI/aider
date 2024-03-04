## Monad in Python

**Monad** is a design pattern used in functional programming to handle side effects, manage state, and chain operations in a flexible and composable way.

In Python, the concept of Monads can be implemented using classes that encapsulate a value and provide a method to transform the value while preserving the Monad structure.

## Conceptual Example

This example illustrates a simple implementation of the Monad design pattern. It focuses on answering these questions:

- What classes does it consist of?
- What roles do these classes play?
- In what way the elements of the pattern are related?

#### main.py: Conceptual example

```python
class Monad:
    def __init__(self, value):
        self.value = value

    def bind(self, func):
        return self.__class__(func(self.value))

    def __repr__(self):
        return f"{self.__class__.__name__}({self.value})"

def double(value):
    return value * 2

def increment(value):
    return value + 1

if __name__ == "__main__":
    # Create a Monad instance with an initial value
    number = Monad(10)
    print(f"Initial Monad: {number}")

    # Use the `bind` method to apply functions to the Monad's value
    number = number.bind(double)
    print(f"After doubling: {number}")

    number = number.bind(increment)
    print(f"After incrementing: {number}")
```

#### Output.txt: Execution result

```text
Initial Monad: Monad(10)
After doubling: Monad(20)
After incrementing: Monad(21)
```

The `Monad` class encapsulates a value and allows us to apply transformations to the value using the `bind` method. The `bind` method takes a function, applies it to the value, and returns a new Monad with the result. This allows us to chain operations on the encapsulated value while maintaining the structure of the Monad.
Content attributed to Refactoring Guru - https://refactoring.guru/design-patterns
