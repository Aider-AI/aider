#!/usr/bin/env bash

GREETING="hello"

greet() {
    local name=$1
    echo "$GREETING, $name"
}

say_hi() {
    greet "world"
}

main() {
    say_hi
    greet "$USER"
}

main "$@"
