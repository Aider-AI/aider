;; Method and Function declarations
(contract_declaration (_
    (function_definition
        name: (identifier) @name) @definition.method))

(source_file
    (function_definition
        name: (identifier) @name) @definition.function)

;; Contract, struct, enum and interface declarations
(contract_declaration
  name: (identifier) @name) @definition.class

(interface_declaration
  name: (identifier) @name) @definition.interface

(library_declaration
  name: (identifier) @name) @definition.interface

(struct_declaration name: (identifier) @name) @definition.class
(enum_declaration name: (identifier) @name) @definition.class
(event_definition name: (identifier) @name) @definition.class

;; Function calls
(call_expression (expression (identifier)) @name ) @reference.call

(call_expression
    (expression (member_expression
        property: (_) @name ))) @reference.call

;; Log emit
(emit_statement name: (_) @name) @reference.class


;; Inheritance

(inheritance_specifier
    ancestor: (user_defined_type (_) @name . )) @reference.class


;; Imports ( note that unknown is not standardised )
(import_directive
  import_name: (_) @name ) @reference.unknown
