(function_declaration
  name: [
    (identifier) @name.definition.function
    (dot_index_expression
      field: (identifier) @name.definition.function)
  ]) @definition.function

(function_declaration
  name: (method_index_expression
    method: (identifier) @name.definition.method)) @definition.method

(assignment_statement
  (variable_list .
    name: [
      (identifier) @name.definition.function
      (dot_index_expression
        field: (identifier) @name.definition.function)
    ])
  (expression_list .
    value: (function_definition))) @definition.function

(table_constructor
  (field
    name: (identifier) @name.definition.function
    value: (function_definition))) @definition.function

(function_call
  name: [
    (identifier) @name.reference.call
    (dot_index_expression
      field: (identifier) @name.reference.call)
    (method_index_expression
      method: (identifier) @name.reference.method)
  ]) @reference.call
