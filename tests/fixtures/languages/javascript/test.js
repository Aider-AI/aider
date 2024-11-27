// Class definition
class Person {
    constructor(name) {
        this.name = name;
    }

    sayHello() {
        return `Hello, ${this.name}!`;
    }
}

// Function declaration
function greet(person) {
    return person.sayHello();
}

// Variables and constants
const DEFAULT_NAME = 'World';
let currentPerson = new Person(DEFAULT_NAME);

// Export for use in other modules
module.exports = {
    Person,
    greet,
    DEFAULT_NAME
};
