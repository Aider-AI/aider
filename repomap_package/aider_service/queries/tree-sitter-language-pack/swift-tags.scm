(class_declaration
  name: (type_identifier) @name.definition.class) @definition.class

(protocol_declaration
  name: (type_identifier) @name.definition.interface) @definition.interface

(class_declaration
    (class_body
        [
            (function_declaration
                name: (simple_identifier) @name.definition.method
            )
            (subscript_declaration
                (parameter (simple_identifier) @name.definition.method)
            )
            (init_declaration "init" @name.definition.method)
            (deinit_declaration "deinit" @name.definition.method)
        ]
    )
) @definition.method

(protocol_declaration
    (protocol_body
        [
            (protocol_function_declaration
                name: (simple_identifier) @name.definition.method
            )
            (subscript_declaration
                (parameter (simple_identifier) @name.definition.method)
            )
            (init_declaration "init" @name.definition.method)
        ]
    )
) @definition.method

(class_declaration
    (class_body
        [
            (property_declaration
                (pattern (simple_identifier) @name.definition.property)
            )
        ]
    )
) @definition.property

(property_declaration
    (pattern (simple_identifier) @name.definition.property)
) @definition.property

(function_declaration
    name: (simple_identifier) @name.definition.function) @definition.function
