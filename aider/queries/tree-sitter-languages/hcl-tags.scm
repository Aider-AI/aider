;; Based on https://github.com/tree-sitter-grammars/tree-sitter-hcl/blob/main/make_grammar.js
;; Which has Apache 2.0 License
;; tags.scm for Terraform (tree-sitter-hcl)

; === Definitions: Terraform Blocks ===
(block 
  (identifier) @block_type
  (string_lit (template_literal) @resource_type)
  (string_lit (template_literal) @name.definition.resource)
  (body) @definition.resource
) (#eq? @block_type "resource")

(block 
  (identifier) @block_type
  (string_lit (template_literal) @name.definition.module)
  (body) @definition.module
) (#eq? @block_type "module")

(block 
  (identifier) @block_type
  (string_lit (template_literal) @name.definition.variable)
  (body) @definition.variable
) (#eq? @block_type "variable")

(block 
  (identifier) @block_type
  (string_lit (template_literal) @name.definition.output)
  (body) @definition.output
) (#eq? @block_type "output")

(block 
  (identifier) @block_type
  (string_lit (template_literal) @name.definition.provider)
  (body) @definition.provider
) (#eq? @block_type "provider")

(block 
  (identifier) @block_type
  (body 
    (attribute 
       (identifier) @name.definition.local 
       (expression) @definition.local
    )+
  )
) (#eq? @block_type "locals")

; === References: Variables, Locals, Modules, Data, Resources ===
((variable_expr) @ref_type
  (get_attr (identifier) @name.reference.variable)
) @reference.variable
 (#eq? @ref_type "var")

((variable_expr) @ref_type
  (get_attr (identifier) @name.reference.local)
) @reference.local
 (#eq? @ref_type "local")

((variable_expr) @ref_type
  (get_attr (identifier) @name.reference.module)
) @reference.module
 (#eq? @ref_type "module")

((variable_expr) @ref_type
  (get_attr (identifier) @data_source_type)
  (get_attr (identifier) @name.reference.data)
) @reference.data
 (#eq? @ref_type "data")

((variable_expr) @resource_type
  (get_attr (identifier) @name.reference.resource)
) @reference.resource
 (#not-eq? @resource_type "var")
 (#not-eq? @resource_type "local")
 (#not-eq? @resource_type "module")
 (#not-eq? @resource_type "data")
 (#not-eq? @resource_type "provider")
 (#not-eq? @resource_type "output")
