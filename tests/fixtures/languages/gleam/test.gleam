import gleam/io

pub fn greet(name: String) -> String {
  "Hello, " <> name <> "!"
}

pub fn main() {
  greet("World")
  |> io.println
}
