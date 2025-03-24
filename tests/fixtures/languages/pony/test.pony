class Greeter
  fun greet(name: String): String =>
    "Hello, " + name + "!"

actor Main
  new create(env: Env) =>
    let greeter = Greeter
    env.out.print(greeter.greet("Pony"))
