; Modules
(module) @name @reference.module
(import alias: (identifier) @name) @reference.module
(remote_type_identifier
  module: (identifier) @name) @reference.module
((field_access
  record: (identifier) @name)
 (#is-not? local)) @reference.module

; Functions
(function
  name: (identifier) @name) @definition.function
(external_function
  name: (identifier) @name) @definition.function
(unqualified_import (identifier) @name) @reference.function
((function_call
   function: (identifier) @name) @reference.function
 (#is-not? local))
((field_access
  record: (identifier) @ignore
  field: (label) @name)
 (#is-not? local)) @reference.function
((binary_expression
   operator: "|>"
   right: (identifier) @name)
 (#is-not? local)) @reference.function

; Types
(type_definition
  (type_name
    name: (type_identifier) @name)) @definition.type
(type_definition
  (data_constructors
    (data_constructor
      name: (constructor_name) @name))) @definition.constructor
(external_type
  (type_name
    name: (type_identifier) @name)) @definition.type

(type_identifier) @name @reference.type
(constructor_name) @name @reference.constructor
