(class_declaration
  name: (name) @name.definition.class) @definition.class

(function_definition
  name: (name) @name.definition.function) @definition.function

(method_declaration
  name: (name) @name.definition.function) @definition.function

(object_creation_expression
  [
    (qualified_name (name) @name.reference.class)
    (variable_name (name) @name.reference.class)
  ]) @reference.class

(function_call_expression
  function: [
    (qualified_name (name) @name.reference.call)
    (variable_name (name)) @name.reference.call
  ]) @reference.call

(scoped_call_expression
  name: (name) @name.reference.call) @reference.call

(member_call_expression
  name: (name) @name.reference.call) @reference.call

(namespace_use_declaration
  (namespace_use_clause (qualified_name) @name.reference.import)) @reference.import

(require_expression (string) @name.reference.import) @reference.import
(include_expression (string) @name.reference.import) @reference.import