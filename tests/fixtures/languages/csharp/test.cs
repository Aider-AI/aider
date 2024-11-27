using System;
using System.Collections.Generic;

namespace Greetings {
    public interface IGreeter {
        string Greet(string name);
    }

    public class Person {
        public string Name { get; set; }
        public int Age { get; set; }

        public Person(string name, int age) {
            Name = name;
            Age = age;
        }
    }

    public class FormalGreeter : IGreeter {
        private const string PREFIX = "Good day";
        private static readonly int MAX_AGE = 150;

        public string Greet(string name) {
            return $"{PREFIX}, {name}!";
        }

        public string GreetPerson(Person person) {
            return $"{PREFIX}, {person.Name} ({person.Age})!";
        }
    }

    public class Program {
        static void Main() {
            var greeter = new FormalGreeter();
            var person = new Person("World", 42);
            Console.WriteLine(greeter.GreetPerson(person));
        }
    }
}
