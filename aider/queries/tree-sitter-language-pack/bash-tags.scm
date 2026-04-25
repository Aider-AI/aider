; Bash / shell script function definitions.
; Matches both POSIX-style `name() { ... }` and keyword-style
; `function name() { ... }` / `function name { ... }`.

(function_definition
  name: (word) @name.definition.function) @definition.function
