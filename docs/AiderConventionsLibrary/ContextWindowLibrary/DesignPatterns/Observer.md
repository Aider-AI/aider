## Observer

**Observer** is a behavioral design pattern that lets you define a subscription mechanism to notify multiple objects about any events that happen to the object they're observing.

### Intent

The Observer pattern allows for the establishment of a one-to-many dependency between objects so that when one object changes state, all its dependents are notified and updated automatically.

### Problem

The Observer pattern addresses a common problem where a part of the system needs to react to changes occurring in another part of the system without creating a tight coupling between them.

### Solution

The solution involves adding a subscription mechanism where observers can subscribe and unsubscribe to events or changes in the subject. The subject maintains a list of observers and notifies them of changes by calling one of their methods.

### Real-World Analogy

A real-world analogy for the Observer pattern is a magazine subscription. Subscribers receive new issues of the magazine whenever they are published without having to check the newsstand.

### Structure

1. The **Publisher** (also known as the subject) maintains a list of subscribers and provides methods to add or remove subscribers.
2. The **Subscriber** (also known as the observer) defines an interface for receiving updates from the publisher.
3. When an event occurs, the publisher notifies all subscribers by calling their update method, potentially passing some context data.

### Applicability

Use the Observer pattern when changes to the state of one object may require changing other objects, and the actual set of objects is unknown beforehand or changes dynamically.

### Pros and Cons

- Promotes the principle of loose coupling.
- Allows for dynamic relationships between objects.
- Subscribers are notified in a random order.

### Relations with Other Patterns

- Can be combined with other patterns such as **Mediator**, **Singleton**, and **Command**.

### Implementation

1. Define the observer interface with a notification method.
2. Implement the observer interface in concrete observer classes.
3. Define the publisher interface with methods for adding and removing observers.
4. Implement the publisher interface in concrete publisher classes.
5. The publisher notifies observers of changes by calling their notification method.
6. The client creates publisher and observer objects and registers observers with the publisher.

### Code Examples

The Observer pattern can be implemented in various programming languages using different approaches, such as event delegation, property observers, or reactive streams.
Content attributed to Refactoring Guru - https://refactoring.guru/design-patterns
