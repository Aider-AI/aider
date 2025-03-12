// A simple Dart class for testing ctags detection
class Person {
  String name;
  int age;

  Person(this.name, this.age);

  void greet() {
    print('Hello, my name is $name and I am $age years old.');
  }

  bool isAdult() {
    return age >= 18;
  }
}

void main() {
  var person = Person('John', 30);
  person.greet();
  print('Is adult: ${person.isAdult()}');
}
