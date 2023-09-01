(translation_unit
  (function_definition
    declarator: (function_declarator
      declarator: (identifier) @name.definition.function
    )
  ) @definition.function

  (struct_specifier
    name: (type_identifier) @name.definition.struct
  ) @definition.struct

  (union_specifier
    name: (type_identifier) @name.definition.union
  ) @definition.union

  (enum_specifier
    name: (type_identifier) @name.definition.enum
  ) @definition.enum
)
