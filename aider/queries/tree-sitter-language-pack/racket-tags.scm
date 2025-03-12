(list
  .
  (symbol) @reference._define
  (#match? @reference._define "^(define|define/contract)$")
  .
  (list
    .
    (symbol) @name.definition.function) @definition.function)

(list
  .
  (symbol) @name.reference.call)
