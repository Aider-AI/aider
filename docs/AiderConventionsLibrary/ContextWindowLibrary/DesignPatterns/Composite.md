Composite

Also known as: Object Tree

Intent

Composite is a structural design pattern that lets you compose objects into tree structures and then work with these structures as if they were individual objects.

Problem

Using the Composite pattern makes sense only when the core model of your app can be represented as a tree.

For example, imagine that you have two types of objects: Products and Boxes. A Box can contain several Products as well as a number of smaller Boxes. These little Boxes can also hold some Products or even smaller Boxes, and so on.

Solution

The Composite pattern suggests that you work with Products and Boxes through a common interface which declares a method for calculating the total price.

Real-World Analogy

Armies of most countries are structured as hierarchies. An army consists of several divisions; a division is a set of brigades, and a brigade consists of platoons, which can be broken down into squads. Finally, a squad is a small group of real soldiers. Orders are given at the top of the hierarchy and passed down onto each level until every soldier knows what needs to be done.

Structure

1. The Component interface describes operations that are common to both simple and complex elements of the tree.
2. The Leaf is a basic element of a tree that doesn't have sub-elements.
3. The Container (aka composite) is an element that has sub-elements: leaves or other containers. A container doesn't know the concrete classes of its children. It works with all sub-elements only via the component interface.
4. The Client works with all elements through the component interface. As a result, the client can work in the same way with both simple or complex elements of the tree.

Applicability

Use the Composite pattern when you have to implement a tree-like object structure.

Use the pattern when you want the client code to treat both simple and complex elements uniformly.

How to Implement

1. Make sure that the core model of your app can be represented as a tree structure.
2. Declare the component interface with a list of methods that make sense for both simple and complex components.
3. Create a leaf class to represent simple elements.
4. Create a container class to represent complex elements.
5. Finally, define the methods for adding and removal of child elements in the container.

Pros and Cons

- You can work with complex tree structures more conveniently.
- Open/Closed Principle. You can introduce new element types into the app without breaking the existing code.

- It might be difficult to provide a common interface for classes whose functionality differs too much.

Relations with Other Patterns

- You can use Builder when creating complex Composite trees because you can program its construction steps to work recursively.
- Chain of Responsibility is often used in conjunction with Composite.
- You can use Iterators to traverse Composite trees.
- You can use Visitor to execute an operation over an entire Composite tree.
- Composite and Decorator have similar structure diagrams since both rely on recursive composition to organize an open-ended number of objects.
Content attributed to Refactoring Guru - https://refactoring.guru/design-patterns
