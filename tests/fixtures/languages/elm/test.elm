module Main exposing (main, Person, Greeting)

import Html exposing (Html, div, text)
import Html.Attributes exposing (class)

type alias Person =
    { name : String
    , age : Int
    }

type Greeting
    = Formal
    | Casual

greet : Greeting -> Person -> String
greet style person =
    let
        prefix =
            case style of
                Formal ->
                    "Good day"

                Casual ->
                    "Hi"
    in
    prefix ++ ", " ++ person.name ++ "!"

defaultPerson : Person
defaultPerson =
    { name = "World"
    , age = 42
    }

main : Html msg
main =
    div [ class "greeting" ]
        [ text (greet Formal defaultPerson)
        ]
module Main exposing (..)

-- Define a Person type
type alias Person =
    { name : String
    , age : Int
    }

-- Create a person
newPerson : String -> Int -> Person
newPerson name age =
    { name = name
    , age = age
    }

-- Main function
main =
    let
        person = newPerson "John Doe" 30
    in
    text ("Hello, " ++ person.name)
