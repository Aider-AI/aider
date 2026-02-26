(binary_operator
    lhs: (identifier) @name
    operator: "<-"
    rhs: (function_definition)
) @definition.function

(binary_operator
    lhs: (identifier) @name
    operator: "="
    rhs: (function_definition)
) @definition.function

(call
    function: (identifier) @name
) @reference.call

(call
    function: (namespace_operator
        rhs: (identifier) @name
    )
) @reference.call
