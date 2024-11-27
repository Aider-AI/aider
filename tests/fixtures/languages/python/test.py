from typing import List, Optional


class Person:
    """A class representing a person."""

    def __init__(self, name: str, age: Optional[int] = None):
        self.name = name
        self.age = age

    def greet(self, formal: bool = False) -> str:
        """Generate a greeting."""
        prefix = "Good day" if formal else "Hello"
        return f"{prefix}, {self.name}!"


def create_greeting_list(people: List[Person]) -> List[str]:
    """Create greetings for a list of people."""
    return [person.greet() for person in people]


# Constants
DEFAULT_NAME = "World"
MAX_AGE = 150

if __name__ == "__main__":
    person = Person(DEFAULT_NAME)
    print(person.greet())
