; Functions
(function_declaration
  name: (identifier) @name.definition.function)

; Structs, Enums, Unions and Opaque types
(variable_declaration
  name: (identifier) @name.definition.class
  value: [
    (struct_declaration)
    (enum_declaration)
    (union_declaration)
    (opaque_declaration)
  ])

; Tests
(test_declaration
  name: (string) @name.definition.test)
