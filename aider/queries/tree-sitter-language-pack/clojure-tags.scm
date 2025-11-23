(list_lit
  meta: _*
  . (sym_lit name: (sym_name) @ignore)
  . (sym_lit name: (sym_name) @name.definition.method)
  (#match? @ignore "^def.*"))

(sym_lit name: (sym_name) @name.reference.call)

(list_lit
 . (sym_lit name: (sym_name) @import_call)
 . (sym_lit name: (sym_name) @name.reference.import)
 (#match? @import_call "^(require|use)$")) @reference.import