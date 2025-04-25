;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;; Function Definitions ;;;;;;;;;;;;;;;;;;;;;;;

(defun_header
  function_name: (sym_lit) @name.definition.function) @definition.function

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;; Function Calls ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;;
;;; Basically, we consider every list literal with symbol as the
;;; first element to be a call to a function named by that element.
;;; But we must exclude some cases. Note, tree-sitter @ignore
;;; cases only work if they are declared before the cases
;;; we want to include.

;; Exclude lambda lists for function definitions
;; For example:
;;
;;    (defun my-func (arg1 arg2) ...)
;;
;; do not treat (arg1 arg2) as a call of function arg1
;;
(defun_header
  lambda_list: (list_lit . [(sym_lit) (package_lit)] @ignore))

;; Similar to the above, but for
;;
;;     (defmethod m ((type1 param1) (type2 param2)) ...)
;;
;; where list literals having symbol as their first element
;; are nested inside the lambda list.
(defun_header
  lambda_list: (list_lit (list_lit . [(sym_lit) (package_lit)] @ignore)))

;;
;;      (let ((var ...) (var2 ...)) ...)
;;
;; - exclude var, var2
;; - the same for let*, flet, labels, macrolet, symbol-macrolet
(list_lit . [(sym_lit) (package_lit)] @name.reference.call
          . (list_lit (list_lit . [(sym_lit) (package_lit)] @ignore))
          (#match? @name.reference.call
                   "(?i)^(cl:)?(let|let\\*|flet|labels|macrolet|symbol-macrolet)$")
  )

;; TODO:
;;     - exclude also:
;;       - (defclass name (parent parent2)
;;           ((slot1 ...)
;;            (slot2 ...))
;;              exclude the parent, slot1, slot2
;;       - (flet ((func-1 (param1 param2))) ...)
;;           - we already exclude func-1, but param1 is still recognized
;;             as a function call - exclude it too
;;           - the same for labels
;;           - the same macrolet
;;       - what else?
;;         (that's a non-goal to completely support all macros
;;          and special operators, but every one we support
;;          makes the solution a little bit better)
;;     - (flet ((func-1 (param1 param2))) ...)
;;       - instead of simply excluding it, as we do today,
;;         tag func-1 as @local.definition.function (I suppose)
;;       - the same for labels, macrolet
;;     - @local.scope for let, let*, flet, labels, macrolet
;;       - I guess the whole span of the scope text,
;;         till the closing paren, should be tagged as @local.scope;
;;         Hopefully, combined with @local.definition.function
;;         within the scope, the usual  @reference.call within
;;         that scope will refer to the local definition,
;;         and there will be no need to use @local.reference.call
;;         (which is more difficult to implement).
;;       - When implementing, remember the scope rules differences
;;         of let vs let*, flet vs labels.


;; Include all other cases - list literal with symbol as the
;; first element
(list_lit . [(sym_lit) (package_lit)] @name.reference.call) @reference.call

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;; classes

(list_lit . [(sym_lit) (package_lit)] @ignore
          . [(sym_lit) (package_lit)] @name.definition.class
  (#match? @ignore "(?i)^(cl:)?defclass$")
          ) @definition.class

(list_lit . [(sym_lit) (package_lit)] @ignore
          . (quoting_lit [(sym_lit) (package_lit)] @name.reference.class)
  (#match? @ignore "(?i)^(cl:)?make-instance$")
          ) @reference.class

;;; TODO:
;;  - @reference.class for base classes

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;; TODO:
;; - Symbols referenced in defpackage
;;
;;       (defpackage ...
;;         (:export (symbol-a :symbol-b #:symbol-c "SYMBOL-D")))
;;
;;   The goal is to allow quick navigation from the API
;;   overview in the form of defpackage, to the definition
;;   where user can read parameters, docstring, etc.
;;   - The @name must not include the colon, or sharpsign colon, quotes,
;;     just symbol-a, symbol-b, symbol-c, sybmol-d
;;   - Downcase the names specified as string literals?
;;     ("SYMBOL-D" -> symbol-d)
;;   - We don't know if the exported symbol is a function, variable,
;;     class or something else. The official doc
;;     (https://tree-sitter.github.io/tree-sitter/code-navigation-systems)
;;     does not even suggest a tag for variable reference.
;;     (Although in practice, the `tree-sitter tags` command
;;     allows any @reference.* and @definition.* tags)
;;     Probably it's better to just use @reference.call for all
;;     the symbols in the :export clause.
;;
;; - The same for the export function call:
;; 
;;       (export '(symbol-a :symbol-b #:symbol-c "SYMBOL-D"))
