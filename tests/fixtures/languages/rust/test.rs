// Define a trait
trait Greeting {
    fn greet(&self) -> String;
}

// Define a struct
struct Person {
    name: String,
    age: u32,
}

// Implement the trait for Person
impl Greeting for Person {
    fn greet(&self) -> String {
        format!("Hello, {}! You are {} years old.", self.name, self.age)
    }
}

// Implementation block for Person
impl Person {
    fn new(name: String, age: u32) -> Self {
        Person { name, age }
    }
}

// Constants
const DEFAULT_NAME: &str = "World";
const MAX_AGE: u32 = 150;

fn main() {
    let person = Person::new(DEFAULT_NAME.to_string(), 30);
    println!("{}", person.greet());
}
