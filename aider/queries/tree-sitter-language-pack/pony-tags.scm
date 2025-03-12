;Class definitions 	@definition.class
;Function definitions 	@definition.function
;Interface definitions 	@definition.interface
;Method definitions 	@definition.method
;Module definitions 	@definition.module
;Function/method calls 	@reference.call
;Class reference 	@reference.class
;Interface implementation 	@reference.implementation
(
  (identifier) @reference.class
  (#match? @reference.class "^_*[A-Z][a-zA-Z0-9_]*$")
)

(class_definition (identifier) @name.definition.class) @definition.class
(actor_definition (identifier) @name.definition.class) @definition.class
(primitive_definition (identifier) @name.definition.class) @definition.class
(struct_definition (identifier) @name.definition.class) @definition.class
(type_alias (identifier) @name.definition.class) @definition.class

(trait_definition (identifier) @name.definition.interface) @definition.interface
(interface_definition (identifier) @name.definition.interface) @definition.interface

(constructor (identifier) @name.definition.method) @definition.method
(method (identifier) @name.definition.method) @definition.method
(behavior (identifier) @name.definition.method) @definition.method

(class_definition (type) @name.reference.implementation) @reference.implementation
(actor_definition (type) @name.reference.implementation) @reference.implementation
(primitive_definition (type) @name.reference.implementation) @reference.implementation
(struct_definition (type) @name.reference.implementation) @reference.implementation
(type_alias (type) @name.reference.implementation) @reference.implementation

; calls - not catching all possible call cases of callees for capturing the method name
(call_expression callee: [(identifier) (ffi_identifier)] @name.reference.call) @reference.call
(call_expression callee: (generic_expression [(identifier) (ffi_identifier)] @name.reference.call)) @reference.call
(call_expression callee: (member_expression (identifier) @name.reference.call .)) @reference.call
(call_expression callee: (member_expression (generic_expression [(identifier) (ffi_identifier)] @name.reference.call) .)) @reference.call
; TODO: add more possible callee expressions
(call_expression) @reference.call
