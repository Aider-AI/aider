import std.stdio;

/**
 * Main function for the D language test file.
 */
void main() {
    writeln("Hello, D language!");
    
    auto greeter = new Greeter("World");
    writeln(greeter.greet());
}

/**
 * A simple greeter class in D
 */
class Greeter {
    private string name;
    
    this(string name) {
        this.name = name;
    }
    
    string greet() {
        return "Hello, " ~ name ~ "!";
    }
}
