## Iterator

**Iterator** is a behavioral design pattern that lets you traverse elements of a collection without exposing its underlying representation (list, stack, tree, etc.).

### Intent

The main idea of the Iterator pattern is to extract the traversal behavior of a collection into a separate object called an *iterator*.

### Problem

Collections store their elements in various ways. To access these elements, there should be a way to traverse each element of the collection without accessing the same elements over and over.

### Solution

Iterators encapsulate the traversal details, such as the current position and how many elements are left till the end. This allows several iterators to traverse the same collection independently.

### Real-World Analogy

Visiting a city and using different methods to see all the sights—whether it's a smartphone app or a human guide—can be thought of as using different types of iterators.

### Structure

1. The **Iterator** interface declares operations for traversing a collection.
2. **Concrete Iterators** implement specific algorithms for traversing a collection.
3. The **Collection** interface declares methods for getting iterators compatible with the collection.
4. **Concrete Collections** return new instances of a particular concrete iterator class each time the client requests one.
5. The **Client** works with both collections and iterators via their interfaces.

### Applicability

Use the Iterator pattern when your collection has a complex data structure, you want to hide its complexity from clients, or you want to reduce duplication of the traversal code.

### Pros and Cons

- Promotes the Single Responsibility and Open/Closed Principles.
- Allows parallel traversal of collections.
- Can be overkill for simple collections and may be less efficient than specialized collections.

### Relations with Other Patterns

- Can be combined with **Composite**, **Factory Method**, **Memento**, and **Visitor** patterns.

### Implementation

1. Declare the iterator interface.
2. Declare the collection interface with a method for fetching iterators.
3. Implement concrete iterator classes for the collections you want to be traversable.
4. Implement the collection interface in your collection classes.
5. Replace all collection traversal code in the client with the use of iterators.
