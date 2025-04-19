// Swift greeting example
class Greeter {
    let name: String
    
    init(name: String) {
        self.name = name
    }
    
    func greet() -> String {
        return "Hello, \(name)!"
    }
}

// Example usage
func exampleGreeting() {
    let greeter = Greeter(name: "World")
    print(greeter.greet())
}
