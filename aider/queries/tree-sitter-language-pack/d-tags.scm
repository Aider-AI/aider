(module_def (module_declaration (module_fqn) @name)) @definition.module

(struct_declaration (struct) . (identifier) @name) @definition.class
(interface_declaration (interface) . (identifier) @name) @definition.interface
(enum_declaration (enum) . (identifier) @name) @definition.type

(class_declaration (class) . (identifier) @name) @definition.class
(constructor (this) @name) @definition.method
(destructor (this) @name) @definition.method
(postblit (this) @name) @definition.method

(manifest_declarator . (identifier) @name) @definition.type

(function_declaration (identifier) @name) @definition.function

(union_declaration (union) . (identifier) @name) @definition.type

(anonymous_enum_declaration (enum_member . (identifier) @name)) @definition.constant

(enum_declaration (enum_member . (identifier) @name)) @definition.constant

(call_expression (identifier) @name) @reference.call
(call_expression (type (template_instance (identifier) @name))) @reference.call
(parameter (type (identifier) @name) @reference.class (identifier))

(variable_declaration (type (identifier) @name) @reference.class (declarator))
