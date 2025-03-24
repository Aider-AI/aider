(binary_operator
    lhs: (identifier) @name.definition.function
    operator: "<-"
    rhs: (function_definition)
) @definition.function

(binary_operator
    lhs: (identifier) @name.definition.function
    operator: "="
    rhs: (function_definition)
) @definition.function

(call
    function: (identifier) @name.reference.call
) @reference.call

(call
    function: (namespace_operator
        rhs: (identifier) @name.reference.call
    )
) @reference.call
