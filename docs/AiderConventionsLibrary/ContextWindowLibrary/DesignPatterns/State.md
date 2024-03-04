## Intent

**State** is a behavioral design pattern that lets an object alter its behavior when its internal state changes. It appears as if the object changed its class.

## Problem

The State pattern is closely related to the concept of a Finite-State Machine. The main idea is that, at any given moment, there's a finite number of states which a program can be in. Within any unique state, the program behaves differently, and the program can be switched from one state to another instantaneously. However, depending on a current state, the program may or may not switch to certain other states. These switching rules, called transitions, are also finite and predetermined.

## Solution

The State pattern suggests that you create new classes for all possible states of an object and extract all state-specific behaviors into these classes.

Instead of implementing all behaviors on its own, the original object, called context, stores a reference to one of the state objects that represents its current state, and delegates all the state-related work to that object.

## Real-World Analogy

The buttons and switches in your smartphone behave differently depending on the current state of the device.

## Structure

1. **Context** stores a reference to one of the concrete state objects and delegates to it all state-specific work.
2. The **State** interface declares the state-specific methods.
3. **Concrete States** provide their own implementations for the state-specific methods.
4. Both context and concrete states can set the next state of the context and perform the actual state transition by replacing the state object linked to the context.

## Applicability

Use the State pattern when you have an object that behaves differently depending on its current state, the number of states is enormous, and the state-specific code changes frequently.

## How to Implement

1. Decide what class will act as the context.
2. Declare the state interface.
3. For every actual state, create a class that derives from the state interface.
4. In the context class, add a reference field of the state interface type and a public setter that allows overriding the value of that field.
5. Go over the method of the context again and replace empty state conditionals with calls to corresponding methods of the state object.
6. To switch the state of the context, create an instance of one of the state classes and pass it to the context.

## Pros and Cons

- Organize the code related to particular states into separate classes.
- Introduce new states without changing existing state classes or the context.
- Simplify the code of the context by eliminating bulky state machine conditionals.

- Applying the pattern can be overkill if a state machine has only a few states or rarely changes.

## Relations with Other Patterns

- **State** can be considered as an extension of **Strategy**.
- **State** pattern lets states alter the state of the context at will.
