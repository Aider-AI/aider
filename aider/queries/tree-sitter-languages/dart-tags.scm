(class_definition
  name: (identifier) @name.definition.class) @definition.class

(method_signature
  (function_signature)) @definition.method

(type_alias
  (type_identifier) @name.definition.type) @definition.type

(method_signature
  (getter_signature
    name: (identifier) @name.definition.method)) @definition.method

(method_signature
  (setter_signature
    name: (identifier) @name.definition.method)) @definition.method

(method_signature
  (function_signature
  name: (identifier) @name.definition.method)) @definition.method

(method_signature
  (factory_constructor_signature
    (identifier) @name.definition.method)) @definition.method

(method_signature
  (constructor_signature
  name: (identifier) @name.definition.method)) @definition.method

(method_signature
  (operator_signature)) @definition.method

(method_signature) @definition.method

(mixin_declaration
  (mixin)
  (identifier) @name.definition.mixin) @definition.mixin

(extension_declaration
  name: (identifier) @name.definition.extension) @definition.extension

(enum_declaration
  name: (identifier) @name.definition.enum) @definition.enum

(function_signature
  name: (identifier) @name.definition.function) @definition.function

(new_expression
  (type_identifier) @name.reference.class) @reference.class

(initialized_variable_definition
  name: (identifier)
  value: (identifier) @name.reference.class
  value: (selector
	"!"?
	(argument_part
	  (arguments
	    (argument)*))?)?) @reference.class

(assignment_expression
  left: (assignable_expression
		  (identifier)
		  (unconditional_assignable_selector
			"."
			(identifier) @name.reference.call))) @reference.call

(assignment_expression
  left: (assignable_expression
		  (identifier)
		  (conditional_assignable_selector
			"?."
			(identifier) @name.reference.call))) @reference.call

((identifier) @name
 (selector
    "!"?
    (conditional_assignable_selector
      "?." (identifier) @name.reference.call)?
    (unconditional_assignable_selector
      "."? (identifier) @name.reference.call)?
    (argument_part
      (arguments
        (argument)*))?)*
	(cascade_section
	  (cascade_selector
		(identifier)) @name.reference.call
	  (argument_part
		(arguments
		  (argument)*))?)?) @reference.call


