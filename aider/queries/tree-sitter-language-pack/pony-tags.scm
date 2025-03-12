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

(class_definition (identifier) @name) @definition.class
(actor_definition (identifier) @name) @definition.class
(primitive_definition (identifier) @name) @definition.class
(struct_definition (identifier) @name) @definition.class
(type_alias (identifier) @name) @definition.class

(trait_definition (identifier) @name) @definition.interface
(interface_definition (identifier) @name) @definition.interface

(constructor (identifier) @name) @definition.method
(method (identifier) @name) @definition.method
(behavior (identifier) @name) @definition.method

(class_definition (type) @name) @reference.implementation
(actor_definition (type) @name) @reference.implementation
(primitive_definition (type) @name) @reference.implementation
(struct_definition (type) @name) @reference.implementation
(type_alias (type) @name) @reference.implementation

; calls - not catching all possible call cases of callees for capturing the method name
(call_expression callee: [(identifier) (ffi_identifier)] @name) @reference.call
(call_expression callee: (generic_expression [(identifier) (ffi_identifier)] @name)) @reference.call
(call_expression callee: (member_expression (identifier) @name .)) @reference.call
(call_expression callee: (member_expression (generic_expression [(identifier) (ffi_identifier)] @name) .)) @reference.call
; TODO: add more possible callee expressions
(call_expression) @reference.call
