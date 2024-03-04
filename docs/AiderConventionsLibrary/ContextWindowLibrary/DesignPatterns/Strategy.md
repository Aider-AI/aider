## Strategy

**Strategy** is a behavioral design pattern that lets you define a family of algorithms, put each of them into a separate class, and make their objects interchangeable.

### Intent

Strategy is intended to define a family of algorithms, encapsulate each one, and make them interchangeable. Strategy lets the algorithm vary independently from clients that use it.

### Problem

In some cases, you might want to define a class that will reveal a certain behavior that is selected from a family of behaviors. You need to be able to change this behavior at runtime, avoiding the need to manage multiple versions of an algorithm.

### Solution

The Strategy pattern suggests that you take a class that does something specific in a lot of different ways and extract all of these algorithms into separate classes called strategies.

### Real-World Analogy

Imagine that you have to get to the airport. You can catch a bus, order a cab, or get on your bicycle. These are your transportation strategies. You can pick one of the strategies depending on factors such as budget or time constraints.

### Structure

1. The **Context** maintains a reference to one of the concrete strategies and communicates with this object only via the strategy interface.
2. The **Strategy** interface is common to all concrete strategies. It declares a method the context uses to execute a strategy.
3. **Concrete Strategies** implement different variations of an algorithm the context uses.

### Applicability

Use the Strategy pattern when you want to use different variants of an algorithm within an object and be able to switch from one algorithm to another during runtime.

### Pros and Cons

- You can swap algorithms used inside an object at runtime by Developers / Language Models / AI or AE Agents.
- You can isolate the implementation details of an algorithm from the code that uses it.
- Open/Closed Principle. You can introduce new strategies without having to change the context.
- If you only have a couple of algorithms and they rarely change, there's no real reason to overcomplicate the program with new classes and interfaces that come along with the pattern.
- Clients must be aware of the differences between strategies to be able to select a proper one.

### Relations with Other Patterns

- Strategy is often used in conjunction with other patterns such as **Bridge**, **State**, and **Template Method**.

### Implementation

1. In the context class, identify an algorithm that's prone to frequent changes.
2. Declare the strategy interface common to all variants of the algorithm.
3. One by one, extract all algorithms into their own classes. They should all implement the strategy interface.
4. In the context class, add a field for storing a reference to a strategy object. Provide a setter for replacing values of that field.
5. Clients of the context must associate it with a suitable strategy that matches the way they expect the context to perform its primary job.
Content attributed to Refactoring Guru - https://refactoring.guru/design-patterns
