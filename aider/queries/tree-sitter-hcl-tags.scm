; variable definition
(
  (block
    (identifier) @block_type
    (string_lit
      (template_literal) @name.definition.variable
      )
    (body) @definition.variable
    )
  (#eq? @block_type "variable")
  )

; variable reference
(
  ((variable_expr) @ref_type
    (get_attr (identifier) @name.reference.variable)) @reference.variable
  (#eq? @ref_type "var")
  )

; module definition
(
  (block
    (identifier) @block_type
    (string_lit
      (template_literal) @name.definition.module
      )
    )
  (#eq? @block_type "module")
  )

; module reference
(
  ((variable_expr) @ref_type
    (get_attr (identifier) @name.reference.module)) @reference.module
  (#eq? @ref_type "module")
  )

; resource definition
(
  (block
    (identifier) @block_type
    (string_lit
      (template_literal) @resource_type
      )
    (string_lit
      (template_literal) @name.definition.resource
      )
    (body) @definition.resource
    )
  (#eq? @block_type "resource")
  )

; resource reference
(
  ((variable_expr) @ref_type
    (get_attr
      (get_attr (identifier) @resource_type)
      (identifier) @name.reference.resource
      )) @reference.resource
  (#eq? @ref_type "resource")
  )

; output definition
(
  (block
    (identifier) @block_type
    (string_lit
      (template_literal) @name.definition.output
      )
    (body) @definition.output
    )
  (#eq? @block_type "output")
  )

; output reference
(
  ((variable_expr) @ref_type
    (get_attr (identifier) @name.reference.output)) @reference.output
  (#eq? @ref_type "output")
  )
