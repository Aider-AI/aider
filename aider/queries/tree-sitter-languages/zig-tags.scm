; Functions
(fn_proto
  name: (identifier) @name.definition.function)

; Structs, Enums, Unions and Opaque types
(var_decl
  name: (identifier) @name.definition.class
  value: (container_decl))

; Tests
(test_decl
  name: (string_literal) @name.definition.test)
