; Modules
(module) @name.reference.module @reference.module
(import alias: (identifier) @name.reference.module) @reference.module
(remote_type_identifier
  module: (identifier) @name.reference.module) @reference.module
((field_access
  record: (identifier) @name.reference.module)
 (#is-not? local)) @reference.module

; Functions
(function
  name: (identifier) @name.definition.function) @definition.function
(external_function
  name: (identifier) @name.definition.function) @definition.function
(unqualified_import (identifier) @name.reference.function) @reference.function
((function_call
   function: (identifier) @name.reference.function) @reference.function
 (#is-not? local))
((field_access
  record: (identifier) @ignore
  field: (label) @name.reference.function)
 (#is-not? local)) @reference.function
((binary_expression
   operator: "|>"
   right: (identifier) @name.reference.function)
 (#is-not? local)) @reference.function

; Types
(type_definition
  (type_name
    name: (type_identifier) @name.definition.type)) @definition.type
(type_definition
  (data_constructors
    (data_constructor
      name: (constructor_name) @name.definition.constructor))) @definition.constructor
(external_type
  (type_name
    name: (type_identifier) @name.definition.type)) @definition.type

(type_identifier) @name.reference.type @reference.type
(constructor_name) @name.reference.constructor @reference.constructor
