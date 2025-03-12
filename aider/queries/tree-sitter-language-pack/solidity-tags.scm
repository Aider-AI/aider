;; Method and Function declarations
(contract_declaration (_
    (function_definition
        name: (identifier) @name.definition.function) @definition.method))

(source_file
    (function_definition
        name: (identifier) @name.definition.function) @definition.function)

;; Contract, struct, enum and interface declarations
(contract_declaration
  name: (identifier) @name.definition.class) @definition.class

(interface_declaration
  name: (identifier) @name.definition.interface) @definition.interface

(library_declaration
  name: (identifier) @name.definition.class) @definition.interface

(struct_declaration name: (identifier) @name.definition.class) @definition.class
(enum_declaration name: (identifier) @name.definition.class) @definition.class
(event_definition name: (identifier) @name.definition.class) @definition.class

;; Function calls
(call_expression (expression (identifier)) @name.reference.call ) @reference.call

(call_expression
    (expression (member_expression
        property: (_) @name.reference.method ))) @reference.call

;; Log emit
(emit_statement name: (_) @name.reference.class) @reference.class


;; Inheritance

(inheritance_specifier
    ancestor: (user_defined_type (_) @name.reference.class . )) @reference.class


;; Imports ( note that unknown is not standardised )
(import_directive
  import_name: (_) @name.reference.module ) @reference.unknown
