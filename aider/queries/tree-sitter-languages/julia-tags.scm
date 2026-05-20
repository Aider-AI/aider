;; derived from: https://github.com/tree-sitter/tree-sitter-julia
;; License: MIT

(module_definition
  name: (identifier) @name.definition.module) @definition.module

(struct_definition
  (type_head
    (identifier) @name.definition.class)) @definition.class

(struct_definition
  (type_head
    (binary_expression
      (identifier) @name.definition.class))) @definition.class

(abstract_definition
  (type_head
    (identifier) @name.definition.class)) @definition.class

(abstract_definition
  (type_head
    (binary_expression
      (identifier) @name.definition.class))) @definition.class

(function_definition
  (signature
    (call_expression
      (identifier) @name.definition.function))) @definition.function

(function_definition
  (signature
    (identifier) @name.definition.function)) @definition.function

(assignment
  (call_expression
    (identifier) @name.definition.function)) @definition.function

(macro_definition
  (signature
    (call_expression
      (identifier) @name.definition.macro))) @definition.macro

(macro_definition
  (signature
    (identifier) @name.definition.macro)) @definition.macro

(call_expression
  (identifier) @name.reference.call) @reference.call

(const_statement
  (assignment
    (identifier) @name.definition.constant)) @definition.constant

(export_statement
  (identifier) @name.reference.export) @reference.export

(using_statement
  (identifier) @name.reference.module) @reference.module

(import_statement
  (identifier) @name.reference.module) @reference.module
