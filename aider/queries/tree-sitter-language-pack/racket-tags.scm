(list
  .
  (symbol) @reference._define
  (#match? @reference._define "^(define|define/contract)$")
  .
  (list
    .
    (symbol) @name) @definition.function)

(list
  .
  (symbol) @reference.call)
