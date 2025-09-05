;; derived from: https://github.com/tree-sitter/tree-sitter-julia
;; License: MIT

(module
  name: (identifier) @name.definition.module) @definition.module

(module
  name: (scoped_identifier) @name.definition.module) @definition.module

(struct_definition
  name: (type_identifier) @name.definition.class) @definition.class

(mutable_struct_definition
  name: (type_identifier) @name.definition.class) @definition.class

(abstract_type_declaration
  name: (type_identifier) @name.definition.class) @definition.class

(constant_assignment
  left: (identifier) @name.definition.class) @definition.class

(function_definition
  name: (identifier) @name.definition.function) @definition.function

(function_definition
  name: (scoped_identifier) @name.definition.function) @definition.function

(assignment
  left: (call_expression
          function: (identifier) @name.definition.function)) @definition.function

(method_definition
  name: (identifier) @name.definition.method) @definition.method

(macro_definition
  name: (identifier) @name.definition.macro) @definition.macro

(macro_call
  name: (identifier) @name.reference.call) @reference.call

(call_expression
  function: (identifier) @name.reference.call) @reference.call

(call_expression
  function: (scoped_identifier) @name.reference.call) @reference.call

(type_expression
  name: (type_identifier) @name.reference.type) @reference.type

(constant_assignment
  left: (identifier) @name.definition.constant) @definition.constant

(export_statement
  (identifier) @name.reference.export) @reference.export

(using_statement
  (identifier) @name.reference.module) @reference.module

(import_statement
  (identifier) @name.reference.module) @reference.module
