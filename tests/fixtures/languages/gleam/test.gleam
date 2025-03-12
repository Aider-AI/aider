import gleam/io

pub fn greeter(name) {
  io.println("Hello, " <> name <> "!")
}
