package main

import (
    "fmt"
    "strings"
)

// Person represents someone who can be greeted
type Person struct {
    Name string
    Age  int
}

// Greeter defines greeting behavior
type Greeter interface {
    Greet(p Person) string
}

// FormalGreeter implements Greeter with formal style
type FormalGreeter struct {
    Prefix string
}

const (
    DefaultName = "World"
    MaxAge     = 150
)

func (g FormalGreeter) Greet(p Person) string {
    return fmt.Sprintf("%s, %s! You are %d years old.",
        g.Prefix, p.Name, p.Age)
}

func NewFormalGreeter() *FormalGreeter {
    return &FormalGreeter{Prefix: "Good day"}
}

func main() {
    greeter := NewFormalGreeter()
    person := Person{Name: DefaultName, Age: 42}
    fmt.Println(greeter.Greet(person))
}
