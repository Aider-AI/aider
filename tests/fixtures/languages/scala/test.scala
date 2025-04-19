package com.example.test

// A trait definition
trait Greeter {
  def greet(name: String): String
}

// A class definition with parameters
class FormalGreeter(prefix: String) extends Greeter {
  // A method definition
  override def greet(name: String): String = {
    s"$prefix, $name!"
  }
  
  // A val definition
  val defaultPrefix: String = "Hello"
  
  // A var definition
  var counter: Int = 0
}

// An object definition
object GreeterFactory {
  // A function definition
  def createGreeter(formal: Boolean): Greeter = {
    if (formal) {
      new FormalGreeter("Good day")
    } else {
      new CasualGreeter
    }
  }
  
  // A type definition
  type GreeterType = Greeter
}

// An enum definition
enum Greeting {
  // Simple enum cases
  case Hello, Hi, Hey
  
  // Full enum case with parameters
  case Custom(text: String)
}

// A class that uses generics
class Container[T](val value: T) {
  def map[U](f: T => U): Container[U] = new Container(f(value))
}

// A case class
case class Person(name: String, age: Int) {
  def introduce(): String = {
    val greeter = GreeterFactory.createGreeter(age > 30)
    greeter.greet(name) + s" I am $age years old."
  }
}

class CasualGreeter extends Greeter {
  override def greet(name: String): String = s"Hey, $name!"
}
