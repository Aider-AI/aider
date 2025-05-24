(list_lit
  meta: _*
  . (sym_lit name: (sym_name) @ignore)
  . (sym_lit name: (sym_name) @name.definition.method)
  (#match? @ignore "^def.*"))

(sym_lit name: (sym_name) @name.reference.call)
