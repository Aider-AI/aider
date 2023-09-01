(translation_unit
  (function_definition
    declarator: (function_declarator
      declarator: (identifier) @name.definition.function
    )
    body: (compound_statement) @body.function
  ) @definition.function

  (struct_specifier
    name: (type_identifier) @name.definition.struct
    body: (field_declaration_list) @body.struct
  ) @definition.struct

  (union_specifier
    name: (type_identifier) @name.definition.union
    body: (field_declaration_list) @body.union
  ) @definition.union

  (enum_specifier
    name: (type_identifier) @name.definition.enum
    body: (enumerator_list) @body.enum
  ) @definition.enum
)
