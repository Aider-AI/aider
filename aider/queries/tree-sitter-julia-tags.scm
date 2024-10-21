;; ignored variable name. TODO replace with _?
(define UNUSED '|#unused#|)

;; pass 1: syntax desugaring

;; allow (:: T) => (:: #gensym T) in formal argument lists
(define (fill-missing-argname a unused)
  (if (and (pair? a) (eq? (car a) '|::|) (null? (cddr a)))
      `(|::| ,(if unused UNUSED (gensy)) ,(cadr a))
      a))
(define (fix-arglist l (unused #t))
  (if (any vararg? (butlast l))
      (error "invalid \"...\" on non-final argument"))
  (map (lambda (a)
         (cond ((and (pair? a) (eq? (car a) 'kw))
                `(kw ,(fill-missing-argname (cadr a) unused) ,(caddr a)))
               ((and (pair? a) (eq? (car a) '...))
                `(... ,(fill-missing-argname (cadr a) unused)))
               (else
                (fill-missing-argname a unused))))
       l))

;; expanding comparison chains: (comparison a op b op c ...)

;; accumulate a series of comparisons, with the given "and" constructor,
;; exit criteria, and "take" function that consumes part of a list,
;; returning (expression . rest)
(define (comp-accum e make-and done? take)
  (let loop ((e e)
             (expr '()))
    (if (done? e) (cons expr e)
        (let ((ex_rest (take e)))
          (loop (cdr ex_rest)
                (if (null? expr)
                    (car ex_rest)
                    (make-and expr (car ex_rest))))))))

(define (add-init arg arg2 expr)
  (if (eq? arg arg2) expr
      `(block (= ,arg2 ,arg) ,expr)))

;; generate first comparison call, converting e.g. (a < b < c)
;; to ((call < a b) b < c)
(define (compare-one e)
  (let* ((arg   (caddr e))
         (arg2  (if (and (pair? arg)
                         (pair? (cdddr e)))
                    (make-ssavalue) arg)))
    (if (and (not (dotop-named? (cadr e)))
             (length> e 5)
             (pair? (cadddr (cdr e)))
             (dotop-named? (cadddr (cddr e))))
        ;; look ahead: if the 2nd argument of the next comparison is also
        ;; an argument to an eager (dot) op, make sure we don't skip the
        ;; initialization of its variable by short-circuiting
        (let ((s (make-ssavalue)))
          (cons `(block
                  ,@(if (eq? arg arg2) '() `((= ,arg2 ,arg)))
                  (= ,s ,(cadddr (cdr e)))
                  (call ,(cadr e) ,(car e) ,arg2))
                (list* arg2 (cadddr e) s (cddddr (cdr e)))))
        (cons
         (add-init arg arg2
                   `(call ,(cadr e) ,(car e) ,arg2))
         (cons arg2 (cdddr e))))))

;; convert a series of scalar comparisons into && expressions
(define (expand-scalar-compare e)
  (comp-accum e
              (lambda (a b) `(&& ,a ,b))
              (lambda (x) (or (not (length> x 2)) (dotop-named? (cadr x))))
              compare-one))

;; convert a series of scalar and vector comparisons into & calls,
;; combining as many scalar comparisons as possible into short-circuit
;; && sequences.
(define (expand-vector-compare e)
  (comp-accum e
              (lambda (a b) `(call .& ,a ,b))
              (lambda (x) (not (length> x 2)))
              (lambda (e)
                (if (dotop-named? (cadr e))
                    (compare-one e)
                    (expand-scalar-compare e)))))

(define (expand-compare-chain e)
  (car (expand-vector-compare e)))

;; return the appropriate computation for a `begin` or `end` symbol for indexing
;; the array `a` in the `n`th index.
;; `tuples` are a list of the splatted arguments that precede index `n`
;; `last` = is this last index?
;; returns a call to lastindex(a) or lastindex(a,n)
(define (end-val a n tuples last)
  (if (null? tuples)
      (if (and last (= n 1))
          `(call (top lastindex) ,a)
          `(call (top lastindex) ,a ,n))
      (let ((dimno `(call (top +) ,(- n (length tuples))
                          ,.(map (lambda (t) `(call (top length) ,t))
                                 tuples))))
            `(call (top lastindex) ,a ,dimno))))

(define (begin-val a n tuples last)
  (if (null? tuples)
      (if (and last (= n 1))
          `(call (top firstindex) ,a)
          `(call (top firstindex) ,a ,n))
      (let ((dimno `(call (top +) ,(- n (length tuples))
                          ,.(map (lambda (t) `(call (top length) ,t))
                                 tuples))))
            `(call (top first) (call (top axes) ,a ,dimno)))))

;; replace `begin` and `end` for the closest ref expression, so doesn't go inside nested refs
(define (replace-beginend ex a n tuples last)
  (cond ((eq? ex 'end)                (end-val a n tuples last))
        ((eq? ex 'begin)              (begin-val a n tuples last))
        ((or (atom? ex) (quoted? ex)) ex)
        ((eq? (car ex) 'ref)
         ;; inside ref only replace within the first argument
         (list* 'ref (replace-beginend (cadr ex) a n tuples last)
                (cddr ex)))
        ;; TODO: this probably should not be allowed since keyword args aren't
        ;; positional, but in this context we have just used their positions anyway
        ((eq? (car ex) 'kw)
         (list 'kw (cadr ex) (replace-beginend (caddr ex) a n tuples last)))
        (else
         (cons (car ex)
               (map (lambda (x) (replace-beginend x a n tuples last))
                    (cdr ex))))))

;; go through indices and replace the `begin` or `end` symbol
;; a = array being indexed, i = list of indices
;; returns (values index-list stmts) where stmts are statements that need
;; to execute first.
(define (process-indices a i)
  (let ((has-va? (any vararg? i)))
    (let loop ((lst i)
               (n   1)
               (stmts '())
               (tuples '())
               (ret '()))
      (if (null? lst)
          (values (reverse ret) (reverse stmts))
          (let* ((idx0 (car lst))
                 (idx  (if (vararg? idx0) (cadr idx0) idx0))
                 (last (null? (cdr lst)))
                 (replaced (replace-beginend idx a n tuples last))
                 (val      (if (kwarg? replaced) (caddr replaced) replaced))
                 (idx      (if (or (not has-va?) (simple-atom? val))
                               val (make-ssavalue))))
            (loop (cdr lst) (+ n 1)
                  (if (eq? idx val)
                      stmts
                      (cons `(= ,idx ,val)
                            stmts))
                  (if (vararg? idx0) (cons idx tuples) tuples)
                  (cons (if (vararg? idx0)
                            `(... ,idx)
                            (if (eq? val replaced)
                                idx
                                (list 'kw (cadr replaced) idx)))
                        ret)))))))

;; GF method does not need to keep decl expressions on lambda args
;; except for rest arg
(define (method-lambda-expr argl body rett)
  (let ((argl (map (lambda (x)
                     (let ((n (arg-name x)))
                       (if (underscore-symbol? n) UNUSED n)))
                   argl))
        (body (blockify body)))
    `(lambda ,argl ()
             (scope-block
              ,(if (equal? rett '(core Any))
                   body
                   (let ((meta (take-while (lambda (x) (and (pair? x)
                                                            (memq (car x) '(lineinfo line meta))))
                                           (cdr body)))
                         (R (make-ssavalue)))
                     `(,(car body) ,@meta
                       (= ,R ,rett)
                       (meta ret-type ,R)
                       ,@(list-tail body (+ 1 (length meta))))))))))

;; convert x<:T<:y etc. exprs into (name lower-bound upper-bound)
;; a bound is #f if not specified
(define (analyze-typevar e)
  (define (check-sym s)
    (if (symbol? (unescape s)) ; unescape for macroexpand.scm use
        s
        (error (string "invalid type parameter name \"" (deparse s) "\""))))
  (cond ((atom? e) (list (check-sym e) #f #f))
        ((eq? (car e) 'var-bounds)  (cdr e))
        ((and (eq? (car e) 'comparison) (length= e 6))
         (cons (check-sym (cadddr e))
               (cond ((and (eq? (caddr e) '|<:|) (eq? (caddr (cddr e)) '|<:|))
                      (list (cadr e) (last e)))
                     (else (error "invalid bounds in \"where\"")))))
        ((eq? (car e) '|<:|)
         (list (check-sym (cadr e)) #f (caddr e)))
        ((eq? (car e) '|>:|)
         (list (check-sym (cadr e)) (caddr e) #f))
        (else (error "invalid variable expression in \"where\""))))

(define (sparam-name-bounds params)
  (let ((bounds (map analyze-typevar params)))
    (values (map car bounds) bounds)))

(define (unmangled-name v)
  (if (eq? v '||)
      v
      (let ((s (string v)))
        (if (eqv? (string.char s 0) #\#)
            (symbol (last (string-split s "#")))
            v))))

;; construct expression to allocate a TypeVar
(define (bounds-to-TypeVar v (unmangle #f))
  (let ((v  ((if unmangle unmangled-name identity) (car v)))
        (lb (cadr v))
        (ub (caddr v)))
    `(call (core TypeVar) ',v
           ,@(if ub
                 (if lb (list lb ub) (list ub))
                 (if lb (list lb '(core Any)) '())))))

(define (is-method? x)
  (if (and (pair? x) (eq? (car x) 'method))
      (let ((name (cadr x)))
        (if (and (pair? name) (eq? (car name) 'globalref))
            (let ((name (caddr name)))
              (if (symbol? name)
                  #t
                  #f))
            (if (symbol? name)
                #t
                #f)))
      #f))

(define (method-expr-name m)
  (let ((name (cadr m)))
      (cond ((globalref? name) (caddr name))
            (else name))))

;; extract static parameter names from a (method ...) expression
(define (method-expr-static-parameters m)
  (let ((type-ex (caddr m)))
    (if (eq? (car type-ex) 'block)
        ;; extract ssavalue labels of sparams from the svec-of-sparams argument to `method`
        (let ((sp-ssavals (cddr (cadddr (last type-ex)))))
          (map (lambda (a)  ;; extract T from (= v (call (core TypeVar) (quote T) ...))
                 (cadr (caddr (caddr a))))
               (filter (lambda (e)
                         (and (pair? e) (eq? (car e) '=) (member (cadr e) sp-ssavals)))
                       (cdr type-ex))))
        '())))

(define (nodot-sym-ref? e)
  (or (symbol? e)
      (and (length= e 3) (eq? (car e) 'globalref))))

;; expressions of the form a.b.c... where everything is a symbol
(define (sym-ref? e)
  (or (nodot-sym-ref? e)
      (and (length= e 3) (eq? (car e) '|.|)
            (or (atom? (cadr e)) (sym-ref? (cadr e)))
            (pair? (caddr e)) (memq (car (caddr e)) '(quote inert))
            (symbol? (cadr (caddr e))))))

(define (overlay? e)
  (and (pair? e) (eq? (car e) 'overlay)))

(define (sym-ref-or-overlay? e)
  (or (overlay? e)
      (sym-ref? e)))

(define (binding-to-globalref e)
  (and (nodot-sym-ref? e)
       (let ((mod (if (globalref? e) (cadr e) '(thismodule)))
             (sym (if (symbol? e) e (last e))))
         `(globalref ,mod ,sym))))

;; convert final (... x) to (curly Vararg x)
(define (dots->vararg a)
  (if (null? a) a
      (let ((head (butlast a))
            (las  (last a)))
        (if (vararg? las)
            `(,@head (curly Vararg ,(cadr las)))
            `(,@head ,las)))))

(define (replace-vars e renames)
  (cond ((symbol? e)      (lookup e renames e))
        ((or (not (pair? e)) (quoted? e))  e)
        ((memq (car e) '(-> function scope-block)) e)
        (else
         (cons (car e)
               (map (lambda (x) (replace-vars x renames))
                    (cdr e))))))

(define (make-generator-function name sp-names arg-names body)
  (let ((arg-names (append sp-names
                           (map (lambda (n)
                                  (if (eq? n '|#self#|) (gensy) n))
                                arg-names))))
    (let ((body (insert-after-meta body  ;; don't specialize on generator arguments
                                   ;; arg-names slots start at 2 (after name)
                                   `((meta nospecialize ,@(map (lambda (idx) `(slot ,(+ idx 2))) (iota (length arg-names))))))))
      `(block
        (global ,name)
        (function (call ,name ,@arg-names) ,body)))))

;; select the `then` or `else` part of `if @generated` based on flag `genpart`
(define (generated-part- x genpart)
  (cond ((or (atom? x) (quoted? x) (function-def? x)) x)
        ((if-generated? x)
         (if genpart `($ ,(caddr x)) (cadddr x)))
        (else (cons (car x)
                    (map (lambda (e) (generated-part- e genpart)) (cdr x))))))

(define (generated-version body)
  `(block
    ,(julia-bq-macro (generated-part- body #t))))

(define (non-generated-version body)
  (generated-part- body #f))

;; Remove and return the line number for the start of the function definition
(define (maybe-remove-functionloc! body)
  (let* ((prologue (extract-method-prologue body))
         (prologue-lnos (filter linenum? prologue))
         (functionloc (if (pair? prologue-lnos)
                          (car prologue-lnos)
                          ; Fallback - take first line anywhere in body
                          (let ((lnos (filter linenum? body)))
                            (if (null? lnos) '(line 0 none) (car lnos))))))
    (if (length> prologue-lnos 1)
        ; First of two line numbers in prologue is function definition location
        ; which should be removed from the body.
        (let loop ((stmts body))
          (if (eq? functionloc (cadr stmts))
              (set-cdr! stmts (cddr stmts))
              (loop (cdr stmts)))))
    functionloc))

;; construct the (method ...) expression for one primitive method definition,
;; assuming optional and keyword args are already handled
(define (method-def-expr- name sparams argl body (rett '(core Any)))
  (if
   (any kwarg? argl)
   ;; has optional positional args
   (begin
     (let check ((l     argl)
                 (seen? #f))
       (if (pair? l)
           (if (kwarg? (car l))
               (check (cdr l) #t)
               (if (and seen? (not (vararg? (car l))))
                   (error "optional positional arguments must occur at end")
                   (check (cdr l) #f)))))
     (receive
      (kws argl) (separate kwarg? argl)
      (let ((opt  (map cadr  kws))
            (dfl  (map caddr kws)))
        (receive
         (vararg req) (separate vararg? argl)
         (optional-positional-defs name sparams req opt dfl body
                                   (append req opt vararg) rett)))))
   ;; no optional positional args
   (let* ((names (map car sparams))
          (anames (map (lambda (x) (if (underscore-symbol? x) UNUSED x)) (llist-vars argl)))
          (unused_anames (filter (lambda (x) (not (eq? x UNUSED))) anames))
          (ename (if (nodot-sym-ref? name) name
                    (if (overlay? name) (cadr name) `(null)))))
     (if (has-dups unused_anames)
         (error (string "function argument name not unique: \"" (car (has-dups unused_anames)) "\"")))
     (if (has-dups names)
         (error (string "function static parameter name not unique: \"" (car (has-dups names)) "\"")))
     (if (any (lambda (x) (and (not (eq? x UNUSED)) (memq x names))) anames)
         (error (string "function argument and static parameter name not distinct: \"" (car (intersect names unused_anames)) "\"")))
     (if (or (and name (not (sym-ref-or-overlay? name))) (not (valid-name? name)))
         (error (string "invalid function name \"" (deparse name) "\"")))
     (let* ((loc (maybe-remove-functionloc! body))
            (generator (if (expr-contains-p if-generated? body (lambda (x) (not (function-def? x))))
                           (let* ((gen    (generated-version body))
                                  (nongen (non-generated-version body))
                                  (gname  (symbol (string (gensy) "#" (current-julia-module-counter '()))))
                                  (gf     (make-generator-function gname names anames gen)))
                             (set! body (insert-after-meta
                                         nongen
                                         `((meta generated
                                                 (new (core GeneratedFunctionStub)
                                                      ,gname
                                                      (call (core svec) ,@(map quotify anames))
                                                      (call (core svec) ,@(map quotify names)))))))
                             (list gf))
                           '()))
            (types (llist-types argl))
            (body  (method-lambda-expr argl body rett))
            ;; HACK: the typevars need to be bound to ssavalues, since this code
            ;; might be moved to a different scope by closure-convert.
            (temps (map (lambda (x) (make-ssavalue)) names))
            (renames (map cons names temps))
            (mdef
             (if (null? sparams)
                 `(method ,ename
                          (call (core svec)
                                (call (core svec) ,@(dots->vararg types))
                                (call (core svec))
                                (inert ,loc))
                          ,body)
                 `(method ,ename
                          (block
                           ,@(let loop ((n       names)
                                        (t       temps)
                                        (sp      (map bounds-to-TypeVar sparams))
                                        (ren     '())
                                        (assigns '()))
                               (if (null? n)
                                   (reverse! assigns)
                                   (loop (cdr n) (cdr t) (cdr sp)
                                         (cons (cons (car n) (car t)) ren)
                                         ;; each static param can see just the previous ones
                                         (cons (make-assignment (car t) (replace-vars (car sp) ren))
                                               assigns))))
                           (call (core svec) (call (core svec)
                                                   ,@(dots->vararg
                                                      (map (lambda (ty)
                                                             (replace-vars ty renames))
                                                           types)))
                                 (call (core svec) ,@temps)
                                 (inert ,loc)))
                          ,body))))
       (if (or (symbol? name) (globalref? name))
           `(block ,@generator (method ,name) ,mdef (unnecessary ,name))  ;; return the function
           (if (not (null? generator))
               `(block ,@generator ,mdef)
               mdef))))))

;; wrap expr in nested scopes assigning names to vals
(define (scopenest names vals expr)
  (if (null? names)
      expr
      `(let (= ,(car names) ,(car vals))
         (block
          ,(scopenest (cdr names) (cdr vals) expr)))))

(define (make-assignments names vals expr)
  `(block
    ,@(map make-assignment names vals)
    ,expr))

(define (keywords-method-def-expr name sparams argl body rett)
  (let* ((kargl (cdar argl))  ;; keyword expressions (= k v)
         (annotations (map (lambda (a) `(meta ,(cadr a) ,(arg-name (cadr (caddr a)))))
                           (filter nospecialize-meta? kargl)))
         (kargl (map (lambda (a)
                       (if (nospecialize-meta? a) (caddr a) a))
                     kargl))
         (pargl (cdr argl))   ;; positional args
         (body  (blockify body))
         (ftype (decl-type (car pargl)))
         ;; 1-element list of vararg argument, or empty if none
         (vararg (let* ((l (if (null? pargl) '() (last pargl)))
                        ;; handle vararg with default value
                        (l- (if (kwarg? l) (cadr l) l)))
                   (if (or (vararg? l-) (varargexpr? l-))
                       (list l) '())))
         ;; expression to forward varargs to another call
         (splatted-vararg (if (null? vararg) '()
                              (list `(... ,(arg-name (car vararg))))))
         ;; positional args with vararg
         (pargl-all pargl)
         ;; positional args without vararg
         (pargl (if (null? vararg) pargl (butlast pargl)))
         ;; positional args with everything required; for use by the core function
         (not-optional (map (lambda (a)
                              (if (kwarg? a) (cadr a) a))
                            pargl))
         ;; keywords glob
         (restkw (let ((l (last kargl)))
                   (if (vararg? l)
                       (list (cadr l)) '())))
         (kargl (let ((kws (if (null? restkw) kargl (butlast kargl))))
                  (if (any vararg? kws)
                      (error "invalid \"...\" on non-final keyword argument"))
                  kws))
         ;; the keyword::Type expressions
         (vars     (map cadr kargl))
         ;; keyword default values
         (vals     (map caddr kargl))
         ;; just the keyword names
         (keynames (map decl-var vars))
         ;; do some default values depend on other keyword arguments?
         (ordered-defaults (any (lambda (v) (contains
                                             (lambda (x) (eq? x v))
                                             vals))
                                keynames))
         ;; if keyword args don't depend on each other and the default
         ;; values don't have embedded assignments (ick) then we can use
         ;; ssavalues instead of slots in the sorter method.
         (ssa-keyvars? (and (not ordered-defaults)
                            (not (contains assignment? vals))))
         (keyvars (if ssa-keyvars?
                      (map (lambda (x) (make-ssavalue)) keynames)
                      keynames))
         (tempslot (gensy))
         ;; list of function's initial line number and meta nodes (empty if none)
         (prologue (extract-method-prologue body))
         ;; body statements
         (stmts (cdr body))
         (positional-sparams (filter-sparams (cons 'list pargl-all) sparams))
         (keyword-sparams
          (filter (lambda (s)
                    (not (any (lambda (p) (eq? (car p) (car s)))
                              positional-sparams)))
                  sparams))
         (kw      (gensy))
         (kwdecl  `(|::| ,kw (core NamedTuple)))
         (rkw     (if (null? restkw) '() (symbol (string (car restkw) "..."))))
         (restkw  (map (lambda (v) `(|::| ,v (call (top pairs) (core NamedTuple)))) restkw))
         (mangled (let ((und (and name (undot-name name))))
                    (symbol (string (if (and name (= (string.char (string name) 0) #\#))
                                        ""
                                        "#")
                                    (or und '_) "#"
                                    (string (current-julia-module-counter '())))))))
      ;; this is a hack: nest these statements inside a call so they get closure
      ;; converted together, allowing all needed types to be defined before any methods.
      `(call (core ifelse) (false) (false) (block
        ;; forward-declare function so its type can occur in the signature of the inner method below
        ,@(if (or (symbol? name) (globalref? name)) `((method ,name)) '())

        ;; call with keyword args pre-sorted - original method code goes here
        ,(method-def-expr-
          mangled sparams
          `((|::| ,mangled (call (core typeof) ,mangled)) ,@vars ,@restkw
            ;; strip type off function self argument if not needed for a static param.
            ;; then it is ok for cl-convert to move this definition above the original def.
            ,@not-optional ,@vararg)
          (insert-after-meta `(block
                               ,@stmts)
                             (cons `(meta nkw ,(+ (length vars) (length restkw)))
                                   annotations))
          rett)

        ;; call with no keyword args
        ,(method-def-expr-
          name positional-sparams pargl-all
          `(block
            ,@(keep-first linenum? (without-generated prologue))
            ,(let (;; call mangled(vals..., [rest_kw,] pargs..., [vararg]...)
                   (ret `(return (call ,mangled
                                       ,@(if ordered-defaults keynames vals)
                                       ,@(if (null? restkw) '() `((call (top pairs) (call (core NamedTuple)))))
                                       ,@(map arg-name pargl)
                                       ,@splatted-vararg))))
               (if ordered-defaults
                   (scopenest keynames vals ret)
                   ret))))

        ;; call with unsorted keyword args. this sorts and re-dispatches.
        ,(method-def-expr-
          name positional-sparams
          `((|::|
             ;; if there are optional positional args, we need to be able to reference the function name
             ,(if (any kwarg? `(,@pargl ,@vararg)) (gensy) UNUSED)
             (call (core kwftype) ,ftype)) ,kwdecl ,@pargl ,@vararg)
          `(block
            ;; propagate method metadata to keyword sorter
            ,@(map propagate-method-meta (filter meta? prologue))
            ,@(filter argwide-nospecialize-meta? prologue)
            ,@(let ((lnns (filter linenum? prologue)))
                (if (pair? lnns)
                    (list (car lnns))
                    '()))
            ;; nospecialize meta for just positional args
            ,@(map (lambda (m)
                     `(meta ,(cadr m) ,@(filter (lambda (v) (not (memq v keynames)))
                                                (cddr m))))
                   (filter nospecialize-meta? prologue))
            ;; If not using slots for the keyword argument values, still declare them
            ;; for reflection purposes.
            ,@(if ssa-keyvars?
                  (map (lambda (v) `(local ,v)) (reverse keynames))
                  '())
            ,((if ssa-keyvars? make-assignments scopenest)
              keyvars
              (map (lambda (v dflt)
                     (let* ((k     (decl-var v))
                            (rval0 `(call (core getfield) ,kw (inert ,k)))
                            ;; note: if the "declared" type of a KW arg includes something
                            ;; from keyword-sparams then don't assert it here, since those
                            ;; static parameters don't have values yet. instead, the type
                            ;; will be picked up when the underlying method is called.
                            (rval (if (and (decl? v)
                                           (not (any (lambda (s)
                                                       (expr-contains-eq (car s) (caddr v)))
                                                     keyword-sparams)))
                                      (let ((T    (caddr v))
                                            (temp (make-ssavalue)))
                                        `(block (= ,temp ,rval0)
                                                (if (call (core isa) ,temp ,T)
                                                    (null)
                                                    (call (core throw)
                                                          (new (core TypeError)
                                                               (inert |keyword argument|)
                                                               (inert ,k)
                                                               ,T
                                                               ,temp)))
                                                ,temp))
                                      rval0)))
                       `(block (if (call (core isdefined) ,kw (quote ,k))
                                   (= ,tempslot ,rval)
                                   (= ,tempslot ,dflt))
                               ,tempslot)))
                   vars vals)
              `(block
                ,(if (null? restkw)
                      `(if (call (top isempty)
                                 (call (top diff_names)
                                       (call (top keys) ,kw)
                                       (tuple ,@(map quotify keynames))))
                            (null)
                            (call (top kwerr) ,kw ,@(map arg-name pargl) ,@splatted-vararg))
                      `(= ,rkw (call (top pairs)
                                     ,(if (null? keynames)
                                          kw
                                          `(call (top structdiff) ,kw (curly (core NamedTuple)
                                                                             (tuple ,@(map quotify keynames))))))))
                (return (call ,mangled  ;; finally, call the core function
                              ,@keyvars
                              ,@(if (null? restkw) '() (list rkw))
                              ,@(map arg-name pargl)
                              ,@splatted-vararg))))))
        ;; return primary function
        ,(if (not (symbol? name))
             '(null) name)))))

;; prologue includes line number node and eventual meta nodes
(define (extract-method-prologue body)
  (if (pair? body)
      (take-while (lambda (e)
                    (and (pair? e) (or (eq? (car e) 'line) (eq? (car e) 'meta))))
                  (cdr body))
      '()))

(define (without-generated stmts)
  (filter (lambda (x) (not (or (generated-meta? x)
                               (generated_only-meta? x))))
          stmts))

;; keep only sparams used by `expr` or other sparams
(define (filter-sparams expr sparams)
  (let loop ((filtered '())
             (params   sparams))
    (cond ((null? params)
           (reverse! filtered))
          ((or (expr-contains-eq (caar params) expr)
               (any (lambda (v) (expr-contains-eq (caar params) v))
                    (cdr params)))
           (loop (cons (car params) filtered) (cdr params)))
          (else
           (loop filtered (cdr params))))))

(define (optional-positional-defs name sparams req opt dfl body overall-argl rett)
  (let ((prologue (without-generated (extract-method-prologue body))))
    `(block
      ,@(map (lambda (n)
               (let* ((passed (append req (list-head opt n)))
                      ;; only keep static parameters used by these arguments
                      (sp     (filter-sparams (cons 'list passed) sparams))
                      (vals   (list-tail dfl n))
                      (absent (list-tail opt n)) ;; absent arguments
                      (body
                       (if (any vararg? (butlast vals))
                         ;; Forbid splat in all but the final default value
                         (error "invalid \"...\" in non-final positional argument default value")
                         (if (any (lambda (defaultv)
                                  ;; does any default val expression...
                                  (contains (lambda (e)
                                              ;; contain "e" such that...
                                              (any (lambda (a)
                                                     ;; "e" is in an absent arg
                                                     (contains (lambda (u)
                                                                 (eq? u e))
                                                               a))
                                                   absent))
                                            defaultv))
                                vals)
                           ;; then add only one next argument
                           `(block
                             ,@prologue
                             (call ,(arg-name (car req)) ,@(map arg-name (cdr passed)) ,(car vals)))
                           ;; otherwise add all
                           `(block
                             ,@prologue
                             (call ,(arg-name (car req)) ,@(map arg-name (cdr passed)) ,@vals))))))
                 (method-def-expr- name sp passed body)))
             (iota (length opt)))
      ,(method-def-expr- name sparams overall-argl body rett))))

;; strip empty (parameters ...), normalizing `f(x;)` to `f(x)`.
(define (remove-empty-parameters argl)
  (if (and (has-parameters? argl) (null? (cdar argl)))
      (cdr argl)
      argl))

(define (check-kw-args kw)
  (let ((invalid (filter (lambda (x) (not (or (kwarg? x) (vararg? x)
                                              (and (nospecialize-meta? x)
                                                   (or (kwarg? (caddr x)) (vararg? (caddr x)))))))
                         kw)))
    (if (pair? invalid)
        (if (and (pair? (car invalid)) (eq? 'parameters (caar invalid)))
            (error "more than one semicolon in argument list")
            (error (string "invalid keyword argument syntax \""
                           (deparse (car invalid)) "\""))))))

; replace unassigned kw args with assignment to throw() call (forcing the caller to assign the keyword)
(define (throw-unassigned-kw-args argl)
  (define (throw-unassigned argname)
    `(call (core throw) (call (core UndefKeywordError) (inert ,argname))))
  (define (to-kw x)
    (cond ((symdecl? x) `(kw ,x ,(throw-unassigned (decl-var x))))
          ((nospecialize-meta? x) `(meta ,(cadr x) ,(to-kw (caddr x))))
          (else x)))
  (if (has-parameters? argl)
      (cons (cons 'parameters
                  (map to-kw (cdar argl)))
            (cdr argl))
      argl))

;; method-def-expr checks for keyword arguments, and if there are any, calls
;; keywords-method-def-expr to expand the definition into several method
;; definitions that do not use keyword arguments.
;; definitions without keyword arguments are passed to method-def-expr-,
;; which handles optional positional arguments by adding the needed small
;; boilerplate definitions.
(define (method-def-expr name sparams argl body rett)
  (let ((argl (throw-unassigned-kw-args (remove-empty-parameters argl))))
    (if (has-parameters? argl)
        ;; has keywords
        (begin (check-kw-args (cdar argl))
               (keywords-method-def-expr name sparams argl body rett))
        ;; no keywords
        (method-def-expr- name sparams argl body rett))))

(define (struct-def-expr name params super fields mut)
  (receive
   (params bounds) (sparam-name-bounds params)
   (struct-def-expr- name params bounds super (flatten-blocks fields) mut)))

;; replace field names with gensyms if they conflict with field-types
(define (safe-field-names field-names field-types)
  (if (any (lambda (v) (contains (lambda (e) (eq? e v)) field-types))
           field-names)
      (map (lambda (x) (gensy)) field-names)
      ;; use a different name for a field called `_`
      (map (lambda (x) (if (eq? x '_) (gensy) x)) field-names)))

(define (with-wheres call wheres)
  (if (pair? wheres)
      `(where ,call ,@wheres)
      call))

(define (default-inner-ctors name field-names field-types params bounds locs)
  (let* ((field-names (safe-field-names field-names field-types))
         (all-ctor (if (null? params)
          ;; definition with exact types for all arguments
          `(function (call ,name
                          ,@(map make-decl field-names field-types))
                    (block
                     ,@locs
                     (new (globalref (thismodule) ,name) ,@field-names)))
          #f))
         (any-ctor (if (or (not all-ctor) (any (lambda (t) (not (equal? t '(core Any))))
                                 field-types))
          ;; definition with Any for all arguments
          ;; only if any field type is not Any, checked at runtime
          `(function (call (|::| |#ctor-self#|
                            ,(with-wheres
                              `(curly (core Type) ,(if (pair? params)
                                                       `(curly ,name ,@params)
                                                       name))
                              (map (lambda (b) (cons 'var-bounds b)) bounds)))
                           ,@field-names)
                     (block
                      ,@locs
                      (call new ,@field-names))) ; this will add convert calls later
          #f)))
    (if all-ctor
        (if any-ctor
            (list all-ctor
                  `(if ,(foldl (lambda (t u)
                           `(&& ,u (call (core ===) (core Any) ,t)))
                         `(call (core ===) (core Any) ,(car field-types))
                         (cdr field-types))
                       '(block)
                       ,any-ctor))
            (list all-ctor))
        (list any-ctor))))

(define (default-outer-ctor name field-names field-types params bounds locs)
  (let ((field-names (safe-field-names field-names field-types)))
    `(function ,(with-wheres
                 `(call ,name ,@(map make-decl field-names field-types))
                 (map (lambda (b) (cons 'var-bounds b)) bounds))
               (block
                ,@locs
                (new (curly ,name ,@params) ,@field-names)))))

(define (num-non-varargs args)
  (count (lambda (a) (not (vararg? a))) args))

;; selftype?: tells us whether the called object is the type being constructed,
;; i.e. `new()` and not `new{...}()`.
(define (new-call Tname type-params sparams params args field-names field-types selftype?)
  (if (any kwarg? args)
      (error "\"new\" does not accept keyword arguments"))
  (let ((nnv (num-non-varargs type-params)))
    (if (and (not (any vararg? type-params)) (length> params nnv))
        (error "too few type parameters specified in \"new{...}\""))
    (if (> nnv (length params))
        (error "too many type parameters specified in \"new{...}\"")))
  (let* ((Texpr (if (null? type-params)
                    `(globalref (thismodule) ,Tname)
                    (if selftype?
                        '|#ctor-self#|
                        `(curly (globalref (thismodule) ,Tname)
                                ,@type-params))))
         (tn (if (symbol? Texpr) Texpr (make-ssavalue)))
         (field-convert (lambda (fld fty val)
                          (if (equal? fty '(core Any))
                              val
                              (convert-for-type-decl val
                                                     ; for ty, usually use the fieldtype, not the fty expression
                                                     (if (and (not selftype?) (equal? type-params params) (memq fty params) (memq fty sparams))
                                                      fty ; the field type is a simple parameter, the usage here is of a
                                                          ; local variable (currently just handles sparam) for the bijection of params to type-params
                                                      `(call (core fieldtype) ,tn ,(+ fld 1)))
                                                      #f
                                                      #f)))))
    (cond ((> (num-non-varargs args) (length field-names))
           `(call (core throw) (call (top ArgumentError)
                                     ,(string "new: too many arguments (expected " (length field-names) ")"))))
          ((any vararg? args)
           (if (every (lambda (ty) (equal? ty '(core Any)))
                      field-types)
               `(splatnew ,Texpr (call (core tuple) ,@args))
               (let ((argt (make-ssavalue))
                     (nf (make-ssavalue)))
                 `(block
                   ,@(if (symbol? tn) '() `((= ,tn ,Texpr)))
                   (= ,argt (call (core tuple) ,@args))
                   (= ,nf (call (core nfields) ,argt))
                   (if (call (top ult_int) ,nf ,(length field-names))
                       (call (core throw) (call (top ArgumentError)
                                                ,(string "new: too few arguments (expected " (length field-names) ")"))))
                   (if (call (top ult_int) ,(length field-names) ,nf)
                       (call (core throw) (call (top ArgumentError)
                                                ,(string "new: too many arguments (expected " (length field-names) ")"))))
                   (new ,tn ,@(map (lambda (fld fty) (field-convert fld fty `(call (core getfield) ,argt ,(+ fld 1) (false))))
                                   (iota (length field-names)) (list-head field-types (length field-names))))))))
          (else
           `(block
             ,@(if (symbol? tn) '() `((= ,tn ,Texpr)))
             (new ,tn ,@(map field-convert (iota (length args)) (list-head field-types (length args)) args)))))))

;; insert item at start of arglist
(define (arglist-unshift sig item)
  (if (and (pair? sig) (pair? (car sig)) (eq? (caar sig) 'parameters))
      `(,(car sig) ,item ,@(cdr sig))
      `(,item ,@sig)))

(define (linenode-string lno)
  (cond ((length= lno 2) (string " around line " (cadr lno)))
        ((length= lno 3) (string " around " (caddr lno) ":" (cadr lno)))
        (else "")))

;; convert constructor signature from X(...) to (|#ctor-self#|::Type{X})(...),
;; or return #f if we can't
(define (ctor-sig sig)
  (cond ((or (eq? (car sig) '|::|) (eq? (car sig) 'where))
         (let ((s2 (ctor-sig (cadr sig))))
           (and s2 `(,(car sig) ,s2 ,@(cddr sig)))))
        ((eq? (car sig) 'call)
         (let ((head (cadr sig)))
           (if (decl? head)
               (if (eq? (cadr head) '|#ctor-self#|)
                   sig  ;; already in the required form
                   #f)
               `(call (|::| |#ctor-self#| (curly (core Type) ,head)) ,@(cddr sig)))))
        (else #f)))

(define (ctor-def name Tname ctor-body sig body wheres)
  (let* ((curly?     (and (pair? name) (eq? (car name) 'curly)))
         (curlyargs  (if curly? (cddr name) '()))
         (name       (if curly? (cadr name) name))
         (sparams (map car (map analyze-typevar wheres))))
    (cond ((not (eq? name Tname))
           `(function ,sig
                      ;; pass '() in order to require user-specified parameters with
                      ;; new{...} inside a non-ctor inner definition.
                      ,(ctor-body body '() sparams #f)))
          (else
           (let ((newsig (ctor-sig sig)))
             `(function ,(or newsig sig)
                        ,(ctor-body body curlyargs sparams (not (not newsig)))))))))

;; rewrite calls to `new( ... )` to `new` expressions on the appropriate
;; type, determined by the containing constructor definition.
(define (rewrite-ctor ctor Tname params field-names field-types)
  (define (ctor-body body type-params sparams selftype?)
    (pattern-replace (pattern-set
                      (pattern-lambda
                       (call (-/ new) . args)
                       (new-call Tname type-params sparams params
                                 (map (lambda (a) (ctor-body a type-params sparams selftype?)) args)
                                 field-names field-types selftype?))
                      (pattern-lambda
                       (call (curly (-/ new) . p) . args)
                       (new-call Tname p sparams params
                                 (map (lambda (a) (ctor-body a type-params sparams selftype?)) args)
                                 field-names field-types #f)))
                     body))
  (pattern-replace
   (pattern-set
    ;; recognize `(t::(Type{X{T}} where T))(...)` as an inner-style constructor for X
    (pattern-lambda (function       (-$ (call (|::| self (where (curly (core (-/ Type)) name) . wheres)) . sig)
                                        (|::| (call (|::| self (where (curly (core (-/ Type)) name) . wheres)) . sig) _t))
                                    body)
                    (ctor-def name Tname ctor-body (cadr __) body wheres))
    ;; definitions without `where`
    (pattern-lambda (function       (-$ (call name . sig) (|::| (call name . sig) _t)) body)
                    (ctor-def name Tname ctor-body (cadr __) body #f))
    (pattern-lambda (= (-$ (call name . sig) (|::| (call name . sig) _t)) body)
                    (ctor-def name Tname ctor-body (cadr __) body #f))
    ;; definitions with `where`
    (pattern-lambda (function       (where (-$ (call name . sig) (|::| (call name . sig) _t)) . wheres) body)
                    (ctor-def name Tname ctor-body (cadr __) body wheres))
    (pattern-lambda (= (where (-$ (call name . sig) (|::| (call name . sig) _t)) . wheres) body)
                    (ctor-def name Tname ctor-body (cadr __) body wheres)))

   ;; flatten `where`s first
   (pattern-replace
    (pattern-set
     (pattern-lambda (where (where . rest1) . rest2)
                     (flatten-where-expr __)))
    ctor)))

;; check if there are any calls to new with fewer than n arguments
(define (ctors-min-initialized expr)
  (and (pair? expr)
       (min
        ((pattern-lambda (call (-/ new) . args)
                         (length args))
         (car expr))
        ((pattern-lambda (call (curly (-/ new) . p) . args)
                         (length args))
         (car expr))
        (ctors-min-initialized (car expr))
        (ctors-min-initialized (cdr expr)))))

(define (struct-def-expr- name params bounds super fields0 mut)
  (receive
   (fields defs) (separate eventually-decl? fields0)
   (let* ((attrs ())
          (fields (let ((n 0))
                    (map (lambda (x)
                           (set! n (+ n 1))
                           (let loop ((x x))
                             (if (and (pair? x) (not (decl? x)))
                                 (begin
                                   (set! attrs (cons (quotify (car x)) (cons n attrs)))
                                   (loop (cadr x)))
                                 x)))
                         fields)))
          (attrs (reverse attrs))
          (defs        (filter (lambda (x) (not (or (effect-free? x) (eq? (car x) 'string)))) defs))
          (locs        (if (and (pair? fields0) (linenum? (car fields0)))
                           (list (car fields0))
                           '()))
          (field-names (map decl-var fields))
          (field-types (map decl-type fields))
          (defs2 (if (null? defs)
                     (default-inner-ctors name field-names field-types params bounds locs)
                     defs))
          (min-initialized (min (ctors-min-initialized defs) (length fields)))
          (prev (make-ssavalue)))
     (let ((dups (has-dups field-names)))
       (if dups (error (string "duplicate field name: \"" (car dups) "\" is not unique"))))
     (for-each (lambda (v)
                 (if (not (symbol? v))
                     (error (string "field name \"" (deparse v) "\" is not a symbol"))))
               field-names)
     `(block
       (global ,name)
       (scope-block
        (block
         (hardscope)
         (local-def ,name)
         ,@(map (lambda (v) `(local ,v)) params)
         ,@(map (lambda (n v) (make-assignment n (bounds-to-TypeVar v #t))) params bounds)
         (toplevel-only struct (globalref (thismodule) ,name))
         (= ,name (call (core _structtype) (thismodule) (inert ,name) (call (core svec) ,@params)
                        (call (core svec) ,@(map quotify field-names))
                        (call (core svec) ,@attrs)
                        ,mut ,min-initialized))
         (call (core _setsuper!) ,name ,super)
         (if (isdefined (globalref (thismodule) ,name) (false))
             (block
              (= ,prev (globalref (thismodule) ,name))
              (if (call (core _equiv_typedef) ,prev ,name)
                  ;; if this is compatible with an old definition, use the existing type object
                  ;; and its parameters
                  (block (= ,name ,prev)
                         ,@(if (pair? params)
                               `((= (tuple ,@params) (|.|
                                                      ,(foldl (lambda (_ x) `(|.| ,x (quote body)))
                                                              prev
                                                              params)
                                                      (quote parameters))))
                               '()))
                  ;; otherwise do an assignment to trigger an error
                  (const (globalref (thismodule) ,name) ,name)))
             (const (globalref (thismodule) ,name) ,name))
         (call (core _typebody!) ,name (call (core svec) ,@field-types))
         (null)))
       ;; "inner" constructors
       (scope-block
        (block
         (hardscope)
         (global ,name)
         ,@(map (lambda (c)
                  (rewrite-ctor c name params field-names field-types))
                defs2)))
       ;; "outer" constructors
       ,@(if (and (null? defs)
                  (not (null? params))
                  ;; To generate an outer constructor, each parameter must occur in a field
                  ;; type, or in the bounds of a subsequent parameter.
                  ;; Otherwise the constructor would not work, since the parameter values
                  ;; would never be specified.
                  (let loop ((root-types field-types)
                             (sp         (reverse bounds)))
                    (or (null? sp)
                        (let ((p (car sp)))
                          (and (expr-contains-eq (car p) (cons 'list root-types))
                               (loop (append (cdr p) root-types)
                                     (cdr sp)))))))
             `((scope-block
                (block
                 (global ,name)
                 ,(default-outer-ctor name field-names field-types
                    params bounds locs))))
             '())
       (null)))))

(define (abstract-type-def-expr name params super)
  (receive
   (params bounds) (sparam-name-bounds params)
   `(block
     (global ,name)
     (scope-block
      (block
       (local-def ,name)
       ,@(map (lambda (v) `(local ,v)) params)
       ,@(map (lambda (n v) (make-assignment n (bounds-to-TypeVar v #t))) params bounds)
       (toplevel-only abstract_type)
       (= ,name (call (core _abstracttype) (thismodule) (inert ,name) (call (core svec) ,@params)))
       (call (core _setsuper!) ,name ,super)
       (call (core _typebody!) ,name)
       (if (&& (isdefined (globalref (thismodule) ,name) (false))
               (call (core _equiv_typedef) (globalref (thismodule) ,name) ,name))
           (null)
           (const (globalref (thismodule) ,name) ,name))
       (null))))))

(define (primitive-type-def-expr n name params super)
  (receive
   (params bounds) (sparam-name-bounds params)
   `(block
     (global ,name)
     (scope-block
      (block
       (local-def ,name)
       ,@(map (lambda (v) `(local ,v)) params)
       ,@(map (lambda (n v) (make-assignment n (bounds-to-TypeVar v #t))) params bounds)
       (toplevel-only primitive_type)
       (= ,name (call (core _primitivetype) (thismodule) (inert ,name) (call (core svec) ,@params) ,n))
       (call (core _setsuper!) ,name ,super)
       (call (core _typebody!) ,name)
       (if (&& (isdefined (globalref (thismodule) ,name) (false))
               (call (core _equiv_typedef) (globalref (thismodule) ,name) ,name))
           (null)
           (const (globalref (thismodule) ,name) ,name))
       (null))))))

;; take apart a type signature, e.g. T{X} <: S{Y}
(define (analyze-type-sig ex)
  (or ((pattern-lambda (-- name (-s))
                       (values name '() '(core Any))) ex)
      ((pattern-lambda (curly (-- name (-s)) . params)
                       (values name params '(core Any))) ex)
      ((pattern-lambda (|<:| (-- name (-s)) super)
                       (values name '() super)) ex)
      ((pattern-lambda (|<:| (curly (-- name (-s)) . params) super)
                       (values name params super)) ex)
      (error "invalid type signature")))

;; insert calls to convert() in ccall, and pull out expressions that might
;; need to be rooted before conversion.
(define (lower-ccall name RT atypes args cconv nreq)
  (let loop ((F atypes)  ;; formals
             (A args)    ;; actuals
             (stmts '()) ;; initializers
             (T '())     ;; argument types (F converted)
             (C '())     ;; argument values (A converted)
             (GC '()))   ;; GC roots
    (if (and (null? F) (not (null? A)))
        (error "more arguments than types for ccall"))
    (if (and (null? A) (not (or (null? F) (and (pair? F) (vararg? (car F)) (null? (cdr F))))))
        (error "more types than arguments for ccall"))
    (let ((isseq (and (not (null? F)) (vararg? (car F)))))
      (if (and isseq (null? T))
          (error "C ABI prohibits vararg without one required argument"))
      (if (null? A)
          `(block
            ,.(reverse! stmts)
            (foreigncall ,(expand-forms name) ,(expand-forms RT) (call (core svec) ,@(reverse! T))
                         ;; 0 or number of arguments before ... in definition
                         ,(or nreq
                              (if isseq (- (length atypes) 1) 0))
                         ',cconv
                         ,.(reverse! C)
                         ,@GC)) ; GC root ordering is arbitrary
          (let* ((a     (expand-forms (car A)))
                 (ty    (expand-forms (if isseq (cadar F) (car F)))))
            (if (and isseq (not (null? (cdr F)))) (error "only the trailing ccall argument type should have \"...\""))
            (if (eq? ty 'Any)
                (loop (if isseq F (cdr F)) (cdr A) stmts (list* '(core Any) T) (list* a C) GC)
                (let* ((g (make-ssavalue))
                       (stmts (cons `(= ,g (call (top cconvert) ,ty ,a)) stmts))
                       (ca `(call (top unsafe_convert) ,ty ,g)))
                  (loop (if isseq F (cdr F)) (cdr A) stmts
                        (list* ty T) (list* ca C) (list* g GC)))))))))

(define (just-arglist? ex)
  (and (pair? ex)
       (or (memq (car ex) '(tuple block ...))
           (and (eq? (car ex) 'where)
                (just-arglist? (cadr ex))))))

(define (expand-function-def e)   ;; handle function definitions
  (if (just-arglist? (cadr e))
      (expand-forms (cons '-> (cdr e)))
      (expand-function-def- e)))

;; convert (where (where x S) T) to (where x T S)
(define (flatten-where-expr e)
  (let loop ((ex e)
             (vars '()))
    (if (and (pair? ex) (eq? (car ex) 'where))
        (loop (cadr ex) (append! (reverse (cddr ex)) vars))
        `(where ,ex ,.(reverse! vars)))))

(define (lower-destructuring-args argl)
  (define (check-lhs a)
    (if (expr-contains-p (lambda (e) (or (decl? e) (assignment? e) (kwarg? e)))
                         a)
        (error (string "invalid argument destructuring syntax \"" (deparse a) "\""))
        a))
  (define (transform-arg a)
    (cond ((and (pair? a) (eq? (car a) 'tuple))
           (let ((a2 (gensy)))
             (cons a2 `(local (= ,(check-lhs a) ,a2)))))
          ((or (and (decl? a) (length= a 3)) (kwarg? a))
           (let ((x (transform-arg (cadr a))))
             (cons `(,(car a) ,(car x) ,(caddr a)) (cdr x))))
          ((vararg? a)
           (let ((x (transform-arg (cadr a))))
             (cons `(... ,(car x)) (cdr x))))
          (else (cons a #f))))
  (let loop ((argl  argl)
             (newa  '())
             (stmts '()))
    (if (null? argl)
        (cons (reverse newa) (if (null? stmts)
                                 stmts
                                 ;; return `nothing` from the assignments (issue #26518)
                                 (reverse (cons '(null) stmts))))
        (let ((a (transform-arg (car argl))))
          (loop (cdr argl) (cons (car a) newa)
                (if (cdr a) (cons (cdr a) stmts) stmts))))))

(define (expand-function-def- e)
  (let* ((name  (cadr e))
         (where (if (and (pair? name) (eq? (car name) 'where))
                    (let ((w (flatten-where-expr name)))
                      (begin0 (cddr w)
                              (if (not (and (pair? (cadr w)) (memq (caadr w) '(call |::|))))
                                  (error (string "invalid assignment location \"" (deparse name) "\"")))
                              (set! name (cadr w))))
                    #f))
         (dcl   (and (pair? name) (eq? (car name) '|::|)))
         (rett  (if dcl (caddr name) '(core Any)))
         (name  (if dcl (cadr name) name)))
    (cond ((and (length= e 2) (or (symbol? name) (globalref? name)))
           (if (not (valid-name? name))
               (error (string "invalid function name \"" name "\"")))
           `(method ,name))
          ((not (pair? name))  e)
          ((eq? (car name) 'call)
           (let* ((raw-typevars (or where '()))
                  (sparams (map analyze-typevar raw-typevars))
                  (argl    (cdr name))
                  ;; strip @nospecialize
                  (annotations (map (lambda (a) `(meta ,(cadr a) ,(arg-name (caddr a))))
                                    (filter nospecialize-meta? argl)))
                  (body (insert-after-meta (caddr e) annotations))
                  (argl (map (lambda (a)
                               (if (nospecialize-meta? a) (caddr a) a))
                             argl))
                  ;; handle destructuring
                  (argl-stmts (lower-destructuring-args argl))
                  (argl       (car argl-stmts))
                  (name       (check-dotop (car argl)))
                  (argname    (if (overlay? name) (caddr name) name))
                  ;; fill in first (closure) argument
                  (adj-decl (lambda (n) (if (and (decl? n) (length= n 2))
                                            `(|::| |#self#| ,(cadr n))
                                            n)))
                  (farg    (if (decl? argname)
                               (adj-decl argname)
                               `(|::| |#self#| (call (core Typeof) ,argname))))
                  (body       (insert-after-meta body (cdr argl-stmts)))
                  (argl    (cdr argl))
                  (argl    (fix-arglist
                            (arglist-unshift argl farg)
                            (and (not (any kwarg? argl)) (not (and (pair? argl)
                                                                   (pair? (car argl))
                                                                   (eq? (caar argl) 'parameters))))))
                  (name    (if (or (decl? name) (and (pair? name) (memq (car name) '(curly where))))
                               #f name)))
             (expand-forms
              (method-def-expr name sparams argl body rett))))
          (else
           (error (string "invalid assignment location \"" (deparse name) "\""))))))

;; handle ( )->( ) function expressions. blocks `(a;b=1)` on the left need to be
;; converted to argument lists with kwargs.
(define (expand-arrow e)
  (let* ((a     (cadr e))
         (body  (caddr e))
         (where (if (and (pair? a) (eq? (car a) 'where))
                    (let ((w (flatten-where-expr a)))
                      (begin0 (cddr w)
                              (set! a (cadr w))))
                    #f))
         (argl (if (pair? a)
                   (tuple-to-arglist (filter (lambda (x) (not (linenum? x))) a))
                   (list a)))
         ;; TODO: always use a specific special name like #anon# or _, then ignore
         ;; this as a local variable name.
         (name (symbol (string "#" (current-julia-module-counter '())))))
    (expand-forms
     `(block (local ,name)
             (function
              ,(if where
                   `(where (call ,name ,@argl) ,@where)
                   `(call ,name ,@argl))
              ,body)))))

(define (function-arglist e)
  (cond ((eq? (car e) 'function)
         (if (just-arglist? (cadr e))
             (function-arglist (cons '-> (cdr e)))
             (let* ((name  (cadr e))
                    (dcl   (and (pair? name) (eq? (car name) '|::|)))
                    (name  (if dcl (cadr name) name)))
               (cddr name))))
        ((eq? (car e) '->)
         (let* ((a (cadr e)))
           (if (pair? a)
               (tuple-to-arglist (filter (lambda (x) (not (linenum? x))) a))
               (list a))))
        (else '())))

(define (let-binds e)
  (if (and (pair? (cadr e))
           (eq? (car (cadr e)) 'block))
      (cdr (cadr e))
      (list (cadr e))))

(define (expand-let e (hard? #t))
  (let ((ex    (caddr e))
        (binds (let-binds e))
        (hs    (if hard? '((hardscope)) '())))
    (expand-forms
     (if
      (null? binds)
      `(scope-block (block ,@hs ,ex))
      (let loop ((binds (reverse binds))
                 (blk   ex))
        (if (null? binds)
            blk
            (cond
             ((symdecl? (car binds))
              ;; just symbol -> add local
              (loop (cdr binds)
                    `(scope-block
                      (block ,@hs
                       (local ,(car binds))
                       ,blk))))
             ((and (length= (car binds) 3)
                   (eq? (caar binds) '=))
              ;; some kind of assignment
              (cond
               ((eventually-call? (cadar binds))
                ;; f() = c
                (let ((name (assigned-name (cadar binds))))
                  (if (not (symbol? name))
                      (error "invalid let syntax"))
                  (loop (cdr binds)
                        `(scope-block
                          (block ,@hs
                           ,(if (expr-contains-eq name (caddar binds))
                                `(local ,name) ;; might need a Box for recursive functions
                                `(local-def ,name))
                           ,(car binds)
                           ,blk)))))
               ((symdecl?   (cadar binds))
                (let ((vname (decl-var (cadar binds))))
                  (loop (cdr binds)
                        (let ((tmp (make-ssavalue)))
                          `(block (= ,tmp ,(caddar binds))
                                  (scope-block
                                   (block ,@hs
                                          (local-def ,(cadar binds))
                                          (= ,vname ,tmp)
                                          ,blk)))))))
               ;; (a, b, c, ...) = rhs
               ((and (pair? (cadar binds))
                     (eq? (caadar binds) 'tuple))
                (let ((vars (lhs-vars (cadar binds))))
                  (loop (cdr binds)
                        (let ((tmp (make-ssavalue)))
                          `(block (= ,tmp ,(caddar binds))
                                  (scope-block
                                   (block ,@hs
                                          ,@(map (lambda (v) `(local-def ,v)) vars)
                                          (= ,(cadar binds) ,tmp)
                                          ,blk)))))))
               (else (error "invalid let syntax"))))
             (else (error "invalid let syntax")))))))))

(define (valid-macro-def-name? e)
  (or (symbol? e) (valid-modref? e) (globalref? e)))

(define (expand-macro-def e)
  (cond ((and (pair? (cadr e))
              (eq? (car (cadr e)) 'call)
              (valid-macro-def-name? (cadr (cadr e))))
         (let ((anames (remove-empty-parameters (cddr (cadr e)))))
           (if (has-parameters? anames)
               (error "macros cannot accept keyword arguments"))
           (expand-forms
            `(function (call ,(macroify-name (cadr (cadr e)))
                             (|::| __source__ (core LineNumberNode))
                             (|::| __module__ (core Module))
                             ,@(map (lambda (v)
                                      (if (symbol? v)
                                          `(meta nospecialize ,v)
                                          v))
                                    anames))
                       ,@(cddr e)))))
        ((and (length= e 2) (valid-macro-def-name? (cadr e)))
         (expand-forms `(function ,(macroify-name (cadr e)))))
        (else
         (error "invalid macro definition"))))

(define (expand-struct-def e)
  (let ((mut (cadr e))
        (sig (caddr e))
        (fields (cdr (cadddr e))))
    (let loop ((f fields))
      (if (null? f)
          '()
          (let ((x (car f)))
            (cond ((or (eventually-decl? x) (linenum? x))
                   (loop (cdr f)))
                  ((and (assignment? x) (eventually-decl? (cadr x)))
                   (error (string "\"" (deparse x) "\" inside type definition is reserved")))
                  (else '())))))
    (expand-forms
     (receive (name params super) (analyze-type-sig sig)
              (struct-def-expr name params super fields mut)))))

;; the following are for expanding `try` blocks

(define (find-symbolic-label-defs e tbl)
  (if (or (not (pair? e)) (quoted? e))
      '()
      (if (eq? (car e) 'symboliclabel)
          (put! tbl (cadr e) #t)
          (for-each (lambda (x) (find-symbolic-label-defs x tbl)) e))))

(define (find-symbolic-label-refs e tbl)
  (if (or (not (pair? e)) (quoted? e))
      '()
      (if (eq? (car e) 'symbolicgoto)
          (put! tbl (cadr e) #t)
          (for-each (lambda (x) (find-symbolic-label-refs x tbl)) e))))

(define (has-unmatched-symbolic-goto? e)
  (let ((label-refs (table))
        (label-defs (table)))
    (find-symbolic-label-refs e label-refs)
    (find-symbolic-label-defs e label-defs)
    (any not (map (lambda (k) (get label-defs k #f))
                  (table.keys label-refs)))))

(define (expand-try e)
  (let ((tryb   (cadr e))
        (var    (caddr e))
        (catchb (cadddr e)))
    (cond ((and (length> e 4) (not (equal? (caddddr e) '(false))))
           (if (has-unmatched-symbolic-goto? tryb)
               (error "goto from a try/finally block is not permitted"))
           (let ((finalb (caddddr e)))
             (expand-forms
              `(tryfinally
                ,(if (and (equal? catchb '(false)) (length= e 5))
                     `(scope-block ,tryb)
                     `(try ,tryb ,var ,catchb (false) ,@(cdddddr e)))
                (scope-block ,finalb)))))
          ((length> e 3)
           (and (length> e 6) (error "invalid \"try\" form"))
           (let ((elseb (if (length= e 6) `((scope-block ,@(cdddddr e))) '())))
             (expand-forms
               `(,(if (null? elseb) 'trycatch 'trycatchelse)
                 (scope-block ,tryb)
                 (scope-block
                   ,(if (symbol-like? var)
                        `(scope-block
                          (block (= ,var (the_exception))
                                 ,catchb))
                        `(scope-block ,catchb)))
                 ,@elseb))))
          (else
           (error "invalid \"try\" form")))))

(define (expand-unionall-def name type-ex (allow-local #t))
  (if (and (pair? name)
           (eq? (car name) 'curly))
      (let ((name   (cadr name))
            (params (cddr name))
            (rr     (make-ssavalue)))
        (if (null? params)
            (error (string "empty type parameter list in \"" (deparse `(= (curly ,name) ,type-ex)) "\"")))
          (expand-forms
            `(block
              (= ,rr (where ,type-ex ,@params))
              (,(if allow-local 'assign-const-if-global 'const) ,name ,rr)
              ,rr)))
      (expand-forms
       `(const (= ,name ,type-ex)))))

(define (filter-not-underscore syms)
  (filter (lambda (x) (not (underscore-symbol? x))) syms))

;; Expand `[global] const a::T = val`
(define (expand-const-decl e (mustassgn #f))
  (if (length= e 3) e
    (let ((arg (cadr e)))
      (if (atom? arg)
          (if mustassgn
            (error "expected assignment after \"const\"")
            e)
          (case (car arg)
            ((global)
              (expand-const-decl `(const ,(cadr arg)) #t))
            ((=)
              (cond
                ;; `const f() = ...` - The `const` here is inoperative, but the syntax happened to work in earlier versions, so simply strip `const`.
                ;; TODO: Consider whether to keep this in 2.0.
                ((eventually-call? (cadr arg))
                 (expand-forms arg))
                ((and (pair? (cadr arg)) (eq? (caadr arg) 'curly))
                 (expand-unionall-def (cadr arg) (caddr arg)))
                ((and (pair? (cadr arg)) (eq? (caadr arg) 'tuple) (not (has-parameters? (cdr (cadr arg)))))
                  ;; We need this case because `(f(), g()) = (1, 2)` goes through here, which cannot go via the `local` lowering below,
                  ;; because the symbols come out wrong. Sigh... So much effort for such a syntax corner case.
                  (expand-tuple-destruct (cdr (cadr arg)) (caddr arg) (lambda (assgn) `(,(car e) ,assgn))))
                (else
                 (let ((rr (make-ssavalue)))
                   (expand-forms `(block
                           (= ,rr ,(caddr arg))
                           (scope-block (block (hardscope)
                            (local (= ,(cadr arg) ,rr))
                            ,.(map (lambda (v) `(,(car e) (globalref (thismodule) ,v) ,v)) (filter-not-underscore (lhs-vars (cadr arg))))
                            ,rr))))))))
            (else (error "expected assignment after \"const\"")))))))

(define (expand-atomic-decl e)
  (error "unimplemented or unsupported atomic declaration"))

(define (expand-local-or-global-decl e)
  (if (and (symbol? (cadr e)) (length= e 2))
      e
      (expand-forms (expand-decls (car e) (cdr e)))))

;; given a complex assignment LHS, return the symbol that will ultimately be assigned to
(define (assigned-name e)
  (cond ((atom? e) e)
        ((or (memq (car e) '(call curly where))
             (and (eq? (car e) '|::|) (eventually-call? e)))
         (assigned-name (cadr e)))
        (else e)))

;; local x, (y=2), z => local x;local y;local z;y = 2
(define (expand-decls what binds)
  (if (not (list? binds))
      (error (string "invalid \"" what "\" declaration")))
  (let loop ((b       binds)
             (decls   '())
             (assigns '()))
    (if (null? b)
        `(block
          ,.(reverse decls)
          ,.(reverse assigns)
          ,.(if (null? assigns) `((null)) '()))
        (let ((x (car b)))
          (cond ((or (assignment-like? x) (function-def? x))
                 (let ((new-vars (lhs-decls (assigned-name (cadr x)))))
                  (loop (cdr b)
                       (append (map (lambda (x) `(,what ,x)) new-vars) decls)
                       (cons `(,(car x) ,(all-decl-vars (cadr x)) ,(caddr x))
                             assigns))))
                ((and (pair? x) (eq? (car x) '|::|))
                 (loop (cdr b)
                       (cons `(decl ,@(cdr x)) (cons `(,what ,(decl-var x)) decls))
                       assigns))
                ((symbol? x)
                 (loop (cdr b) (cons `(,what, x) decls) assigns))
                (else
                 (error (string "invalid syntax in \"" what "\" declaration"))))))))

;; convert (lhss...) = (tuple ...) to assignments, eliminating the tuple
(define (tuple-to-assignments lhss0 x wrap)
  (let loop ((lhss lhss0)
             (assigned lhss0)
             (rhss (cdr x))
             (stmts '())
             (after '())
             (elts  '()))
    (if (null? lhss)
        `(block ,@(reverse stmts)
                ,@(reverse after)
                (unnecessary (tuple ,@(reverse elts))))
        (let ((L (car lhss))
              ;; rhss can be null iff L is a vararg
              (R (if (null? rhss) '() (car rhss))))
          (cond ((and (symbol-like? L)
                      (or (not (pair? R)) (quoted? R) (equal? R '(null)))
                      ;; overwrite var immediately if it doesn't occur elsewhere
                      (not (contains (lambda (e) (eq-sym? e L)) (cdr rhss)))
                      (not (contains (lambda (e) (eq-sym? e R)) assigned)))
                 (loop (cdr lhss)
                       (cons L assigned)
                       (cdr rhss)
                       (cons (wrap (make-assignment L R)) stmts)
                       after
                       (cons R elts)))
                ((vararg? L)
                 (if (any vararg? (cdr lhss))
                     (error "multiple \"...\" on lhs of assignment"))
                 (if (null? (cdr lhss))
                     (let ((temp (if (eventually-call? (cadr L)) (gensy) (make-ssavalue))))
                       `(block ,@(reverse stmts)
                               (= ,temp (tuple ,@rhss))
                               ,@(reverse after)
                               ,(wrap `(= ,(cadr L) ,temp))
                               (unnecessary (tuple ,@(reverse elts) (... ,temp)))))
                     (let ((lhss- (reverse lhss))
                           (rhss- (reverse rhss))
                           (lhs-tail '())
                           (rhs-tail '()))
                       (define (extract-tail)
                         (if (not (or (null? lhss-) (null? rhss-)
                                      (vararg? (car lhss-)) (vararg? (car rhss-))))
                             (begin
                               (set! lhs-tail (cons (car lhss-) lhs-tail))
                               (set! rhs-tail (cons (car rhss-) rhs-tail))
                               (set! lhss- (cdr lhss-))
                               (set! rhss- (cdr rhss-))
                               (extract-tail))))
                       (extract-tail)
                       (let* ((temp (if (any (lambda (x)
                                               (or (eventually-call? x)
                                                   (and (vararg? x) (eventually-call? (cadr x)))))
                                             lhss-)
                                        (gensy)
                                        (make-ssavalue)))
                              (assigns (make-assignment temp `(tuple ,@(reverse rhss-))))
                              (assigns (if (symbol? temp)
                                          `((local-def ,temp) ,assigns)
                                          (list assigns)))
                              (n (length lhss-))
                              (st (gensy))
                              (end (list after))
                              (assigns (if (and (length= lhss- 1) (vararg? (car lhss-)))
                                           (begin
                                             (set-car! end
                                                       (cons (wrap `(= ,(cadar lhss-) ,temp)) (car end)))
                                             assigns)
                                           (append (if (> n 0)
                                                       `(,@assigns (local ,st))
                                                       assigns)
                                                   (destructure- 1 (reverse lhss-) temp
                                                                 n st end wrap)))))
                         (loop lhs-tail
                               (append (map (lambda (x) (if (vararg? x) (cadr x) x)) lhss-) assigned)
                               rhs-tail
                               (append (reverse assigns) stmts)
                               (car end)
                               (cons `(... ,temp) elts))))))

                ((vararg? R)
                 (let ((temp (make-ssavalue)))
                   `(block ,@(reverse stmts)
                           ,(make-assignment temp (cadr R))
                           ,@(reverse after)
                           ,(wrap `(= (tuple ,@lhss) ,temp))
                           (unnecessary (tuple ,@(reverse elts) (... ,temp))))))
                (else
                 (let ((temp (if (eventually-call? L) (gensy) (make-ssavalue))))
                   (loop (cdr lhss)
                         (cons L assigned)
                         (cdr rhss)
                         (if (symbol? temp)
                             (list* (make-assignment temp R) `(local-def ,temp) stmts)
                             (cons  (make-assignment temp R) stmts))
                         (cons (wrap (make-assignment L temp)) after)
                         (cons temp elts)))))))))

;; convert (lhss...) = x to tuple indexing
(define (lower-tuple-assignment lhss x (wrap (lambda (x i) x)))
  (let ((t (make-ssavalue)))
    `(block
      (= ,t ,x)
      ,@(let loop ((lhs lhss)
                   (i   1))
          (if (null? lhs) '()
              (cons (if (eventually-call? (car lhs))
                        ;; if this is a function assignment, avoid putting our ssavalue
                        ;; inside the function and instead create a capture-able variable.
                        ;; issue #22032
                        (let ((temp (gensy)))
                          `(block
                            (local-def ,temp)
                            (= ,temp (call (core getfield) ,t ,i))
                            ,(wrap `(= ,(car lhs) ,temp) i)))
                        (wrap
                          `(= ,(car lhs)
                            (call (core getfield) ,t ,i)) i))
                    (loop (cdr lhs)
                          (+ i 1)))))
      ,t)))

;; make an expression safe for multiple evaluation
;; for example a[f(x)] => (temp=f(x); a[temp])
;; returns a pair (expr . assignments)
;; where 'assignments' is a list of needed assignment statements
(define (remove-argument-side-effects e)
  (if (not (pair? e))
      (cons e '())
      (let ((a '()))
        (define (arg-to-temp x)
          (cond ((effect-free? x)  x)
                ((or (eq? (car x) '...) (eq? (car x) '&))
                 `(,(car x) ,(arg-to-temp (cadr x))))
                ((eq? (car x) 'kw)
                 `(,(car x) ,(cadr x) ,(arg-to-temp (caddr x))))
                (else
                 (let ((g (make-ssavalue)))
                   (begin (set! a (cons `(= ,g ,x) a))
                          g)))))
        (if (eq? (car e) 'let)
          (cons (arg-to-temp e) (reverse a))
          (cons (cons (car e) (map arg-to-temp (cdr e)))
                (reverse a))))))

(define (lower-kw-call f args)
  (let* ((para (if (has-parameters? args) (cdar args) '()))
         (args (if (has-parameters? args) (cdr args) args)))
    (let* ((parg-stmts (remove-argument-side-effects `(call ,f ,@args)))
           (call-ex    (car parg-stmts))
           (fexpr      (cadr call-ex))
           (cargs      (cddr call-ex)))
      `(block
        ,.(cdr parg-stmts)
        ,(receive
          (kws pargs) (separate kwarg? cargs)
          (lower-kw-call- fexpr (append! kws para) pargs))))))

(define (lower-kw-call- fexpr kw pa)
  (define (kwcall-unless-empty f pa kw-container-test kw-container)
    `(if (call (top isempty) ,kw-container-test)
         (call ,f ,@pa)
         (call (core kwcall) ,kw-container ,f ,@pa)))

  (let ((f            (if (sym-ref? fexpr) fexpr (make-ssavalue)))
        (kw-container (make-ssavalue)))
    `(block
      ,@(if (eq? f fexpr) '() `((= ,f, fexpr)))
      (= ,kw-container ,(lower-named-tuple kw
                                           (lambda (name) (string "keyword argument \"" name
                                                                  "\" repeated in call to \"" (deparse fexpr) "\""))
                                           "keyword argument"
                                           "keyword argument syntax"
                                           #t))
      ,(if (every vararg? kw)
           (kwcall-unless-empty f pa kw-container kw-container)
           `(call (core kwcall) ,kw-container ,f ,@pa)))))

;; convert `a+=b` to `a=a+b`
(define (expand-update-operator- op op= lhs rhs declT)
  (let* ((e      (remove-argument-side-effects lhs))
         (newlhs (car e))
         (temp   (and (eq? op= '|.=|)
                      (pair? newlhs)
                      (not (or (eq? (car newlhs) 'ref)
                               (and (eq? (car newlhs) '|.|) (length= newlhs 3))))
                      (make-ssavalue)))
         (e      (if temp
                     (cons temp (append (cdr e) (list `(= ,temp ,newlhs))))
                     e))
         (newlhs (or temp newlhs)))
    (if (and (pair? lhs) (eq? (car lhs) 'tuple))
        (let loop ((a (cdr newlhs))
                   (b (cdr lhs)))
          (if (pair? a)
              ;; if remove-argument-side-effects needed to replace an expression with
              ;; an ssavalue, then it can't be updated by assignment. issue #30062
              (begin (if (and (ssavalue? (car a)) (not (ssavalue? (car b))))
                         (error (string "invalid multiple assignment location \"" (deparse (car b)) "\"")))
                     (loop (cdr a) (cdr b))))))
    `(block ,@(cdr e)
            ,(if (null? declT)
                 `(,op= ,newlhs (call ,op ,newlhs ,rhs))
                 `(,op= ,newlhs (call ,op (:: ,newlhs ,(car declT)) ,rhs))))))

(define (partially-expand-ref e)
  (let ((a    (cadr e))
        (idxs (cddr e)))
    (let* ((reuse (and (pair? a)
                       (contains (lambda (x) (or (eq? x 'begin) (eq? x 'end)))
                                 idxs)))
           (arr   (if reuse (make-ssavalue) a))
           (stmts (if reuse `((= ,arr ,a)) '())))
      (receive
       (new-idxs stuff) (process-indices arr idxs)
       `(block
         ,@(append stmts stuff)
         (call (top getindex) ,arr ,@new-idxs))))))

(define (expand-update-operator op op= lhs rhs . declT)
  (cond ((and (pair? lhs) (eq? (car lhs) 'ref))
         ;; expand indexing inside op= first, to remove "begin", "end", and ":"
         (let* ((ex (partially-expand-ref lhs))
                (stmts (butlast (cdr ex)))
                (refex (last    (cdr ex)))
                (nuref `(ref ,(caddr refex) ,@(cdddr refex))))
           `(block ,@stmts
                   ,(expand-update-operator- op op= nuref rhs declT))))
        ((and (pair? lhs) (eq? (car lhs) '|::|))
         ;; (+= (:: x T) rhs)
         (let ((e (remove-argument-side-effects (cadr lhs)))
               (T (caddr lhs)))
           `(block ,@(cdr e)
                   ,(expand-update-operator op op= (car e) rhs T))))
        (else
         (if (and (pair? lhs) (eq? op= '=)
                  (not (memq (car lhs) '(|.| tuple vcat ncat typed_hcat typed_vcat typed_ncat))))
             (error (string "invalid assignment location \"" (deparse lhs) "\"")))
         (expand-update-operator- op op= lhs rhs declT))))

(define (lower-update-op e)
  (expand-forms
   (let ((str (string (car e))))
     (expand-update-operator
      (symbol (string.sub str 0 (- (length str) 1)))
      (if (= (string.char str 0) #\.) '.= '=)
      (cadr e)
      (caddr e)))))

(define (expand-and e)
  (let ((e (cdr (flatten-ex '&& e))))
    (let loop ((tail e))
      (if (null? tail)
          '(true)
          (if (null? (cdr tail))
              (car tail)
              `(if ,(car tail)
                   ,(loop (cdr tail))
                   (false)))))))

(define (expand-or e)
  (let ((e (cdr (flatten-ex '|\|\|| e))))
    (let loop ((tail e))
      (if (null? tail)
          '(false)
          (if (null? (cdr tail))
              (car tail)
              (if (symbol-like? (car tail))
                  `(if ,(car tail) ,(car tail)
                       ,(loop (cdr tail)))
                  (let ((g (make-ssavalue)))
                    `(block (= ,g ,(car tail))
                            (if ,g ,g
                                ,(loop (cdr tail)))))))))))

(define (expand-for lhss itrs body)
  (define (outer? x) (and (pair? x) (eq? (car x) 'outer)))
  (let ((copied-vars  ;; variables not declared `outer` are copied in the innermost loop
         ;; TODO: maybe filter these to remove vars not assigned in the loop
         (delete-duplicates
          (filter-not-underscore
                  (apply append
                         (map lhs-vars
                              (filter (lambda (x) (not (outer? x))) (butlast lhss))))))))
    `(break-block
      loop-exit
      ,(let nest ((lhss lhss)
                  (itrs itrs))
         (if (null? lhss)
             body
             (let* ((coll  (make-ssavalue))
                    (next  (gensy))
                    (state (make-ssavalue))
                    (outer (outer? (car lhss)))
                    (lhs   (if outer (cadar lhss) (car lhss)))
                    (body
                     `(block
                       ,@(if (not outer)
                             (map (lambda (v) `(local ,v)) (lhs-vars lhs))
                             '())
                       ,(lower-tuple-assignment (list lhs state) next)
                       ,(nest (cdr lhss) (cdr itrs))))
                    (body
                     (if (null? (cdr lhss))
                         `(break-block
                           loop-cont
                           (soft-let (block ,@(map (lambda (v) `(= ,v ,v)) copied-vars))
                             ,body))
                         `(scope-block ,body))))
               `(block (= ,coll ,(car itrs))
                       (local ,next)
                       (= ,next (call (top iterate) ,coll))
                       ;; TODO avoid `local declared twice` error from this
                       ;;,@(if outer `((local ,lhs)) '())
                       ,@(if outer `((require-existing-local ,lhs)) '())
                       (if (call (top not_int) (call (core ===) ,next (null)))
                           (_do_while
                            (block ,body
                                   (= ,next (call (top iterate) ,coll ,state)))
                            (call (top not_int) (call (core ===) ,next (null))))))))))))

;; wrap `expr` in a function appropriate for consuming values from given ranges
(define (func-for-generator-ranges expr range-exprs flat outervars)
  (let* ((vars    (map cadr range-exprs))
         (argname (if (and (length= vars 1) (symbol? (car vars)))
                      (car vars)
                      (gensy)))
         (myvars  (lhs-vars `(tuple ,@vars)))
         (splat (cond ((eq? argname (car vars))  '())
                      ((length= vars 1)
                       `(,@(map (lambda (v) `(local ,v)) myvars)
                         (= ,(car vars) ,argname)))
                      (else
                       `(,@(map (lambda (v) `(local ,v)) myvars)
                         (= (tuple ,@vars) ,argname))))))
    (cond
     ((eq? expr argname)
      ;; use `identity` for x->x
      `(top identity))
      ;; TODO: deprecate this (#18621):
     ((and (null? splat)
           (length= expr 3) (eq? (car expr) 'call)
           (eq? (caddr expr) argname)
           (underscore-symbol? argname)
           (not (dotop-named? (cadr expr)))
           (not (expr-contains-eq argname (cadr expr))))
      ;; eta reduce `_->f(_)` => `f`
      (cadr expr))
     (else
      (let ((expr (cond ((and flat (pair? expr) (eq? (car expr) 'generator))
                         (expand-generator expr #f (delete-duplicates (append outervars myvars))))
                        ((and flat (pair? expr) (eq? (car expr) 'flatten))
                         (expand-generator (cadr expr) #t (delete-duplicates (append outervars myvars))))
                        ((pair? outervars)
                         `(let (block ,@(map (lambda (v) `(= ,v ,v)) (filter-not-underscore outervars)))
                            ,expr))
                        (else expr))))
        `(-> ,argname (block ,@splat ,expr)))))))

(define (expand-generator e flat outervars)
  (let* ((expr  (cadr e))
         (filt? (eq? (car (caddr e)) 'filter))
         (range-exprs (if filt? (cddr (caddr e)) (cddr e)))
         (ranges (map caddr range-exprs))
         (iter (if (length= ranges 1)
                   (car ranges)
                   `(call (top product) ,@ranges)))
         (iter (if filt?
                   `(call (top Filter)
                          ,(func-for-generator-ranges (cadr (caddr e)) range-exprs #f '())
                          ,iter)
                   iter))
         (gen  `(call (top Generator)
                      ,(func-for-generator-ranges expr range-exprs flat outervars)
                      ,iter)))
    (expand-forms
     (if flat
         `(call (top Flatten) ,gen)
         gen))))

(define (ref-to-view expr)
  (cond ((and (pair? expr) (eq? (car expr) 'ref))
         (let* ((ex (partially-expand-ref expr))
                (stmts (butlast (cdr ex)))
                (refex (last    (cdr ex)))
                (nuref `(call (top dotview) ,(caddr refex) ,@(cdddr refex))))
           `(block ,@stmts ,nuref)))
        ((and (length= expr 3) (eq? (car expr) '|.|))
         `(call (top dotgetproperty) ,(cadr expr) ,(caddr expr)))
        (else expr)))

; lazily fuse nested calls to expr == f.(args...) into a single broadcast call,
; or a broadcast! call if lhs is non-null.
(define (expand-fuse-broadcast lhs rhs)
  (define (fuse? e) (and (pair? e) (eq? (car e) 'fuse)))
  (define (dot-to-fuse e (top #f)) ; convert e == (. f (tuple args)) to (fuse f args)
    (define (make-fuse f args) ; check for nested (fuse f args) exprs and combine
      (define (split-kwargs args) ; return (cons keyword-args positional-args) extracted from args
        (define (sk args kwargs pargs)
          (if (null? args)
              (cons kwargs pargs)
              (if (kwarg? (car args))
                  (sk (cdr args) (cons (car args) kwargs) pargs)
                  (sk (cdr args) kwargs (cons (car args) pargs)))))
        (if (has-parameters? args)
            (sk (reverse (cdr args)) (cdar args) '())
            (sk (reverse args) '() '())))
      (let* ((kws+args (split-kwargs args)) ; fusing occurs on positional args only
             (kws (car kws+args))
             (kws (if (null? kws) kws (list (cons 'parameters kws))))
             (args (map dot-to-fuse (cdr kws+args)))
             (make `(call (top ,(if (null? kws) 'broadcasted 'broadcasted_kwsyntax)) ,@kws ,f ,@args)))
        (if top (cons 'fuse make) make)))
    (cond ((and (length= e 3) (eq? (car e) '|.|))
           (let ((f (cadr e)) (x (caddr e)))
             (cond ((or (atom? x) (eq? (car x) 'quote) (eq? (car x) 'inert) (eq? (car x) '$))
                    `(call (top getproperty) ,f ,x))
                   ((eq? (car x) 'tuple)
                    (if (and (eq? (identifier-name f) '^) (length= x 3) (integer? (caddr x)))
                        (make-fuse '(top literal_pow)
                                   (list f (cadr x) (expand-forms `(call (call (core apply_type) (top Val) ,(caddr x))))))
                        (make-fuse f (cdr x))))
                   (else
                    (error (string "invalid syntax \"" (deparse e) "\""))))))
          ((and (pair? e) (eq? (car e) 'call))
           (define (make-fuse- f x)
             (if (and (eq? (identifier-name f) '^) (length= x 2) (integer? (cadr x)))
                 (make-fuse '(top literal_pow)
                            (list f (car x) (expand-forms `(call (call (core apply_type) (top Val) ,(cadr x))))))
                 (make-fuse f x)))
           (let ((f (cadr e)))
             (cond ((dotop-named? f)
                    (make-fuse- (undotop f) (cddr e)))
                   ;; (.+)(a, b) is parsed as (call (|.| +) a b), but we still want it to fuse
                   ((and (length= f 2) (eq? (car f) '|.|))
                    (make-fuse- (cadr f) (cddr e)))
                   (else
                     e))))
          ((and (pair? e) (eq? (car e) 'comparison))
           (dot-to-fuse (expand-compare-chain (cdr e)) top))
          ((and (pair? e) (eq? (car e) '.&&))
           (make-fuse '(top andand) (cdr e)))
          ((and (pair? e) (eq? (car e) '|.\|\||))
           (make-fuse '(top oror) (cdr e)))
          (else e)))
  (let ((e (dot-to-fuse rhs #t)) ; an expression '(fuse func args) if expr is a dot call
        (lhs-view (ref-to-view lhs))) ; x[...] expressions on lhs turn in to view(x, ...) to update x in-place
    (if (fuse? e)
        ; expanded to a fuse op call
        (if (null? lhs)
            (expand-forms `(call (top materialize) ,(cdr e)))
            (expand-forms `(call (top materialize!) ,lhs-view ,(cdr e))))
        ; expanded to something else (like a getfield)
        (if (null? lhs)
            (expand-forms e)
            (expand-forms `(call (top materialize!) ,lhs-view
                                 (call (top broadcasted) (top identity) ,e)))))))


(define (expand-where body var)
  (let* ((bounds (analyze-typevar var))
         (v  (car bounds)))
    `(let (= ,v ,(bounds-to-TypeVar bounds))
       (call (core UnionAll) ,v ,body))))

(define (expand-wheres body vars)
  (if (null? vars)
      body
      (expand-where (expand-wheres body (cdr vars)) (car vars))))

; given e = (curly T params...), return (newparams . whereparams) where any <:X expression
; in params is converted to T and T<:X is added to whereparams; similarly for >:X.
; (This implements the syntactic sugar Foo{<:Bar} --> Foo{T} where T<:Bar.)
(define (extract-implicit-whereparams e)
  (define (extract params newparams whereparams)
    (if (null? params)
        (cons (reverse newparams) (reverse whereparams))
        (let ((p (car params)))
          (if (and (length= p 2) (or (eq? (car p) '|<:|) (eq? (car p) '|>:|)))
              (let ((T (gensy)))
                (extract (cdr params) (cons T newparams) (cons (list (car p) T (cadr p)) whereparams)))
              (extract (cdr params) (cons p newparams) whereparams)))))
  (extract (cddr e) '() '()))

(define (named-tuple-expr names values)
  `(call (curly (core NamedTuple) (tuple ,@names))
         ;; NOTE: don't use `tuple` head, so an assignment expression as a value
         ;; doesn't turn this into another named tuple.
         (call (core tuple) ,@values)))

(define (lower-named-tuple lst
                           (dup-error-fn (lambda (name) (string "field name \"" name "\" repeated in named tuple")))
                           (name-str     "named tuple field")
                           (syntax-str   "named tuple element")
                           (call-with-keyword-arguments? #f))
  (let* ((names (apply append
                       (map (lambda (x)
                              (cond ((symbol? x) (list x))
                                    ((and (or (assignment? x) (kwarg? x)) (symbol? (cadr x)))
                                     (list (cadr x)))
                                    ((and (length= x 3) (eq? (car x) '|.|))
                                     (list (cadr (caddr x))))
                                    (else '())))
                            lst)))
         (dups (has-dups names)))
    (if dups
        (error (dup-error-fn (car dups)))))
  (define (not-vararg x)
    (if (vararg? x)
        (error (string "\"...\" expression cannot be used as " name-str " value"))
        x))
  (define (to-nt n v)
    (if (null? n)
        #f
        (named-tuple-expr (reverse! (map quotify n)) (reverse v))))
  (define (merge old new)
    (if old
        (if new
            `(call (top merge) ,old ,new)
            old)
        new))
  (let loop ((L             lst)
             (current-names '())
             (current-vals  '())
             (expr          #f))
    (if (null? L)
        (or (merge expr (to-nt current-names current-vals))
            ;; if that result is #f the named tuple is empty
            '(call (core NamedTuple)))
        (let ((el (car L)))
          (cond ((or (assignment? el) (kwarg? el))
                 (if (not (symbol? (cadr el)))
                     (error (string "invalid " name-str " name \"" (deparse (cadr el)) "\"")))
                 (not-vararg (caddr el))
                 (loop (cdr L)
                       (cons (cadr el) current-names)
                       (cons (caddr el) current-vals)
                       expr))
                ((symbol? el)  ;; x  =>  x = x
                 (loop (cdr L)
                       (cons el current-names)
                       (cons el current-vals)
                       expr))
                ((and (length= el 3) (eq? (car el) '|.|)   ;; a.x  =>  x = a.x
                      (quoted-sym? (caddr el)))
                 (loop (cdr L)
                       (cons (cadr (caddr el)) current-names)
                       (cons el current-vals)
                       expr))
                ((and (length= el 4) (eq? (car el) 'call) (eq? (cadr el) '=>))
                 (loop (cdr L)
                       '()
                       '()
                       (merge (merge expr (to-nt current-names current-vals))
                              (named-tuple-expr (list (caddr el)) (list (not-vararg (cadddr el)))))))
                ((vararg? el)
                 (loop (cdr L)
                       '()
                       '()
                       (let ((current (merge expr (to-nt current-names current-vals))))
                         (if current
                             (merge current (cadr el))
                             `(call (top merge) (call (top NamedTuple)) ,(cadr el))))))
                ((and call-with-keyword-arguments? (has-parameters? L))
                 (error "more than one semicolon in argument list"))
                (else
                 (error (string "invalid " syntax-str " \"" (deparse el) "\""))))))))

(define (expand-condition cnd)
  (let* ((blk? (and (pair? cnd) (eq? (car cnd) 'block)))
         (stmts (if blk? (cdr (butlast cnd)) '()))
         (test  (if blk? (last cnd) cnd)))
    (if (and (pair? test) (memq (car test) '(&& |\|\||)))
        (let* ((clauses `(,(car test) ,@(map expand-forms (cdr (flatten-ex (car test) test)))))
               (clauses (if (null? (cdr clauses))
                            (if (eq? (car clauses) '&&) '(true) '(false))
                            clauses)))
          (if blk?
              `(block ,@(map expand-forms stmts) ,clauses)
              clauses))
        (expand-forms cnd))))

(define (expand-if e)
  (list* (car e) (expand-condition (cadr e)) (map expand-forms (cddr e))))

(define (expand-while e)
  `(break-block loop-exit
                (_while ,(expand-condition (cadr e))
                        (break-block loop-cont
                                     (scope-block ,(blockify (expand-forms (caddr e))))))))

(define (expand-vcat e
                     (vcat '((top vcat)))
                     (hvcat '((top hvcat)))
                     (hvcat_rows '((top hvcat_rows))))
  (let ((a (cdr e)))
    (if (any assignment? a)
        (error (string "misplaced assignment statement in \"" (deparse e) "\"")))
    (if (has-parameters? a)
        (error "unexpected semicolon in array expression")
        (expand-forms
         (if (any (lambda (x)
                    (and (pair? x) (eq? (car x) 'row)))
                  a)
             ;; convert nested hcat inside vcat to hvcat
             (let ((rows (map (lambda (x)
                                (if (and (pair? x) (eq? (car x) 'row))
                                    (cdr x)
                                    (list x)))
                              a)))
               ;; in case there is splatting inside `hvcat`, collect each row as a
               ;; separate tuple and pass those to `hvcat_rows` instead (ref #38844)
               (if (any (lambda (row) (any vararg? row)) rows)
                   `(call ,@hvcat_rows ,@(map (lambda (x) `(tuple ,@x)) rows))
                   `(call ,@hvcat
                          (tuple ,@(map length rows))
                          ,@(apply append rows))))
             `(call ,@vcat ,@a))))))

(define (expand-ncat e (hvncat '((top hvncat))))
  (define (is-row a) (and (pair? a)
                          (or (eq? (car a) 'row)
                              (eq? (car a) 'nrow))))
  (define (is-1d a) (not (any is-row a)))
  (define (sum xs) (foldl + 0 xs))
  (define (get-shape a is-row-first d)
    (define (zip xss) (apply map list xss))
    (define (get-next x)
      (cond ((or (not (is-row x))
                 (and (eq? (car x) 'nrow) (> d (1+ (cadr x))))
                 (and (eq? (car x) 'row) (> d 1)))
             (list x))
            ((eq? (car x) 'nrow) (cddr x))
            (else (cdr x))))
    ; describe the shape of the concatenation
    (cond ((or (= d 0)
               (and (not is-row-first) (= d 1)))
           (length a))
          ((and is-row-first (= d 3))
           (get-shape a is-row-first (1- d)))
          (else
           (let ((ashape
                 (map (lambda (x)
                        (get-shape (get-next x) is-row-first (1- d)))
                      a)))
             (if (pair? (car ashape))
                 (let ((zipashape (zip ashape)))
                   (cons (sum (car zipashape))
                         (cons (car zipashape)
                               (map (lambda (x)
                                      (apply append x))
                                    (cdr zipashape)))))
                 (list (sum ashape) ashape))))))
  (define (get-dims a is-row-first d)
    (cond ((and (< d 2) (not (is-row (car a))))
           (list (length a)))
          ((= d 1)
           (list (car (get-dims (cdar a) is-row-first 0)) (length a)))
          ((and (= d 3) is-row-first)
           (get-dims a is-row-first 2))
          (else
           (let ((anext (if (and (pair? (car a))
                                 (eq? (caar a) 'nrow)
                                 (= d (1+ (cadar a))))
                            (cddar a)
                            (list (car a)))))
             (cons (length a) (get-dims anext is-row-first (1- d)))))))
  (define (is-balanced s)
    ; determine whether there are exactly the same number of elements along each axis
    (= 0 (sum (map (lambda (x y)
                     (sum (map (lambda (z)
                                 (- z y))
                               x)))
                   (cdr s) (map car (cdr s))))))
  (define (hasrows-flatten a)
    ; (car <result>) stores if a row was observed
    (foldl (lambda (x y)
             (let ((r (car y))
                   (yt (cdr y)))
               (if (is-row x)
                   (if (eq? (car x) 'nrow)
                       (let* ((raflat (append (hasrows-flatten (cddr x))))
                              (aflat (cdr raflat))
                              (rinner (car raflat))
                              (r (if (null? (or r rinner))
                                     (and r rinner)
                                     r)))
                         (if (and (not (null? r))
                                  (or (null? rinner) (and (not r) rinner))
                                  (and (= (cadr x) 2) r))
                             (error "cannot mix space and ;; separators in an array expression, except to wrap a line"))
                         (cons (if (and (= (cadr x) 2) (null? r))
                                   #f
                                   r)
                               (append aflat yt)))
                     (if (or (null? r) r)
                         (cons #t (append (reverse (cdr x)) yt))
                         (error "cannot mix space and ;; separators in an array expression, except to wrap a line")))
                 (cons r (cons x yt)))))
           (list '()) a))
  (define (tf a) (if a '(true) '(false)))
  (define (tuplize s)
    (cons 'tuple (reverse (map (lambda (x)
                                 (cons 'tuple x))
                               (cons (list (car s)) (cdr s))))))
  (let* ((d (cadr e))
         (a (cddr e))
         (raflat (hasrows-flatten a))
         (r (car raflat))
         (is-row-first (if (null? r) #f r))
         (aflat (reverse (cdr raflat))))
    (if (any assignment? aflat)
        (error (string "misplaced assignment statement in \"" (deparse e) "\"")))
    (if (has-parameters? aflat)
        (error "unexpected parameters in array expression"))
    (expand-forms
      (if (is-1d a)
          `(call ,@hvncat ,d ,@aflat)
          (if (any vararg? aflat)
              (error (string "Splatting ... in an hvncat with multiple dimensions is not supported"))
              (let ((shape (get-shape a is-row-first d)))
                (if (is-balanced shape)
                    (let ((dims `(tuple ,@(reverse (get-dims a is-row-first d)))))
                     `(call ,@hvncat ,dims ,(tf is-row-first) ,@aflat))
                    `(call ,@hvncat ,(tuplize shape) ,(tf is-row-first) ,@aflat))))))))

(define (maybe-ssavalue lhss x in-lhs?)
  (cond ((or (and (not (in-lhs? x lhss)) (symbol? x))
             (ssavalue? x))
          x)
        ((and (pair? lhss) (vararg? (last lhss))
              (eventually-call? (cadr (last lhss))))
         (gensy))
        (else (make-ssavalue))))

(define (expand-property-destruct lhs x)
  (if (not (length= lhs 1))
      (error (string "invalid assignment location \"" (deparse `(tuple ,lhs)) "\"")))
  (let* ((lhss (cdar lhs))
         (xx   (maybe-ssavalue lhss x memq))
         (ini  (if (eq? x xx) '() (list (sink-assignment xx (expand-forms x))))))
    `(block
       ,@ini
       ,@(map
           (lambda (field)
             (let ((prop (cond ((symbol? field) field)
                               ((and (pair? field) (eq? (car field) '|::|) (symbol? (cadr field)))
                                (cadr field))
                               (else
                                (error (string "invalid assignment location \"" (deparse `(tuple ,lhs)) "\""))))))
               (expand-forms `(= ,field (call (top getproperty) ,xx (quote ,prop))))))
           lhss)
       (unnecessary ,xx))))

;; implement tuple destructuring, possibly with slurping
;;
;; `i`:    index of the current lhs arg
;; `lhss`: remaining lhs args
;; `xx`:   the rhs, already either an ssavalue or something simple
;; `st`:   empty list if i=1, otherwise contains the iteration state
;; `n`:    total nr of lhs args
;; `end`:  car collects statements to be executed afterwards.
;;         In general, actual assignments should only happen after
;;         the whole iterator is desctructured (https://github.com/JuliaLang/julia/issues/40574)
;;
;; The `wrap` argument is a callback that will be called on all assignments to
;; symbols `lhss`, e.g. to insert a `const` declaration.
(define (destructure- i lhss xx n st end wrap)
  (if (null? lhss)
      '()
      (let* ((lhs  (car lhss))
             (wrapfirst (lambda (x i) (if (= i 1) (wrap x) x)))
             (lhs- (cond ((or (symbol? lhs) (ssavalue? lhs))
                          lhs)
                         ((vararg? lhs)
                          (let ((lhs- (cadr lhs)))
                            (if (or (symbol? lhs-) (ssavalue? lhs-))
                                lhs
                                `(|...| ,(if (eventually-call? lhs-)
                                             (gensy)
                                             (make-ssavalue))))))
                         ;; can't use ssavalues if it's a function definition
                         ((eventually-call? lhs) (gensy))
                         (else (make-ssavalue)))))
        (if (and (vararg? lhs) (any vararg? (cdr lhss)))
            (error "multiple \"...\" on lhs of assignment"))
        (if (not (eq? lhs lhs-))
            (if (vararg? lhs)
                (set-car! end (cons (expand-forms (wrap `(= ,(cadr lhs) ,(cadr lhs-)))) (car end)))
                (set-car! end (cons (expand-forms (wrap `(= ,lhs ,lhs-))) (car end)))))
        (if (vararg? lhs-)
            (if (= i n)
                (if (underscore-symbol? (cadr lhs-))
                    '()
                    (list (expand-forms
                            (wrap `(= ,(cadr lhs-) (call (top rest) ,xx ,@(if (eq? i 1) '() `(,st))))))))
                (let ((tail (if (eventually-call? lhs) (gensy) (make-ssavalue))))
                  (cons (expand-forms
                          (lower-tuple-assignment
                            (list (cadr lhs-) tail)
                            `(call (top split_rest) ,xx ,(- n i) ,@(if (eq? i 1) '() `(,st))) wrapfirst))
                        (destructure- 1 (cdr lhss) tail (- n i) st end wrap))))
            (cons (expand-forms
                    (lower-tuple-assignment
                      (if (= i n)
                          (list lhs-)
                          (list lhs- st))
                      `(call (top indexed_iterate)
                             ,xx ,i ,@(if (eq? i 1) '() `(,st))) wrapfirst))
                  (destructure- (+ i 1) (cdr lhss) xx n st end wrap))))))

(define (expand-tuple-destruct lhss x (wrap identity))
  (define (sides-match? l r)
    ;; l and r either have equal lengths, or r has a trailing ...
    (cond ((null? l)          (null? r))
          ((vararg? (car l))  #t)
          ((null? r)          #f)
          ((vararg? (car r))  (null? (cdr r)))
          (else               (sides-match? (cdr l) (cdr r)))))
  (if (and (pair? x) (pair? lhss) (eq? (car x) 'tuple) (not (any assignment? (cdr x)))
           (not (has-parameters? (cdr x)))
           (sides-match? lhss (cdr x)))
      ;; (a, b, ...) = (x, y, ...)
      (expand-forms
       (tuple-to-assignments lhss x wrap))
      ;; (a, b, ...) = other
      (begin
        ;; like memq, but if lhs is (... sym), check against sym instead
        (define (in-lhs? x lhss)
          (if (null? lhss)
              #f
              (let ((l (car lhss)))
                (cond ((and (pair? l) (eq? (car l) '|...|))
                       (eq? (cadr l) x))
                      ((eq? l x) #t)
                      (else (in-lhs? x (cdr lhss)))))))
        ;; in-lhs? also checks for invalid syntax, so always call it first
        (let* ((xx  (maybe-ssavalue lhss x in-lhs?))
               (ini (if (eq? x xx) '() (list (sink-assignment xx (expand-forms x)))))
               (n   (length lhss))
               (st  (gensy))
               (end (list (list))))
          `(block
            ,@(if (> n 0) `((local ,st)) '())
            ,@ini
            ,@(destructure- 1 lhss xx n st end wrap)
            ,@(reverse (car end))
            (unnecessary ,xx))))))

;; move an assignment into the last statement of a block to keep more statements at top level
(define (sink-assignment lhs rhs)
  (if (and (pair? rhs) (eq? (car rhs) 'block))
      (let ((rr (reverse (cdr rhs))))
        `(block ,@(reverse (cdr rr))
                (= ,lhs ,(car rr))))
      `(= ,lhs ,rhs)))

(define (expand-forms e)
  (if (or (atom? e) (memq (car e) '(quote inert top core globalref module toplevel ssavalue null true false meta using import export public thismodule toplevel-only)))
      e
      (let ((ex (get expand-table (car e) #f)))
        (if ex
            (ex e)
            (cons (car e)
                  (map expand-forms (cdr e)))))))

(define (find pred e)
  (let loop ((xs e))
    (if (null? xs)
        #f
        (let ((elt (car xs)))
          (if (pred elt)
              elt
              (loop (cdr xs)))))))

(define (something e)
  (find (lambda (x) (not (equal? x '(null)))) e))

;; table mapping expression head to a function expanding that form
(define expand-table
  (table
   'function       expand-function-def
   '->             expand-arrow
   'let            expand-let
   'soft-let       (lambda (e) (expand-let e #f))
   'macro          expand-macro-def
   'struct         expand-struct-def
   'try            expand-try

   'lambda
   (lambda (e)
     `(lambda ,(map expand-forms (cadr e))
        ,@(if (length= e 3) '(()) '())
        ,@(map expand-forms (cddr e))))

   'opaque_closure
   (lambda (e)
     (let* ((argt  (something (list (expand-forms (cadr e)) #f)))
            (rt_lb (something (list (expand-forms (caddr e)) #f)))
            (rt_ub (something (list (expand-forms (cadddr e)) #f)))
            (allow-partial (caddddr e))
            (F             (cadddddr e))
            (isva (let* ((arglist (function-arglist F))
                         (lastarg (and (pair? arglist) (last arglist))))
                    (if (and argt (any (lambda (arg)
                                       (let ((arg (if (vararg? arg) (cadr arg) arg)))
                                         (not (symbol? arg))))
                                     arglist))
                        (error "Opaque closure argument type may not be specified both in the method signature and separately"))
                    (if (or (varargexpr? lastarg) (vararg? lastarg))
                        '(true) '(false))))
            (meth (caddr (caddr (expand-forms F)))) ;; `method` expr
            (lam       (cadddr meth))
            (sig-block (caddr meth))
            (sig-block (if (and (pair? sig-block) (eq? (car sig-block) 'block))
                           sig-block
                           `(block ,sig-block)))
            (stmts     (cdr (butlast sig-block)))
            (sig-svec  (last sig-block))
            (typ-svec  (caddr sig-svec))
            (tvars     (cddr (cadddr sig-svec)))
            (argtypes  (cdddr typ-svec))
            (functionloc (cadr (caddddr sig-svec))))
       (let* ((argtype   (foldl (lambda (var ex) `(call (core UnionAll) ,var ,ex))
                                (expand-forms `(curly (core Tuple) ,@argtypes))
                                (reverse tvars))))
         `(_opaque_closure ,(or argt argtype) ,rt_lb ,rt_ub ,isva ,(length argtypes) ,allow-partial ,functionloc ,lam))))

   'block
   (lambda (e)
     (cond ((null? (cdr e)) '(null))
           ((and (null? (cddr e))
                 (not (linenum? (cadr e))))
            (expand-forms (cadr e)))
           (else
            (cons 'block
                  (map expand-forms (cdr e))))))

   '|.|
   (lambda (e)
     (if (length= e 2)
         ;; e = (|.| op)
         `(call (top BroadcastFunction) ,(cadr e))
         ;; e = (|.| f x)
         (expand-fuse-broadcast '() e)))

   '.&&
   (lambda (e) (expand-fuse-broadcast '() e))
   '|.\|\||
   (lambda (e) (expand-fuse-broadcast '() e))

   '.=
   (lambda (e)
     (expand-fuse-broadcast (cadr e) (caddr e)))

   '|<:|
   (lambda (e) (expand-forms `(call |<:| ,@(cdr e))))
   '|>:|
   (lambda (e) (expand-forms `(call |>:| ,@(cdr e))))
   '-->
   (lambda (e) (expand-forms `(call --> ,@(cdr e))))

   'where
   (lambda (e) (expand-forms (expand-wheres (cadr e) (cddr e))))

   'const  expand-const-decl
   'atomic expand-atomic-decl
   'local  expand-local-or-global-decl
   'global expand-local-or-global-decl
   'local-def expand-local-or-global-decl

   '=
   (lambda (e)
     (define lhs (cadr e))
     (define (function-lhs? lhs)
       (and (pair? lhs)
            (or (eq? (car lhs) 'call)
                (eq? (car lhs) 'where)
                (and (eq? (car lhs) '|::|)
                     (pair? (cadr lhs))
                     (eq? (car (cadr lhs)) 'call)))))
     (define (assignment-to-function lhs e)  ;; convert '= expr to 'function expr
       (cons 'function (cdr e)))
     (cond
      ((function-lhs? lhs)
       (expand-forms (assignment-to-function lhs e)))
      ((and (pair? lhs)
            (eq? (car lhs) 'curly))
       (expand-unionall-def (cadr e) (caddr e)))
      ((assignment? (caddr e))
       ;; chain of assignments - convert a=b=c to `b=c; a=c`
       (let loop ((lhss (list lhs))
                  (rhs  (caddr e)))
         (if (and (assignment? rhs) (not (function-lhs? (cadr rhs))))
             (loop (cons (cadr rhs) lhss) (caddr rhs))
             (let ((rr (if (symbol-like? rhs) rhs (make-ssavalue))))
               (expand-forms
                `(block ,.(if (eq? rr rhs) '() `((= ,rr ,(if (assignment? rhs)
                                                             (assignment-to-function (cadr rhs) rhs)
                                                             rhs))))
                        ,@(map (lambda (l) `(= ,l ,rr))
                               lhss)
                        (unnecessary ,rr)))))))
      ((or (and (symbol-like? lhs) (valid-name? lhs))
           (globalref? lhs))
       (sink-assignment lhs (expand-forms (caddr e))))
      ((atom? lhs)
       (error (string "invalid assignment location \"" (deparse lhs) "\"")))
      (else
       (case (car lhs)
         ((|.|)
          ;; a.b =
          (let* ((a   (cadr lhs))
                 (b  (caddr lhs))
                 (rhs (caddr e)))
            (if (and (length= b 2) (eq? (car b) 'tuple))
                (error (string "invalid syntax \""
                               (string (deparse a) ".(" (deparse (cadr b)) ") = ...") "\"")))
            (let ((aa (if (symbol-like? a) a (make-ssavalue)))
                  (bb (if (or (atom? b) (symbol-like? b) (and (pair? b) (quoted? b)))
                          b (make-ssavalue)))
                  (rr (if (or (symbol-like? rhs) (atom? rhs)) rhs (make-ssavalue))))
              `(block
                ,.(if (eq? aa a)   '() (list (sink-assignment aa (expand-forms a))))
                ,.(if (eq? bb b)   '() (list (sink-assignment bb (expand-forms b))))
                ,.(if (eq? rr rhs) '() (list (sink-assignment rr (expand-forms rhs))))
                (call (top setproperty!) ,aa ,bb ,rr)
                (unnecessary ,rr)))))
         ((tuple)
          (let ((lhss (cdr lhs))
                (x    (caddr e)))
            (if (has-parameters? lhss)
                ;; property destructuring
                (expand-property-destruct lhss x)
                ;; multiple assignment
                (expand-tuple-destruct lhss x))))
         ((typed_hcat)
          (error "invalid spacing in left side of indexed assignment"))
         ((typed_vcat typed_ncat)
          (error "unexpected \";\" in left side of indexed assignment"))
         ((ref)
          ;; (= (ref a . idxs) rhs)
          (let ((a    (cadr lhs))
                (idxs (cddr lhs))
                (rhs  (caddr e)))
            (let* ((reuse (and (pair? a)
                               (contains (lambda (x) (eq? x 'end))
                                         idxs)))
                   (arr   (if reuse (make-ssavalue) a))
                   (stmts (if reuse `((= ,arr ,(expand-forms a))) '()))
                   (rrhs (and (pair? rhs) (not (ssavalue? rhs)) (not (quoted? rhs))))
                   (r    (if rrhs (make-ssavalue) rhs))
                   (rini (if rrhs (list (sink-assignment r (expand-forms rhs))) '())))
              (receive
               (new-idxs stuff) (process-indices arr idxs)
               `(block
                 ,@stmts
                 ,.(map expand-forms stuff)
                 ,@rini
                 ,(expand-forms
                   `(call (top setindex!) ,arr ,r ,@new-idxs))
                 (unnecessary ,r))))))
         ((|::|)
          ;; (= (|::| T) rhs) is an error
          (if (null? (cddr lhs))
              (error (string "invalid assignment location \"" (deparse lhs) "\"")))
          ;; (= (|::| x T) rhs)
          (let ((x (cadr lhs))
                (T (caddr lhs))
                (rhs (caddr e)))
            (let ((e (remove-argument-side-effects x)))
              (expand-forms
               `(block ,@(cdr e)
                       (decl ,(car e) ,T)
                       (= ,(car e) ,rhs))))))
         ((vcat ncat)
          ;; (= (vcat . args) rhs)
          (error "use \"(a, b) = ...\" to assign multiple values"))
         (else
          (error (string "invalid assignment location \"" (deparse lhs) "\"")))))))

   'abstract
   (lambda (e)
     (let ((sig (cadr e)))
       (expand-forms
        (receive (name params super) (analyze-type-sig sig)
                 (abstract-type-def-expr name params super)))))

   'primitive
   (lambda (e)
     (let ((sig (cadr e))
           (n   (caddr e)))
       (expand-forms
        (receive (name params super) (analyze-type-sig sig)
                 (primitive-type-def-expr n name params super)))))

   'comparison
   (lambda (e) (expand-forms (expand-compare-chain (cdr e))))

   'ref
   (lambda (e)
     (let ((args (cddr e)))
       (if (has-parameters? args)
           (error "unexpected semicolon in array expression")
           (expand-forms (partially-expand-ref e)))))

   'curly
   (lambda (e)
     (if (has-parameters? (cddr e))
         (error (string "unexpected semicolon in \"" (deparse e) "\"")))
     (if (any assignment? (cddr e))
         (error (string "misplaced assignment statement in \"" (deparse e) "\"" )))
     (let* ((p (extract-implicit-whereparams e))
            (curlyparams (car p))
            (whereparams (cdr p)))
       (if (null? whereparams)
           (expand-forms `(call (core apply_type) ,@(cdr e)))
           (expand-forms `(where (curly ,(cadr e) ,@curlyparams) ,@whereparams)))))

   'call
   (lambda (e)
     (if (length> e 2)
         (let ((f (cadr e)))
           (cond ((dotop-named? f)
                  (expand-fuse-broadcast '() `(|.| ,(undotop f) (tuple ,@(cddr e)))))
                 ;; "(.op)(...)"
                 ((and (length= f 2) (eq? (car f) '|.|))
                  (expand-fuse-broadcast '() `(|.| ,(cadr f) (tuple ,@(cddr e)))))
                 ((eq? f 'ccall)
                  (if (not (length> e 4)) (error "too few arguments to ccall"))
                  (let* ((cconv (cadddr e))
                         (have-cconv-expr (and (pair? cconv) (eq? (car cconv) 'cconv)))
                         (have-cconv (or have-cconv-expr
                                         (memq cconv '(cdecl stdcall fastcall thiscall llvmcall))))
                         (after-cconv (if have-cconv (cddddr e) (cdddr e)))
                         (name (caddr e))
                         (RT   (car after-cconv))
                         (argtypes (cadr after-cconv))
                         (args (cddr after-cconv)))
                        (begin
                          (if (not (and (pair? argtypes)
                                        (eq? (car argtypes) 'tuple)))
                              (if (and (pair? RT)
                                       (eq? (car RT) 'tuple))
                                  (error "ccall argument types must be a tuple; try \"(T,)\" and check if you specified a correct return type")
                                  (error "ccall argument types must be a tuple; try \"(T,)\"")))
                          (lower-ccall name RT (cdr argtypes) args
                                       (if have-cconv
                                           (if have-cconv-expr
                                               (cadr cconv)
                                               cconv)
                                           'ccall)
                                       (and have-cconv-expr (caddr cconv))))))
                 ((any kwarg? (cddr e))       ;; f(..., a=b, ...)
                  (expand-forms (lower-kw-call f (cddr e))))
                 ((has-parameters? (cddr e))  ;; f(...; ...)
                  (expand-forms
                   (if (null? (cdr (car (cddr e))))
                       ;; empty parameters block; issue #18845
                       `(call ,f ,@(cdddr e))
                       (lower-kw-call f (cddr e)))))
                 ((any vararg? (cddr e))
                  ;; call with splat
                  (let ((argl (cddr e)))
                    ;; wrap sequences of non-... arguments in tuple()
                    (define (tuple-wrap a run)
                      (if (null? a)
                          (if (null? run) '()
                              (list `(call (core tuple) ,.(reverse run))))
                          (let ((x (car a)))
                            (if (and (length= x 2)
                                     (eq? (car x) '...))
                                (if (null? run)
                                    (list* (cadr x)
                                           (tuple-wrap (cdr a) '()))
                                    (list* `(call (core tuple) ,.(reverse run))
                                           (cadr x)
                                           (tuple-wrap (cdr a) '())))
                                (tuple-wrap (cdr a) (cons x run))))))
                    (expand-forms
                     `(call (core _apply_iterate) (top iterate) ,f ,@(tuple-wrap argl '())))))

                 ((and (eq? (identifier-name f) '^) (length= e 4) (integer? (cadddr e)))
                  (expand-forms
                   `(call (top literal_pow) ,f ,(caddr e) (call (call (core apply_type) (top Val) ,(cadddr e))))))
                 (else
                  (map expand-forms e))))
         (map expand-forms e)))

   'do
   (lambda (e)
     (let* ((call (cadr e))
            (f    (cadr call))
            (argl (cddr call))
            (af   (caddr e)))
       (expand-forms
        (if (has-parameters? argl)
            `(call ,f ,(car argl) ,af ,@(cdr argl))
            `(call ,f ,af ,@argl)))))

   'tuple
   (lambda (e)
     (cond ((and (length> e 1) (pair? (cadr e)) (eq? (caadr e) 'parameters))
            (if (length= e 2)
                (expand-forms (lower-named-tuple (cdr (cadr e))))
                (error "unexpected semicolon in tuple")))
           ((any assignment? (cdr e))
            (expand-forms (lower-named-tuple (cdr e))))
           (else
            (expand-forms `(call (core tuple) ,@(cdr e))))))

   'braces    (lambda (e) (error "{ } vector syntax is discontinued"))
   'bracescat (lambda (e) (error "{ } matrix syntax is discontinued"))

   'string
   (lambda (e)
     (expand-forms
       `(call (top string)
              ,@(map (lambda (s)
                       (if (and (length= s 2) (eq? (car s) 'string) (string? (cadr s)))
                           (cadr s)
                           s))
                     (cdr e)))))

   '|::|
   (lambda (e)
     (if (not (length= e 3))
         (error "invalid \"::\" syntax"))
     (if (not (symbol-like? (cadr e)))
         `(call (core typeassert)
                ,(expand-forms (cadr e)) ,(expand-forms (caddr e)))
         (map expand-forms e)))

   'if expand-if
   'elseif expand-if
   'while expand-while

   'break
   (lambda (e)
     (if (pair? (cdr e))
         e
         '(break loop-exit)))

   'continue (lambda (e) '(break loop-cont))

   'for
   (lambda (e)
     (let ((ranges (if (eq? (car (cadr e)) 'block)
                       (cdr (cadr e))
                       (list (cadr e)))))
       (expand-forms (expand-for (map cadr ranges) (map caddr ranges) (caddr e)))))

   '&&     (lambda (e) (expand-forms (expand-and e)))
   '|\|\|| (lambda (e) (expand-forms (expand-or  e)))

   '&      (lambda (e) (error (string "invalid syntax " (deparse e))))

   '+=     lower-update-op
   '-=     lower-update-op
   '*=     lower-update-op
   '.*=    lower-update-op
   '/=     lower-update-op
   './=    lower-update-op
   '//=    lower-update-op
   './/=   lower-update-op
   '|\\=|  lower-update-op
   '|.\\=| lower-update-op
   '|.+=|  lower-update-op
   '|.-=|  lower-update-op
   '^=     lower-update-op
   '.^=    lower-update-op
   '÷=     lower-update-op
   '.÷=    lower-update-op
   '%=     lower-update-op
   '.%=    lower-update-op
   '|\|=|  lower-update-op
   '|.\|=|  lower-update-op
   '&=     lower-update-op
   '.&=     lower-update-op
   '$=     lower-update-op
   '⊻=     lower-update-op
   '.⊻=     lower-update-op
   '<<=    lower-update-op
   '.<<=    lower-update-op
   '>>=    lower-update-op
   '.>>=    lower-update-op
   '>>>=   lower-update-op
   '.>>>=   lower-update-op

   '|...|
   (lambda (e) (error "\"...\" expression outside call"))

   '$
   (lambda (e) (error "\"$\" expression outside quote"))

   'vect
   (lambda (e)
     (if (has-parameters? (cdr e))
         (error "unexpected semicolon in array expression"))
     (if (any assignment? (cdr e))
         (error (string "misplaced assignment statement in \"" (deparse e) "\"")))
     (expand-forms `(call (top vect) ,@(cdr e))))

   'hcat
   (lambda (e)
     (if (any assignment? (cdr e))
         (error (string "misplaced assignment statement in \"" (deparse e) "\"")))
     (expand-forms `(call (top hcat) ,@(cdr e))))

   'vcat expand-vcat

   'ncat expand-ncat

   'typed_hcat
   (lambda (e)
     (if (any assignment? (cddr e))
         (error (string "misplaced assignment statement in \"" (deparse e) "\"")))
     (expand-forms `(call (top typed_hcat) ,@(cdr e))))

   'typed_vcat
   (lambda (e)
     (let ((t (cadr e))
           (e (cdr e)))
       (expand-vcat e `((top typed_vcat) ,t) `((top typed_hvcat) ,t) `((top typed_hvcat_rows) ,t))))

   'typed_ncat
   (lambda (e)
     (let ((t (cadr e))
           (e (cdr e)))
       (expand-ncat e `((top typed_hvncat) ,t))))

   '|'|  (lambda (e) (expand-forms `(call |'| ,(cadr e))))

   'generator
   (lambda (e)
     (check-no-return e)
     (expand-generator e #f '()))

   'flatten
   (lambda (e) (expand-generator (cadr e) #t '()))

   'comprehension
   (lambda (e)
     (if (length> e 2)
         ;; backwards compat for macros that generate :comprehension exprs
         (expand-forms `(comprehension (generator ,@(cdr e))))
         (begin (if (and (eq? (caadr e) 'generator)
                         (any (lambda (x) (eq? x ':)) (cddr (cadr e))))
                    (error "comprehension syntax with `:` ranges has been removed"))
                (expand-forms `(call (top collect) ,(cadr e))))))

   'typed_comprehension
   (lambda (e)
     (expand-forms
      (or (and (eq? (caaddr e) 'generator)
               (let ((ranges (cddr (caddr e))))
                 (if (any (lambda (x) (eq? x ':)) ranges)
                     (error "comprehension syntax with `:` ranges has been removed"))
                 (and (every (lambda (x) (and (pair? x) (eq? (car x) '=)))
                             ranges)
                      ;; TODO: this is a hack to lower simple comprehensions to loops very
                      ;; early, to greatly reduce the # of functions and load on the compiler
                      (lower-comprehension (cadr e) (cadr (caddr e)) ranges))))
          `(call (top collect) ,(cadr e) ,(caddr e)))))

    'gc_preserve
    (lambda (e)
      (let* ((s (make-ssavalue))
             (r (make-ssavalue)))
        `(block
          (= ,s (gc_preserve_begin ,@(cddr e)))
          (= ,r ,(expand-forms (cadr e)))
          (gc_preserve_end ,s)
          ,r)))

    'line
    (lambda (e)
      (set! *current-desugar-loc* e)
      e)
    ))

(define (has-return? e)
  (expr-contains-p return? e (lambda (x) (not (function-def? x)))))

(define (check-no-return e)
  (if (has-return? e)
      (error "\"return\" not allowed inside comprehension or generator")))

(define (has-break-or-continue? e)
  (expr-contains-p (lambda (x) (and (pair? x) (memq (car x) '(break continue))))
                   e
                   (lambda (x) (not (and (pair? x)
                                         (memq (car x) '(for while)))))))

(define (lower-comprehension ty expr itrs)
  (check-no-return expr)
  (if (has-break-or-continue? expr)
      (error "break or continue outside loop"))
  (let ((result    (make-ssavalue))
        (idx       (gensy))
        (oneresult (make-ssavalue))
        (prod      (make-ssavalue))
        (isz       (make-ssavalue))
        (szunk     (make-ssavalue))
        (iv        (map (lambda (x) (make-ssavalue)) itrs)))

    ;; construct loops over all iterators
    (define (construct-loops itrs iv)
      (if (null? itrs)
          `(block (= ,oneresult ,expr)
                  (inbounds (true))
                  (if ,szunk
                      (call (top push!) ,result ,oneresult)
                      (call (top setindex!) ,result ,oneresult ,idx))
                  (inbounds pop)
                  (= ,idx (call (top add_int) ,idx 1)))
          `(for (= ,(cadr (car itrs)) ,(car iv))
                ,(construct-loops (cdr itrs) (cdr iv)))))

    (let ((overall-itr (if (length= itrs 1) (car iv) prod)))
      `(scope-block
        (block
         (local ,idx)
         ,.(map (lambda (v r) `(= ,v ,(caddr r))) iv itrs)
         ,.(if (length= itrs 1)
               '()
               `((= ,prod (call (top product) ,@iv))))
         (= ,isz (call (top IteratorSize) ,overall-itr))
         (= ,szunk (call (core isa) ,isz (top SizeUnknown)))
         (= ,result (call (top _array_for) ,ty ,overall-itr ,isz))
         (= ,idx (call (top first) (call (top LinearIndices) ,result)))
         ,(construct-loops (reverse itrs) (reverse iv))
         ,result)))))

(define (lhs-decls e)
  (cond ((symdecl? e)   (list e))
        ((and (pair? e)
              (or (eq? (car e) 'tuple)
                  (eq? (car e) 'parameters)))
         (apply append (map lhs-decls (cdr e))))
        (else '())))

(define (lhs-vars e)
  (map decl-var (lhs-decls e)))

(define (all-decl-vars e)  ;; map decl-var over every level of an assignment LHS
  (cond ((eventually-call? e) e)
        ((decl? e)   (decl-var e))
        ((and (pair? e) (eq? (car e) 'tuple))
         (cons 'tuple (map all-decl-vars (cdr e))))
        (else e)))

;; pass 2: identify and rename local vars

(define (find-assigned-vars e)
  (define vars '())
  (define (find-assigned-vars- e)
    (if (or (not (pair? e)) (quoted? e))
        '()
        (case (car e)
          ((lambda scope-block module toplevel)  '())
          ((method)
           (let ((v (decl-var (method-expr-name e))))
             (if (symbol? v)
                 (set! vars (cons v vars)))
             (if (not (length= e 2))
                 (find-assigned-vars- (caddr e)))))
          ((assign-const-if-global)
            ;; like v = val, except that if `v` turns out global(either
            ;; implicitly or by explicit `global`), it gains an implicit `const`
            (set! vars (cons (cadr e) vars)))
          ((=)
           (let ((v (decl-var (cadr e))))
             (find-assigned-vars- (caddr e))
             (if (or (ssavalue? v) (globalref? v) (underscore-symbol? v))
                 '()
                 (set! vars (cons v vars)))))
          (else
           (for-each find-assigned-vars- (cdr e))))))
  (find-assigned-vars- e)
  (delete-duplicates vars))

(define (find-decls kind e)
  (define vars '())
  (define (find-decls- e)
    (cond ((or (not (pair? e)) (quoted? e))
           '())
          ((memq (car e) '(lambda scope-block module toplevel))
           '())
          ((eq? (car e) kind)
           (if (underscore-symbol? (cadr e))
               '()
               (set! vars (cons (decl-var (cadr e)) vars))))
          (else
           (for-each find-decls- (cdr e)))))
  (find-decls- e)
  vars)

(define (find-local-decls e) (find-decls 'local e))
(define (find-local-def-decls e) (find-decls 'local-def e))
(define (find-global-decls e) (find-decls 'global e))

(define (find-scope-decl e kind)
  (expr-contains-p
   (lambda (x) (and (pair? x) (eq? (car x) kind) x))
   e
   (lambda (x) (not (and (pair? x)
                         (memq (car x) '(lambda scope-block module toplevel)))))))

(define (check-valid-name e)
  (or (valid-name? e)
      (error (string "invalid identifier name \"" e "\""))))

(define (push-var! tab var val) (put! tab var (cons val (get tab var #f))))
(define (pop-var! tab var) (put! tab var (cdr (get tab var))))

(define (make-scope (lam #f) (args '()) (locals '()) (globals '()) (sp '()) (renames '()) (prev #f)
                    (soft? #f) (hard? #f) (implicit-globals '()) (warn-vars #f))
  (let ((tab (if prev (scope:table prev) (table))))
    (for-each (lambda (v) (push-var! tab v v)) sp)
    (for-each (lambda (v) (push-var! tab v v)) locals)
    (for-each (lambda (pair) (push-var! tab (car pair) (cdr pair))) renames)
    (for-each (lambda (v) (push-var! tab v `(globalref (thismodule) ,v))) globals)
    (for-each (lambda (v) (push-var! tab v v)) args)
    (vector lam args locals globals sp renames prev soft? hard? implicit-globals warn-vars tab)))

(define (pop-scope! scope)
  (let ((tab (scope:table scope)))
    (for-each (lambda (v) (pop-var! tab v)) (scope:sp scope))
    (for-each (lambda (v) (pop-var! tab v)) (scope:locals scope))
    (for-each (lambda (pair) (pop-var! tab (car pair))) (scope:renames scope))
    (for-each (lambda (v) (pop-var! tab v)) (scope:globals scope))
    (for-each (lambda (v) (pop-var! tab v)) (scope:args scope))))

(define (scope:lam s)     (aref s 0))
(define (scope:args s)    (aref s 1))
(define (scope:locals s)  (aref s 2))
(define (scope:globals s) (aref s 3))
(define (scope:sp s)      (aref s 4))
(define (scope:renames s) (aref s 5))
(define (scope:prev s)    (aref s 6))
(define (scope:soft? s)   (aref s 7))
(define (scope:hard? s)   (aref s 8))
(define (scope:implicit-globals s) (aref s 9))
(define (scope:warn-vars s) (aref s 10))
(define (scope:table s)   (aref s 11))

(define (var-kind var scope (exclude-top-level-globals #f))
  (if scope
      (or (and (memq var (scope:args scope))    'argument)
          (and (memq var (scope:locals scope))  'local)
          (and (memq var (scope:globals scope))
              (if (and exclude-top-level-globals
                        (null? (lam:args (scope:lam scope)))
                        ;; don't inherit global decls from the outermost scope block
                        ;; in a top-level expression.
                        (or (not (scope:prev scope))
                            (not (scope:prev (scope:prev scope)))))
                  'none 'global))
          (and (memq var (scope:sp scope))      'static-parameter)
          (var-kind var (scope:prev scope) exclude-top-level-globals))
      'none))

(define (in-scope? var scope) (not (eq? (var-kind var scope) 'none)))

(define (warn-var?! v scope)
  (and scope
       (let ((w (scope:warn-vars scope)))
         (if (and w (has? w v))
             (begin (del! w v)
                    #t)
             (warn-var?! v (scope:prev scope))))))

(define (all-local-names scope)
  (define (all-lists s)
    (if s
        (list* (scope:args s) (scope:sp s) (scope:locals s) (all-lists (scope:prev s)))
        '()))
  (apply append (all-lists scope)))

;; returns lambdas in the form (lambda (args...) (locals...) body)
(define (resolve-scopes- e scope (sp '()) (loc #f))
  (cond ((symbol? e)
         (let ((val (and scope (get (scope:table scope) e #f))))
           (cond (val (car val))
                 ((underscore-symbol? e) e)
                 (else `(globalref (thismodule) ,e)))))
        ((or (not (pair? e)) (quoted? e) (memq (car e) '(toplevel symbolicgoto symboliclabel toplevel-only)))
         e)
        ((eq? (car e) 'global)
         (check-valid-name (cadr e))
         e)
        ((eq? (car e) 'assign-const-if-global)
           (if (eq? (var-kind (cadr e) scope) 'local)
               (if (length= e 2) (null) `(= ,@(cdr e)))
               `(const ,@(cdr e))))
        ((memq (car e) '(local local-def))
         (check-valid-name (cadr e))
         ;; remove local decls
         '(null))
        ((memq (car e) '(using import export public))
          ;; no scope resolution - identifiers remain raw symbols
          e)
        ((eq? (car e) 'require-existing-local)
         (if (not (in-scope? (cadr e) scope))
             (error "no outer local variable declaration exists for \"for outer\""))
         '(null))
        ((or (eq? (car e) 'softscope) (eq? (car e) 'hardscope))
         '(null))
        ((eq? (car e) 'locals)
         (let* ((names (filter (lambda (v)
                                 (and (not (gensym? v))
                                      (not (length= (string-split (string v) "#") 2))))
                               (all-local-names scope)))
                (names (delete-duplicates
                        (filter (lambda (v) (not (eq? v '||)))
                                (map unmangled-name names))))
                (d (make-ssavalue)))
           `(block (= ,d (call (call (core apply_type) (top Dict) (core Symbol) (core Any))))
                   ,@(map (lambda (v)
                            (let ((var (resolve-scopes- v scope)))
                              `(if (isdefined ,var)
                                   (call (top setindex!) ,d ,var (quote ,v)))))
                          names)
                   ,d)))
        ((eq? (car e) 'islocal)
         (if (memq (var-kind (cadr e) scope) '(global none))
             '(false)
             '(true)))
        ((eq? (car e) 'lambda)
         (let* ((args (lam:argnames e))
                (new-scope (make-scope e args '() '() sp '() scope))
                (body (resolve-scopes- (lam:body e) new-scope)))
           (pop-scope! new-scope)
           `(lambda ,(cadr e) ,(caddr e) ,body)))
        ((eq? (car e) 'scope-block)
         (let* ((blok            (cadr e)) ;; body of scope-block expression
                (lam             (scope:lam scope))
                (argnames        (lam:argnames lam))
                (toplevel?       (and (null? argnames) (eq? e (lam:body lam))))
                (current-locals  (caddr lam)) ;; locals created so far in our lambda
                (globals         (find-global-decls blok))
                (assigned        (find-assigned-vars blok))
                (locals-def      (find-local-def-decls blok))
                (local-decls     (find-local-decls blok))
                (hard?           (and (null? argnames) (or (scope:hard? scope)
                                                           (find-scope-decl blok 'hardscope))))
                (soft?           (and (null? argnames) (not hard?)
                                      (let ((ss (find-scope-decl blok 'softscope)))
                                        (cond ((not ss) (scope:soft? scope))
                                              ((equal? (cadr ss) '(true))  #t)
                                              ((equal? (cadr ss) '(false)) #f)
                                              (else (scope:soft? scope))))))
                (nonloc-assigned (filter (lambda (v) (and (not (memq v locals-def))
                                                          (not (memq v local-decls))))
                                         assigned))
                (implicit-globals (if toplevel? nonloc-assigned '()))
                (implicit-locals
                 (filter (if toplevel?
                             (lambda (v) #f)  ;; no implicit locals at top level
                             (lambda (v) (and (memq (var-kind v scope #t) '(none static-parameter))
                                              (not (and soft?
                                                        (or (memq v (scope:implicit-globals scope))
                                                            (defined-julia-global v))))
                                              (not (memq v globals)))))
                         nonloc-assigned))
                (locals-nondef   (delete-duplicates (append local-decls implicit-locals)))
                (need-rename?    (lambda (vars)
                                   (filter (lambda (v) (or (memq v current-locals) (in-scope? v scope)))
                                           vars)))
                (need-rename     (need-rename? locals-nondef))
                (need-rename-def (need-rename? locals-def))
                ;; new gensym names for conflicting variables
                (renamed         (map named-gensy need-rename))
                (renamed-def     (map named-gensy need-rename-def))
                (newnames        (append (diff locals-nondef need-rename) renamed))
                (newnames-def    (append (diff locals-def need-rename-def) renamed-def))
                (warn-vars
                 (and (not toplevel?) (null? argnames) (not soft?) (not hard?)
                      (let ((vars (filter (lambda (v)
                                            (and (or (memq v (scope:implicit-globals scope))
                                                     (defined-julia-global v))
                                                 (eq? (var-kind v scope) 'none)
                                                 (not (memq v globals))))
                                          nonloc-assigned)))
                        (if (pair? vars)
                            (let ((t (table)))
                              (for-each (lambda (v) (put! t v #t))
                                        vars)
                              t)
                            #f)))))
           (for-each (lambda (v)
                       (if (or (memq v locals-def) (memq v local-decls))
                           (error (string "variable \"" v "\" declared both local and global")))
                       (if (and (null? argnames) (memq (var-kind v scope) '(argument local)))
                           (error (string "`global " v "`: " v " is a local variable in its enclosing scope"))))
                     globals)
           (if (and (pair? argnames) (eq? e (lam:body lam)))
               (for-each (lambda (v)
                           (if (memq v argnames)
                               (error (string "local variable name \"" v "\" conflicts with an argument"))))
                         local-decls))
           (for-each (lambda (lst)
                       (for-each (lambda (v)
                                   (if (eq? (var-kind v scope) 'static-parameter)
                                       (error (string "local variable name \"" v "\" conflicts with a static parameter"))))
                                 lst))
                     (list local-decls implicit-locals))
           (if lam
               (set-car! (cddr lam)
                         (append (caddr lam) newnames newnames-def)))
           (insert-after-meta ;; return the new, expanded scope-block
            (blockify
             (let ((new-scope (make-scope lam
                                          '()
                                          (append locals-nondef locals-def)
                                          globals
                                          '()
                                          (append (map cons need-rename renamed)
                                                  (map cons need-rename-def renamed-def))
                                          scope
                                          (and soft? (null? argnames))
                                          hard?
                                          (if toplevel?
                                              implicit-globals
                                              (scope:implicit-globals scope))
                                          warn-vars)))
               (begin0
                (resolve-scopes- blok new-scope '() loc)
                (pop-scope! new-scope))))
            (append! (map (lambda (v) `(local ,v)) newnames)
                     (map (lambda (v) `(local-def ,v)) newnames-def)))
           ))
        ((eq? (car e) 'module)
         (error "\"module\" expression not at top level"))
        ((eq? (car e) 'break-block)
         `(break-block ,(cadr e) ;; ignore type symbol of break-block expression
                       ,(resolve-scopes- (caddr e) scope '() loc))) ;; body of break-block expression
        ((eq? (car e) 'with-static-parameters)
         `(with-static-parameters
           ,(resolve-scopes- (cadr e) scope (cddr e) loc)
           ,@(cddr e)))
        ((and (eq? (car e) 'method) (length> e 2))
         `(method
           ,(resolve-scopes- (cadr   e) scope)
           ,(resolve-scopes- (caddr  e) scope)
           ,(resolve-scopes- (cadddr e) scope (method-expr-static-parameters e))))
        (else
         (if (and (eq? (car e) '=) (symbol? (cadr e))
                  scope (null? (lam:args (scope:lam scope)))
                  (warn-var?! (cadr e) scope)
                  (= *scopewarn-opt* 1))
             (let* ((v    (cadr e))
                    (loc  (extract-line-file loc)))
               (lowering-warning
                1000 'warn (cadr loc) (car loc)
                (string "Assignment to `" v "` in soft scope is ambiguous "
                        "because a global variable by the same name exists: "
                        "`" v "` will be treated as a new local. "
                        "Disambiguate by using `local " v "` to suppress this warning or "
                        "`global " v "` to assign to the existing global variable."))))
         (cons (car e)
               (map (lambda (x)
                      (if (linenum? x)
                          (set! loc x))
                      (resolve-scopes- x scope '() loc))
                    (cdr e))))))

(define (resolve-scopes e) (resolve-scopes- e #f))

;; pass 3: analyze variables

;; names of arguments and local vars
(define (lambda-all-vars e)
  (append (lam:argnames e) (caddr e)))

;; compute set of variables referenced in a lambda but not bound by it
(define (free-vars- e tab)
  (cond ((or (eq? e UNUSED) (underscore-symbol? e)) tab)
        ((symbol? e) (put! tab e #t))
        ((and (pair? e) (eq? (car e) 'globalref)) tab)
        ((and (pair? e) (eq? (car e) 'break-block)) (free-vars- (caddr e) tab))
        ((and (pair? e) (eq? (car e) 'with-static-parameters)) (free-vars- (cadr e) tab))
        ((or (atom? e) (quoted? e)) tab)
        ((eq? (car e) 'lambda)
         (let ((bound (table)))
           (for-each (lambda (b) (put! bound b #t)) (lambda-all-vars e))
           (for-each (lambda (v) (if (not (has? bound v)) (put! tab v #t)))
                     (free-vars (lam:body e))))
         tab)
        (else
         (for-each (lambda (x) (free-vars- x tab))
                   (cdr e))
         tab)))

(define (free-vars e)
  (table.keys (free-vars- e (table))))

(define (vinfo-to-table vi)
  (let ((tab (table)))
    (for-each (lambda (v) (put! tab (car v) v))
              vi)
    tab))

(define (analyze-vars-lambda e env captvars sp new-sp methsig tab)
  (let* ((args (lam:args e))
         (locl (caddr e))
         (allv (nconc (map arg-name args) locl))
         (fv   (let* ((fv (diff (free-vars (lam:body e)) allv))
                      ;; add variables referenced in declared types for free vars
                      (dv (apply nconc (map (lambda (v)
                                              (let ((vi (get tab v #f)))
                                                (if vi (free-vars (vinfo:type vi)) '())))
                                            fv))))
                 (append (diff dv fv) fv)))
         (sig-fv (if methsig (free-vars methsig) '()))
         (glo  (find-global-decls (lam:body e)))
         ;; make var-info records for vars introduced by this lambda
         (vi   (nconc
                (map (lambda (decl) (make-var-info (decl-var decl)))
                     args)
                (map make-var-info locl)))
         (capt-sp (filter (lambda (v) (or (and (memq v fv) (not (memq v glo)) (not (memq v new-sp)))
                                          (memq v sig-fv)))
                          sp))
         ;; captured vars: vars from the environment that occur
         ;; in our set of free variables (fv).
         (cv    (append (filter (lambda (v) (and (memq (vinfo:name v) fv)
                                                 (not (memq (vinfo:name v) new-sp))
                                                 (not (memq (vinfo:name v) glo))))
                                env)
                        (map make-var-info capt-sp)))
         (new-env (append vi
                          ;; new environment: add our vars
                          (filter (lambda (v)
                                    (and (not (memq (vinfo:name v) allv))
                                         (not (memq (vinfo:name v) glo))))
                                  env))))
    (analyze-vars (lam:body e)
                  new-env
                  cv (delete-duplicates (append new-sp sp))
                  (vinfo-to-table new-env))
    ;; mark all the vars we capture as captured
    (for-each (lambda (v) (vinfo:set-capt! v #t))
              cv)
    (set-car! (cddr e)
              `(,vi ,cv 0 ,(delete-duplicates (append new-sp capt-sp))))
    e))

;; this pass records information about variables used by closure conversion.
;; finds which variables are assigned or captured, and records variable
;; type declarations.
;; this info is recorded by setting the second argument of `lambda` expressions
;; in-place to
;;   (var-info-lst captured-var-infos ssavalues static_params)
;; where var-info-lst is a list of var-info records
(define (analyze-vars e env captvars sp tab)
  (if (or (atom? e) (quoted? e))
      (begin
        (if (symbol? e)
            (let ((vi (get tab e #f)))
              (if vi
                  (vinfo:set-read! vi #t))))
        e)
      (case (car e)
        ((local-def) ;; a local that we know has an assignment that dominates all usages
         (let ((vi (get tab (cadr e) #f)))
              (vinfo:set-never-undef! vi #t)))
        ((=)
         (let ((vi (and (symbol? (cadr e)) (get tab (cadr e) #f))))
           (if vi ; if local or captured
               (begin (if (vinfo:asgn vi)
                          (vinfo:set-sa! vi #f)
                          (vinfo:set-sa! vi #t))
                      (vinfo:set-asgn! vi #t))))
         (analyze-vars (caddr e) env captvars sp tab))
        ((call)
         (let ((vi (get tab (cadr e) #f)))
           (if vi
               (vinfo:set-called! vi #t))
           ;; calls to functions with keyword args have head of `kwcall` first
           (if (and (length> e 3) (equal? (cadr e) '(core kwcall)))
               (let ((vi2 (get tab (cadddr e) #f)))
                 (if vi2
                     (vinfo:set-called! vi2 #t))))
           (for-each (lambda (x) (analyze-vars x env captvars sp tab))
                     (cdr e))))
        ((decl)
         ;; handle var::T declaration by storing the type in the var-info
         ;; record. for non-symbols or globals, emit a type assertion.
         (let ((vi (get tab (cadr e) #f)))
           (if vi
               (begin (if (not (equal? (vinfo:type vi) '(core Any)))
                          (error (string "multiple type declarations for \""
                                         (cadr e) "\"")))
                      (if (assq (cadr e) captvars)
                          (error (string "type of \"" (cadr e)
                                         "\" declared in inner scope")))
                      (vinfo:set-type! vi (caddr e))))))
        ((lambda)
         (analyze-vars-lambda e env captvars sp '() #f tab))
        ((with-static-parameters)
         ;; (with-static-parameters func_expr sp_1 sp_2 ...)
         (assert (eq? (car (cadr e)) 'lambda))
         (analyze-vars-lambda (cadr e) env captvars sp
                              (cddr e) #f tab))
        ((method)
         (if (length= e 2)
             (let ((vi (get tab (method-expr-name e) #f)))
               (if vi
                   (begin (if (vinfo:asgn vi)
                              (vinfo:set-sa! vi #f)
                              (vinfo:set-sa! vi #t))
                          (vinfo:set-asgn! vi #t)))
               e)
             (begin (analyze-vars (caddr e) env captvars sp tab)
                    (assert (eq? (car (cadddr e)) 'lambda))
                    (analyze-vars-lambda (cadddr e) env captvars sp
                                         (method-expr-static-parameters e)
                                         (caddr e) tab))))
        ((module toplevel) e)
        (else (for-each (lambda (x) (analyze-vars x env captvars sp tab))
                        (cdr e))))))

(define (analyze-variables! e) (analyze-vars e '() '() '() (table)) e)

;; pass 4: closure conversion

;; this pass lifts all inner functions to the top level by generating
;; a type for them. for example `f(x) = y->(y+x)` is converted to
#|
immutable yt{T}
    x::T
end

(self::yt)(y) = y + self.x

f(x) = yt(x)
|#

(define (type-for-closure-parameterized name P names fields types super)
  (let ((n (length P))
        (s (make-ssavalue)))
    `((thunk ,(linearize `(lambda ()
         (() () 0 ())
         (block (global ,name)
                ,@(map (lambda (p n) `(= ,p (call (core TypeVar) ',n (core Any)))) P names)
                (= ,s (call (core _structtype) (thismodule) (inert ,name) (call (core svec) ,@P)
                            (call (core svec) ,@(map quotify fields))
                            (call (core svec))
                            (false) ,(length fields)))
                (call (core _setsuper!) ,s ,super)
                (const (globalref (thismodule) ,name) ,s)
                (call (core _typebody!) ,s (call (core svec) ,@types))
                (return (null)))))))))

(define (type-for-closure name fields super)
  (let ((s (make-ssavalue)))
    `((thunk ,(linearize `(lambda ()
       (() () 0 ())
       (block (global ,name)
              (= ,s (call (core _structtype) (thismodule) (inert ,name) (call (core svec))
                          (call (core svec) ,@(map quotify fields))
                          (call (core svec))
                          (false) ,(length fields)))
              (call (core _setsuper!) ,s ,super)
              (const (globalref (thismodule) ,name) ,s)
              (call (core _typebody!) ,s
                    (call (core svec) ,@(map (lambda (v) '(core Box)) fields)))
              (return (null)))))))))

;; better versions of above, but they get handled wrong in many places
;; need to fix that in order to handle #265 fully (and use the definitions)

;; template for generating a closure type with parameters
;(define (type-for-closure-parameterized name P names fields types super)
;  (let ((n (length P)))
;        `((global ,name)
;          (const ,name)
;          ,@(map (lambda (p n) `(= ,p (call (core TypeVar) ',n (core Any)))) P names)
;          (struct_type ,name (call (core svec) ,@P)
;                       (call (core svec) ,@(map quotify fields))
;                       ,super
;                       (call (core svec) ,@types) (false) ,(length fields)))))

;; ... and without parameters
;(define (type-for-closure name fields super)
;  `((global ,name)
;    (const ,name)
;    (struct_type ,name (call (core svec))
;                 (call (core svec) ,@(map quotify fields))
;                 ,super
;                 (call (core svec) ,@(map (lambda (v) 'Any) fields))
;                 (false) ,(length fields))))


(define (vinfo:not-capt vi)
  (list (car vi) (cadr vi) (logand (caddr vi) (lognot 1))))

(define (clear-capture-bits vinfos)
  (map vinfo:not-capt vinfos))

(define (convert-lambda lam fname interp capt-sp opaq parsed-method-stack)
  (let ((body (add-box-inits-to-body
               lam (cl-convert (cadddr lam) fname lam (table) (table) #f interp opaq parsed-method-stack (table) (vinfo-to-table (car (lam:vinfo lam)))))))
    `(lambda ,(lam:args lam)
       (,(clear-capture-bits (car (lam:vinfo lam)))
        ()
        ,(caddr (lam:vinfo lam))
        ,(delete-duplicates (append (lam:sp lam) capt-sp)))
       ,body)))

;; renumber ssavalues assigned in an expr, allowing it to be repeated
(define (renumber-assigned-ssavalues e)
  (let ((vals (expr-find-all (lambda (x) (and (assignment? x) (ssavalue? (cadr x))))
                             e
                             cadadr)))
    (if (null? vals)
        e
        (let ((repl (table)))
          (for-each (lambda (id) (put! repl id (make-ssavalue)))
                    vals)
          (let do-replace ((x e))
            (if (or (atom? x) (quoted? x))
                x
                (if (eq? (car x) 'ssavalue)
                    (or (get repl (cadr x) #f) x)
                    (cons (car x)
                          (map do-replace (cdr x))))))))))

(define (convert-for-type-decl rhs t assert lam)
  (if (equal? t '(core Any))
      rhs
      (let* ((new-mutable-var
               (lambda () (let ((g (gensy)))
                               (if lam (set-car! (lam:vinfo lam) (append (car (lam:vinfo lam)) `((,g Any 10)))))
                               g)))
             (left (if (or (atom? t) (ssavalue? t) (quoted? t))
                       #f
                       (make-ssavalue)))
             (temp (new-mutable-var)) ; use a slot to permit union-splitting this in inference
             (ty   (or left t))
             (ex   `(call (top convert) ,ty ,temp))
             (ex   (if assert `(call (core typeassert) ,ex ,ty) ex))
             (ex   `(= ,temp ,ex))
             (ex   `(if (call (core isa) ,temp ,ty) (null) ,ex))
             (t    (if left (renumber-assigned-ssavalues t) t))
             (ex   `((= ,temp ,rhs) ,ex ,temp))
             (ex   (if left (cons `(= ,left ,t) ex) ex))
             (ex   (if lam ex (cons `(local-def ,temp) ex))))
        (cons 'block ex))))

(define (capt-var-access var fname opaq)
  (if opaq
      `(call (core getfield) ,fname ,(get opaq var))
      `(call (core getfield) ,fname (inert ,var))))

(define (convert-global-assignment var rhs0 globals lam)
  (let* ((rhs1 (if (or (simple-atom? rhs0)
                       (equal? rhs0 '(the_exception)))
                   rhs0
                   (make-ssavalue)))
         (ref   (binding-to-globalref var))
         (ty   `(call (core get_binding_type) ,(cadr ref) (inert ,(caddr ref))))
         (rhs  (if (get globals ref #t) ;; no type declaration for constants
                   (convert-for-type-decl rhs1 ty #f lam)
                   rhs1))
         (ex   `(= ,var ,rhs)))
    (if (eq? rhs1 rhs0)
        `(block ,ex ,rhs0)
        `(block (= ,rhs1 ,rhs0)
                ,ex
                ,rhs1))))

;; convert assignment to a closed variable to a setfield! call.
;; while we're at it, generate `convert` calls for variables with
;; declared types.
;; when doing this, the original value needs to be preserved, to
;; ensure the expression `a=b` always returns exactly `b`.
(define (convert-assignment var rhs0 fname lam interp opaq parsed-method-stack globals locals)
  (cond
    ((symbol? var)
     (let* ((vi (get locals var #f))
            (cv (assq var (cadr (lam:vinfo lam))))
            (vt  (or (and vi (vinfo:type vi))
                     (and cv (vinfo:type cv))
                     '(core Any)))
            (closed (and cv (vinfo:asgn cv) (vinfo:capt cv)))
            (capt   (and vi (vinfo:asgn vi) (vinfo:capt vi))))
       (if (and (not closed) (not capt) (equal? vt '(core Any)))
           (if (or (local-in? var lam) (underscore-symbol? var))
               `(= ,var ,rhs0)
               (convert-global-assignment var rhs0 globals lam))
           (let* ((rhs1 (if (or (simple-atom? rhs0)
                                (equal? rhs0 '(the_exception)))
                            rhs0
                            (make-ssavalue)))
                  (rhs  (convert-for-type-decl rhs1 (cl-convert vt fname lam #f #f #f interp opaq parsed-method-stack (table) locals) #t lam))
                  (ex (cond (closed `(call (core setfield!)
                                           ,(if interp
                                                `($ ,var)
                                                (capt-var-access var fname opaq))
                                           (inert contents)
                                           ,rhs))
                            (capt `(call (core setfield!) ,var (inert contents) ,rhs))
                            (else `(= ,var ,rhs)))))
             (if (eq? rhs1 rhs0)
                 `(block ,ex ,rhs0)
                 `(block (= ,rhs1 ,rhs0)
                         ,ex
                         ,rhs1))))))
     ((globalref? var)
      (convert-global-assignment var rhs0 globals lam))
     ((ssavalue? var)
      `(= ,var ,rhs0))
     (else
       (error (string "invalid assignment location \"" (deparse var) "\"")))))

(define (rename-sig-types ex namemap)
  (pattern-replace
   (pattern-set
    (pattern-lambda (call (core (-/ Typeof)) name)
                    (get namemap name __)))
   ex))

;; replace leading (function) argument type with `typ`
(define (fix-function-arg-type te typ iskw namemap type-sp)
  (let* ((typapp (caddr te))
         (types  (rename-sig-types (cddr typapp) namemap))
         (closure-type (if (null? type-sp)
                           typ
                           `(call (core apply_type) ,typ ,@type-sp)))
         (newtypes
          (if iskw
              `(,(car types) ,(cadr types) ,closure-type ,@(cdddr types))
              `(,closure-type ,@(cdr types))))
         (loc (caddddr te)))
    `(call (core svec)
           (call (core svec) ,@newtypes)
           (call (core svec) ,@(append (cddr (cadddr te)) type-sp))
           ,loc)))

;; collect all toplevel-butfirst expressions inside `e`, and return
;; (ex . stmts), where `ex` is the expression to evaluated and
;; `stmts` is a list of statements to move to the top level.
(define (lift-toplevel e)
  (let ((top '()))
    (define (lift- e)
      (if (or (atom? e) (quoted? e))
          e
          (let ((e (cons (car e) (map lift- (cdr e)))))
            (if (eq? (car e) 'toplevel-butfirst)
                (begin (set! top (cons (cddr e) top))
                       (cadr e))
                e))))
    (let ((e2 (lift- e)))
      (let ((stmts (apply append (reverse top))))
        ;; move all type definitions first
        (receive (structs others)
                 (separate (lambda (x) (and (pair? x) (eq? (car x) 'thunk)))
                           stmts)
                 (cons e2 (append structs others)))))))

(define (first-non-meta blk)
  (let loop ((xs (cdr blk)))
    (if (null? xs)
        #f
        (let ((elt (car xs)))
          (if (and (pair? elt) (eq? (car elt) 'meta))
              (loop (cdr xs))
              elt)))))

; try to ignore some metadata expressions for implicit return sometimes
(define (only-meta? blk)
  (let loop ((xs blk))
    (if (null? xs)
        #t
        (let ((elt (car xs)))
          (if (and (pair? elt) (memq (car elt) '(lineinfo line loopinfo)))
              (loop (cdr xs))
              #f)))))

;; return `body` with `stmts` inserted after any meta nodes
(define (insert-after-meta body stmts)
  (if (null? stmts)
      body
      (let ((meta (take-while (lambda (x) (and (pair? x)
                                               (memq (car x) '(lineinfo line meta))))
                              (cdr body))))
        `(,(car body)
          ,@meta
          ,@stmts
          ,@(list-tail body (+ 1 (length meta)))))))

(define (add-box-inits-to-body lam body)
  (let ((args (map arg-name (lam:args lam)))
        (vis  (car (lam:vinfo lam))))
    ;; insert Box allocations for captured/assigned arguments
    (insert-after-meta
     body
     (apply append
            (map (lambda (arg)
                   (let ((vi (assq arg vis)))
                     (if (and vi (vinfo:asgn vi) (vinfo:capt vi))
                         `((= ,arg (call (core Box) ,arg)))
                         '())))
                 args)))))

;; find all methods for the same function as `ex` in `body`
(define (all-methods-for ex body)
  (let ((mname (method-expr-name ex)))
    (expr-find-all (lambda (s)
                     (and (length> s 2) (eq? (car s) 'method)
                          (eq? (method-expr-name s) mname)))
                   body
                   identity
                   (lambda (x) (and (pair? x) (not (eq? (car x) 'lambda)))))))

(define lambda-opt-ignored-exprs
  (Set '(quote top core lineinfo line inert local-def unnecessary copyast
         meta inbounds boundscheck loopinfo decl aliasscope popaliasscope
         thunk with-static-parameters toplevel-only
         global globalref assign-const-if-global thismodule
         const atomic null true false ssavalue isdefined toplevel module lambda
         error gc_preserve_begin gc_preserve_end import using export public inline noinline purity)))

(define (local-in? s lam (tab #f))
  (or (and tab (has? tab s))
      (assq s (car  (lam:vinfo lam)))
      (assq s (cadr (lam:vinfo lam)))))

;; Try to identify never-undef variables, and then clear the `captured` flag for single-assigned,
;; never-undef variables to avoid allocating unnecessary `Box`es.
(define (lambda-optimize-vars! lam)
  (assert (eq? (car lam) 'lambda))
  ;; memoize all-methods-for to avoid O(n^2) behavior
  (define allmethods-table (table))
  (define (get-methods ex stmts)
    (let ((mn (method-expr-name ex)))
      (if (has? allmethods-table mn)
          (get allmethods-table mn)
          (let ((am (all-methods-for ex stmts)))
            (put! allmethods-table mn am)
            am))))
  ;; This does a basic-block-local dominance analysis to find variables that
  ;; are never used undef.
  (let ((vi     (car (lam:vinfo lam)))
        (args   (lam:argnames lam))
        (decl   (table))
        (unused (table))  ;; variables not (yet) used (read from) in the current block
        (live   (table))  ;; variables that have been set in the current block
        (seen   (table))) ;; all variables we've seen assignments to
    ;; Collect candidate variables: those that are captured (and hence we want to optimize)
    ;; and only assigned once. This populates the initial `unused` table.
    (for-each (lambda (v)
                (if (and (vinfo:capt v) (vinfo:sa v))
                    (put! unused (car v) #t)))
              vi)
    (define (restore old)
      (table.foreach (lambda (k v)
                       (if (not (has? old k))
                           (put! unused k v)))
                     live)
      (set! live old))
    (define (kill)
      ;; when we see control flow, empty live set back into unused set
      (restore (table)))
    (define (mark-used var)
      ;; remove variable from the unused table
      ;; Note arguments are only "used" for purposes of this analysis when
      ;; they are captured, since they are never undefined.
      (if (and (has? unused var) (not (memq var args)))
          (del! unused var)))
    (define (mark-captured var)
      (if (has? unused var)
          (del! unused var)))
    (define (assign! var)
      (if (has? unused var)
          ;; When a variable is assigned, move it to the live set to protect
          ;; it from being removed from `unused`.
          (begin (put! live var #t)
                 (put! seen var #t)
                 (del! unused var))))
    (define (declare! var)
      (if (has? unused var)
          (put! decl var #t)))
    (define (leave-loop! old-decls)
      ;; at the end of a loop, remove live variables that were declared outside,
      ;; since those might be assigned multiple times (issue #37690)
      (for-each (lambda (k)
                  (if (has? old-decls k)
                      (del! live k)))
                (table.keys live))
      (set! decl old-decls))
    (define (visit e)
      ;; returns whether e contained a symboliclabel
      (cond ((atom? e) (if (symbol? e) (mark-used e))
             #f)
            ((lambda-opt-ignored-exprs (car e))
             #f)
            ((eq? (car e) 'scope-block)
             (visit (cadr e)))
            ((memq (car e) '(block call new splatnew new_opaque_closure))
             (eager-any visit (cdr e)))
            ((eq? (car e) 'break-block)
             (visit (caddr e)))
            ((eq? (car e) 'return)
             (begin0 (visit (cadr e))
                     (kill)))
            ((memq (car e) '(break label symbolicgoto))
             (kill)
             #f)
            ((eq? (car e) 'symboliclabel)
             (kill)
             #t)
            ((memq (car e) '(if elseif trycatch tryfinally trycatchelse))
             (let ((prev (table.clone live)))
               (if (eager-any (lambda (e) (begin0 (visit e)
                                                  (kill)))
                              (cdr e))
                   ;; if there is a label inside, we could have skipped a prior
                   ;; variable initialization
                   (begin (kill) #t)
                   (begin (restore prev) #f))))
            ((or (eq? (car e) '_while) (eq? (car e) '_do_while))
             (let ((prev  (table.clone live))
                   (decl- (table.clone decl)))
               (let ((result (eager-any visit (cdr e))))
                 (leave-loop! decl-)
                 (if result
                     #t
                     (begin (restore prev) #f)))))
            ((eq? (car e) '=)
             (begin0 (visit (caddr e))
                     (assign! (cadr e))))
            ((eq? (car e) 'local)
             (declare! (cadr e))
             #f)
            ((eq? (car e) 'method)
             (if (length> e 2)
                 (let* ((mn          (method-expr-name e))
                        ;; a method expression captures a variable if any methods for
                        ;; the same function do.
                        (all-methods (if (local-in? mn lam)
                                         (get-methods e (lam:body lam))
                                         (list e))))
                   (for-each (lambda (ex)
                               (for-each mark-captured
                                         (map car (cadr (lam:vinfo (cadddr ex))))))
                             all-methods)
                   (assign! (cadr e))))
             #f)
            (else
             (eager-any visit (cdr e))
             ;; in all other cases there's nothing to do except assert that
             ;; all expression heads have been handled.
             #;(assert (memq (car e) '(foreigncall cfunction |::|))))))
    (visit (lam:body lam))
    ;; Finally, variables can be marked never-undef if they were set in the first block,
    ;; or are currently live, or are back in the unused set (because we've left the only
    ;; block that uses them, or possibly because they have no uses at all).
    (for-each (lambda (v)
                (if (has? seen v)
                    (let ((vv (assq v vi)))
                      (vinfo:set-never-undef! vv #t))))
              (append (table.keys live) (table.keys unused)))
    (for-each (lambda (v)
                (if (and (vinfo:sa v) (vinfo:never-undef v))
                    (set-car! (cddr v) (logand (caddr v) (lognot 5)))))
              vi)
    lam))

(define (is-var-boxed? v lam)
  (or (let ((vi (assq v (car (lam:vinfo lam)))))
        (and vi (vinfo:asgn vi) (vinfo:capt vi)))
      (let ((cv (assq v (cadr (lam:vinfo lam)))))
        (and cv (vinfo:asgn cv) (vinfo:capt cv)))))

(define (toplevel-preserving? e)
  (and (pair? e) (memq (car e) '(if elseif block trycatch tryfinally trycatchelse))))

(define (map-cl-convert exprs fname lam namemap defined toplevel interp opaq parsed-method-stack (globals (table)) (locals (table)))
  (if toplevel
      (map (lambda (x)
             (let ((tl (lift-toplevel (cl-convert x fname lam namemap defined
                                                  (and toplevel (toplevel-preserving? x))
                                                  interp opaq parsed-method-stack globals locals))))
               (if (null? (cdr tl))
                   (car tl)
                   `(block ,@(cdr tl) ,(car tl)))))
           exprs)
      (map (lambda (x) (cl-convert x fname lam namemap defined #f interp opaq parsed-method-stack globals locals)) exprs)))

(define (prepare-lambda! lam)
  ;; mark all non-arguments as assigned, since locals that are never assigned
  ;; need to be handled the same as those that are (i.e., boxed).
  (for-each (lambda (vi) (vinfo:set-asgn! vi #t))
            (list-tail (car (lam:vinfo lam)) (length (lam:args lam))))
  (lambda-optimize-vars! lam))

;; must start with a hash and second character must be numeric
(define (anon-function-name? str)
  (and (>= (string-length str) 2)
       (char=? (string.char str 0) #\#)
       (char-numeric? (string.char str 1))))

(define (cl-convert- e fname lam namemap defined toplevel interp opaq parsed-method-stack (globals (table)) (locals (table)))
  (if (and (not lam)
           (not (and (pair? e) (memq (car e) '(lambda method macro opaque_closure)))))
      (if (atom? e) e
          (cons (car e) (map-cl-convert (cdr e) fname lam namemap defined toplevel interp opaq parsed-method-stack globals locals)))
      (cond
       ((symbol? e)
        (define (new-undef-var name)
          (let ((g (named-gensy name)))
            (set-car! (lam:vinfo lam) (append (car (lam:vinfo lam)) `((,g Any 32))))
            g))
        (define (get-box-contents box typ)
          ; lower in an UndefVar check to a similarly named variable (ref #20016)
          ; so that closure lowering Box introduction doesn't impact the error message
          ; and the compiler is expected to fold away the extraneous null check
          (let* ((access (if (symbol? box) box (make-ssavalue)))
                 (undeftest `(call (core isdefined) ,access (inert contents)))
                 (undefvar (new-undef-var e))
                 (undefcheck `(if ,undeftest (null) (block (newvar ,undefvar) ,undefvar)))
                 (val `(call (core getfield) ,access (inert contents)))
                 (val (if (equal? typ '(core Any))
                          val
                          `(call (core typeassert) ,val
                                 ,(let ((convt (cl-convert typ fname lam namemap defined toplevel interp opaq parsed-method-stack globals locals)))
                                    (if (or (symbol-like? convt) (quoted? convt))
                                        convt
                                        (renumber-assigned-ssavalues convt)))))))
            `(block
               ,@(if (eq? box access) '() `((= ,access ,box)))
               ,undefcheck
               ,val)))
        (let ((vi (get locals e #f))
              (cv (assq e (cadr (lam:vinfo lam)))))
          (cond ((eq? e fname) e)
                ((memq e (lam:sp lam)) e)
                (cv
                 (let ((access (if interp
                                   `($ (call (core QuoteNode) ,e))
                                   (capt-var-access e fname opaq))))
                   (if (and (vinfo:asgn cv) (vinfo:capt cv))
                       (get-box-contents access (vinfo:type cv))
                       access)))
                (vi
                 (if (and (vinfo:asgn vi) (vinfo:capt vi))
                     (get-box-contents e (vinfo:type vi))
                     e))
                (else e))))
       ((atom? e) e)
       (else
        (case (car e)
          ((quote top core globalref thismodule lineinfo line break inert module toplevel null true false meta) e)
          ((toplevel-only)
           ;; hack to avoid generating a (method x) expr for struct types
           (if (eq? (cadr e) 'struct)
               (put! defined (caddr e) #t))
           e)
          ((=)
           (let ((var (cadr e))
                 (rhs (cl-convert (caddr e) fname lam namemap defined toplevel interp opaq parsed-method-stack globals locals)))
             (convert-assignment var rhs fname lam interp opaq parsed-method-stack globals locals)))
          ((local-def) ;; make new Box for local declaration of defined variable
           (let ((vi (get locals (cadr e) #f)))
             (if (and vi (vinfo:asgn vi) (vinfo:capt vi))
                 `(= ,(cadr e) (call (core Box)))
                 '(null))))
          ((local) ;; convert local declarations to newvar statements
           (let ((vi (get locals (cadr e) #f)))
             (if (and vi (vinfo:asgn vi) (vinfo:capt vi))
                 `(= ,(cadr e) (call (core Box)))
                 (if (vinfo:never-undef vi)
                     '(null)
                     `(newvar ,(cadr e))))))
          ((const)
           (put! globals (binding-to-globalref (cadr e)) #f)
           e)
          ((atomic) e)
          ((isdefined) ;; convert isdefined expr to function for closure converted variables
           (let* ((sym (cadr e))
                  (vi (and (symbol? sym) (get locals sym #f)))
                  (cv (and (symbol? sym) (assq sym (cadr (lam:vinfo lam))))))
             (cond ((eq? sym fname) e)
                   ((memq sym (lam:sp lam)) e)
                   (cv
                    (if (and (vinfo:asgn cv) (vinfo:capt cv))
                        (let ((access (if interp
                                          `($ (call (core QuoteNode) ,sym))
                                          (capt-var-access sym fname opaq))))
                          `(call (core isdefined) ,access (inert contents)))
                        '(true)))
                   (vi
                    (if (and (vinfo:asgn vi) (vinfo:capt vi))
                        `(call (core isdefined) ,sym (inert contents))
                        e))
                   (else e))))
          ((_opaque_closure)
           (let* ((isva  (car (cddddr e)))
                  (nargs (cadr (cddddr e)))
                  (allow-partial (caddr (cddddr e)))
                  (functionloc   (cadddr (cddddr e)))
                  (lam2  (last e))
                  (vis   (lam:vinfo lam2))
                  (cvs   (map car (cadr vis))))
             (prepare-lambda! lam2)
             (let ((var-exprs (map (lambda (v)
                                     (let ((cv (assq v (cadr (lam:vinfo lam)))))
                                       (if cv
                                           (capt-var-access v fname opaq)
                                           v)))
                                   cvs)))
               `(new_opaque_closure
                 ,(cadr e) ,(or (caddr e) '(call (core apply_type) (core Union))) ,(or (cadddr e) '(core Any)) ,allow-partial
                 (opaque_closure_method (null) ,nargs ,isva ,functionloc ,(convert-lambda lam2 (car (lam:args lam2)) #f '() (symbol-to-idx-map cvs) parsed-method-stack))
                 ,@var-exprs))))
          ((method)
           (let* ((name  (method-expr-name e))
                  (short (length= e 2))  ;; function f end
                  (lam2  (if short #f (cadddr e)))
                  (vis   (if short '(() () ()) (lam:vinfo lam2)))
                  (cvs   (map car (cadr vis)))
                  (local? (lambda (s) (and lam (symbol? s) (local-in? s lam locals))))
                  (local (and (not (globalref? (cadr e))) (local? name)))
                  (sig      (and (not short) (caddr e)))
                  (sp-inits (if (or short (not (eq? (car sig) 'block)))
                                '()
                                (map-cl-convert (butlast (cdr sig))
                                                fname lam namemap defined toplevel interp opaq parsed-method-stack globals locals)))
                  (sig      (and sig (if (eq? (car sig) 'block)
                                         (last sig)
                                         sig))))
             (if local
                 (begin (if (memq name (lam:args lam))
                            (error (string "cannot add method to function argument " name)))
                        (if (eqv? (string.char (string name) 0) #\@)
                            (error "macro definition not allowed inside a local scope"))))
             (if lam2 (prepare-lambda! lam2))
             (if (not local) ;; not a local function; will not be closure converted to a new type
                 (cond (short (if (has? defined (cadr e))
                                  e
                                  (begin
                                    (put! defined (cadr e) #t)
                                    `(toplevel-butfirst
                                      ;; wrap in toplevel-butfirst so it gets moved higher along with
                                      ;; closure type definitions
                                      ,e
                                      (thunk (lambda () (() () 0 ()) (block (return ,e))))))))
                       ((null? cvs)
                        `(block
                          ,@sp-inits
                          (method ,(cadr e) ,(cl-convert
                                          ;; anonymous functions with keyword args generate global
                                          ;; functions that refer to the type of a local function
                                          (rename-sig-types sig namemap)
                                          fname lam namemap defined toplevel interp opaq parsed-method-stack globals locals)
                                  ,(let ((body (add-box-inits-to-body
                                                lam2
                                                (cl-convert (cadddr lam2) 'anon lam2 (table) (table) #f interp opaq parsed-method-stack (table)
                                                            (vinfo-to-table (car (lam:vinfo lam2)))))))
                                     `(lambda ,(cadr lam2)
                                        (,(clear-capture-bits (car vis))
                                         ,@(cdr vis))
                                        ,body)))))
                       (else
                        (let* ((exprs     (lift-toplevel (convert-lambda lam2 '|#anon| #t '() #f parsed-method-stack)))
                               (top-stmts (cdr exprs))
                               (newlam    (compact-and-renumber (linearize (car exprs)) 'none 0)))
                          `(toplevel-butfirst
                            (block ,@sp-inits
                                   (method ,(cadr e) ,(cl-convert sig fname lam namemap defined toplevel interp opaq parsed-method-stack globals locals)
                                           ,(julia-bq-macro newlam)))
                            ,@top-stmts))))

                 ;; local case - lift to a new type at top level
                 (let* ((exists (get defined name #f))
                        (type-name  (or (get namemap name #f)
                                        (and name
                                             (symbol (string (if (= (string.char (string name) 0) #\#)
                                                                  (if (anon-function-name? (string name))
                                                                    (string "#" (current-julia-module-counter parsed-method-stack))
                                                                    name)
                                                                  (string "#" name))
                                                              "#" (current-julia-module-counter parsed-method-stack))))))
                        (alldefs (expr-find-all
                                  (lambda (ex) (and (length> ex 2) (eq? (car ex) 'method)
                                                    (not (eq? ex e))
                                                    (eq? (method-expr-name ex) name)))
                                  (lam:body lam)
                                  identity
                                  (lambda (x) (and (pair? x) (not (eq? (car x) 'lambda)))))))
                 (and name (put! namemap name type-name))
                 (let* ((all-capt-vars   (delete-duplicates
                                          (apply append  ;; merge captured vars from all definitions
                                                 cvs
                                                 (map (lambda (methdef)
                                                        (map car (cadr (lam:vinfo (cadddr methdef)))))
                                                      alldefs))))
                        (all-sparams   (delete-duplicates  ;; static params from all definitions
                                        (apply append
                                               (if lam2 (lam:sp lam2) '())
                                               (map (lambda (methdef) (lam:sp (cadddr methdef)))
                                                    alldefs))))
                        (capt-sp (simple-sort (intersect all-capt-vars all-sparams))) ; the intersection is the list of sparams that need to be captured
                        (capt-vars (diff all-capt-vars capt-sp)) ; remove capt-sp from capt-vars
                        (moved-vars  ;; signature-local vars that should be moved to the top-level
                         (if lam2
                             (delete-duplicates
                              (expr-find-all
                               (lambda (s) (and (symbol? s)
                                                (not (eq? name s))
                                                (not (memq s capt-sp))
                                                (if (and (length> (lam:args lam) 0) (local? s))
                                                    ;; local variable used in signature. either move it,
                                                    ;; or give an error if there are uses outside the sig.
                                                    (if (or (expr-contains-p (lambda (v) (eq? v s))
                                                                             (lam:body lam)
                                                                             (lambda (ex) (not (or (eq? ex (caddr e))
                                                                                                   (and (pair? ex)
                                                                                                        (eq? (car ex) 'local))))))
                                                            ;; var must be assigned within the signature block.
                                                            ;; otherwise it might not be assigned at all.
                                                            (not
                                                             (expr-contains-p (lambda (e)
                                                                                (and (pair? e)
                                                                                     (memq (car e) '(= method))
                                                                                     (eq? (cadr e) s)))
                                                                              (caddr e))))
                                                        (if (has? namemap s)
                                                            #f
                                                            (error (string "local variable " s
                                                                           " cannot be used in closure declaration")))
                                                        #t)
                                                    #f)))
                               (caddr e)
                               identity))
                             '()))
                        (find-locals-in-method-sig (lambda (methdef)
                                                     (expr-find-all
                                                      (lambda (s) (and (symbol? s)
                                                                       (not (eq? name s))
                                                                       (not (memq s capt-sp))
                                                                       (memq s (lam:sp lam))))
                                                      (caddr methdef)
                                                      identity)))
                        (sig-locals (simple-sort
                                     (delete-duplicates  ;; locals used in sig from all definitions
                                      (apply append      ;; will convert these into sparams for dispatch
                                             (if lam2 (find-locals-in-method-sig e) '())
                                             (map find-locals-in-method-sig alldefs)))))
                        (closure-param-names (append capt-sp sig-locals)) ; sparams for the closure method declaration
                        (closure-param-syms (map (lambda (s) (make-ssavalue)) closure-param-names))
                        (typedef  ;; expression to define the type
                         (let* ((fieldtypes (map (lambda (v)
                                                   (if (is-var-boxed? v lam)
                                                       '(core Box)
                                                       (make-ssavalue)))
                                                 capt-vars))
                                (para (append closure-param-syms
                                              (filter ssavalue? fieldtypes)))
                                (fieldnames (append closure-param-names (filter (lambda (v) (not (is-var-boxed? v lam))) capt-vars))))
                           (if (null? para)
                               (type-for-closure type-name capt-vars '(core Function))
                               (type-for-closure-parameterized type-name para fieldnames capt-vars fieldtypes '(core Function)))))
                        (mk-method ;; expression to make the method
                         (if short '()
                             (let* ((iskw ;; TODO jb/functions need more robust version of this
                                     (contains (lambda (x) (eq? x 'kwftype)) sig))
                                    (renamemap (map cons closure-param-names closure-param-syms))
                                    (arg-defs (replace-vars
                                               (fix-function-arg-type sig type-name iskw namemap closure-param-syms)
                                               renamemap)))
                               (append (map (lambda (gs tvar)
                                              (make-assignment gs `(call (core TypeVar) ',tvar (core Any))))
                                            closure-param-syms closure-param-names)
                                       `((method #f ,(cl-convert arg-defs fname lam namemap defined toplevel interp opaq parsed-method-stack globals locals)
                                                 ,(convert-lambda lam2
                                                                  (if iskw
                                                                      (caddr (lam:args lam2))
                                                                      (car (lam:args lam2)))
                                                                  #f closure-param-names #f parsed-method-stack)))))))
                        (mk-closure  ;; expression to make the closure
                         (let* ((var-exprs (map (lambda (v)
                                                  (let ((cv (assq v (cadr (lam:vinfo lam)))))
                                                    (if cv
                                                        (if interp
                                                            `($ (call (core QuoteNode) ,v))
                                                            (capt-var-access v fname opaq))
                                                        v)))
                                                capt-vars))
                                (P (append
                                    closure-param-names
                                    (filter identity (map (lambda (v ve)
                                                            (if (is-var-boxed? v lam)
                                                                #f
                                                                `(call (core _typeof_captured_variable) ,ve)))
                                                          capt-vars var-exprs)))))
                           `(new ,(if (null? P)
                                      type-name
                                      `(call (core apply_type) ,type-name ,@P))
                                 ,@var-exprs))))
                   (if (pair? moved-vars)
                       (set-car! (lam:vinfo lam)
                                 (filter (lambda (vi)
                                           (not (memq (car vi) moved-vars)))
                                         (car (lam:vinfo lam)))))
                   (if (or exists (and short (pair? alldefs)))
                       `(toplevel-butfirst
                         (null)
                         ,@sp-inits
                         ,@mk-method)
                       (begin
                         (put! defined name #t)
                         `(toplevel-butfirst
                           ,(convert-assignment name mk-closure fname lam interp opaq parsed-method-stack globals locals)
                           ,@typedef
                           ,@(map (lambda (v) `(moved-local ,v)) moved-vars)
                           ,@sp-inits
                           ,@mk-method))))))))
          ((lambda)  ;; happens inside (thunk ...) and generated function bodies
           (for-each (lambda (vi) (vinfo:set-asgn! vi #t))
                     (list-tail (car (lam:vinfo e)) (length (lam:args e))))
           (lambda-optimize-vars! e)
           (let ((body (map-cl-convert (cdr (lam:body e)) 'anon
                                       e
                                       (table)
                                       (table)
                                       (null? (cadr e)) ;; only toplevel thunks have 0 args
                                       interp opaq parsed-method-stack globals (vinfo-to-table (car (lam:vinfo e))))))
             `(lambda ,(cadr e)
                (,(clear-capture-bits (car (lam:vinfo e)))
                 () ,@(cddr (lam:vinfo e)))
                (block ,@body))))
          ;; remaining `::` expressions are type assertions
          ((|::|)
           (cl-convert `(call (core typeassert) ,@(cdr e)) fname lam namemap defined toplevel interp opaq parsed-method-stack globals locals))
          ;; remaining `decl` expressions are only type assertions if the
          ;; argument is global or a non-symbol.
          ((decl)
           (cond ((and (symbol? (cadr e))
                       (local-in? (cadr e) lam locals))
                  '(null))
                 (else
                  (cl-convert
                   (let ((ref (binding-to-globalref (cadr e))))
                     (if ref
                         (begin
                           (put! globals ref #t)
                           `(block
                             (toplevel-only set_binding_type! ,(cadr e))
                             (globaldecl ,ref ,(caddr e))
                             (null)))
                         `(call (core typeassert) ,@(cdr e))))
                   fname lam namemap defined toplevel interp opaq parsed-method-stack globals locals))))
          ;; `with-static-parameters` expressions can be removed now; used only by analyze-vars
          ((with-static-parameters)
           (cl-convert (cadr e) fname lam namemap defined toplevel interp opaq parsed-method-stack globals locals))
          (else
           (cons (car e)
                 (map-cl-convert (cdr e) fname lam namemap defined toplevel interp opaq parsed-method-stack globals locals))))))))

;; wrapper for `cl-convert-`
(define (cl-convert e fname lam namemap defined toplevel interp opaq (parsed-method-stack '()) (globals (table)) (locals (table)))
  (if (is-method? e)
      (let ((name (method-expr-name e)))
        (cl-convert- e fname lam namemap defined toplevel interp opaq (cons name parsed-method-stack) globals locals))
      (cl-convert- e fname lam namemap defined toplevel interp opaq parsed-method-stack globals locals)))

(define (closure-convert e) (cl-convert e #f #f (table) (table) #f #f #f))

;; pass 5: convert to linear IR

(define (linearize e)
  (cond ((or (not (pair? e)) (quoted? e)) e)
        ((eq? (car e) 'lambda)
         (set-car! (cdddr e) (compile-body (cadddr e) (append (car (caddr e))
                                                              (cadr (caddr e)))
                                           e)))
        (else (for-each linearize (cdr e))))
  e)

(define (valid-ir-argument? e)
  (or (simple-atom? e)
      (and (globalref? e) (nothrow-julia-global (cadr e) (caddr e)))
      (and (pair? e)
           (memq (car e) '(quote inert top core
                                 slot static_parameter)))))

(define (valid-ir-rvalue? lhs e)
  (or (ssavalue? lhs)
      (valid-ir-argument? e)
      (and (symbol? lhs) (pair? e)
           (memq (car e) '(new splatnew the_exception isdefined call invoke foreigncall cfunction gc_preserve_begin copyast new_opaque_closure globalref)))))

(define (valid-ir-return? e)
  ;; returning lambda directly is needed for @generated
  (or (valid-ir-argument? e) (and (pair? e) (memq (car e) '(lambda)))))

(define (code-trivially-effect-free? e)
  ;; determine whether the execution of this code can be observed.
  ;; If not it may be deleted. In general, the only thing we can detect here
  ;; is empty blocks that only have metadata in them.
  (if (pair? e)
    (case (car e)
      ((block) (every code-trivially-effect-free? (cdr e)))
      ((line null) #t)
      (else #f))
    #t))

;; this pass behaves like an interpreter on the given code.
;; to perform stateful operations, it calls `emit` to record that something
;; needs to be done. in value position, it returns an expression computing
;; the needed value. in the future, all intermediate values will have
;; numbered slots (or be simple immediate values), and then those will be the
;; only possible returned values.
(define (compile-body e vi lam)
  (let ((code '())            ;; statements (emitted in reverse order)
        (filename #f)
        (first-line #t)
        (current-loc #f)
        (rett #f)
        (global-const-error #f)
        (vinfo-table (vinfo-to-table (car (lam:vinfo lam))))
        (arg-map #f)          ;; map arguments to new names if they are assigned
        (label-counter 0)     ;; counter for generating label addresses
        (label-map (table))   ;; maps label names to generated addresses
        (label-nesting (table)) ;; exception handler and catch block nesting of each label
        (finally-handler #f)  ;; Current finally block info: `(var label map level tokens)`
                              ;; `map` is a list of `(tag . action)` which will
                              ;; be emitted at the exit of the block. Code
                              ;; should enter the finally block via `enter-finally-block`.
        (handler-goto-fixups '())  ;; `goto`s that might need `leave` exprs added
        (handler-token-stack '())  ;; tokens identifying handler stack while active
        (catch-token-stack '())) ;; tokens identifying handler enter for current catch blocks
    (define (emit c)
      (or c (raise "missing value in IR"))
      (set! code (cons c code))
      c)
    (define (make-label)
      (begin0 label-counter
              (set! label-counter (+ 1 label-counter))))
    (define (mark-label l) (emit `(label ,l)))
    (define (make&mark-label)
      (if (and (pair? code) (pair? (car code)) (eq? (caar code) 'label))
          ;; use current label if there is one
          (cadr (car code))
          (let ((l (make-label)))
            (mark-label l)
            l)))
    ;; Enter a finally block, either through the landing pad or via a jump if
    ;; `need-goto` is true. Before entering, the current code path is identified
    ;; with a tag which labels the action to be taken at finally handler exit.
    ;; `action` may be `(return x)`, `(break x)`, or a call to rethrow.
    (define (enter-finally-block action (need-goto #t))
      (let* ((tags (caddr finally-handler))
             (tag  (if (null? tags) 1 (+ 1 (caar tags)))))
        ;; To enter the current active finally block, set the tag variable
        ;; to identify the current code path with the action for this code path
        ;; which will run at finally block exit.
        (set-car! (cddr finally-handler) (cons (cons tag action) tags))
        (emit `(= ,(car finally-handler) ,tag))
        (if need-goto
            (let ((label (cadr finally-handler))
                  (dest-handler-tokens (cadddr finally-handler))
                  (dest-catch-tokens   (caddddr finally-handler)))
              ;; Leave current exception handling scope and jump to finally block
              (let ((pexc (pop-exc-expr catch-token-stack dest-catch-tokens)))
                (if pexc (emit pexc)))
              (let ((plist (pop-handler-list handler-token-stack (cdr dest-handler-tokens) '())))
                (emit `(leave ,@plist)))
              (emit `(goto ,label))))
        tag))
    (define (pop-exc-expr src-tokens dest-tokens)
      (if (eq? src-tokens dest-tokens)
          #f
          (let ((restore-token (let loop ((s src-tokens))
                                 (if (not (pair? s))
                                     (error "Attempt to jump into catch block"))
                                 (if (eq? (cdr s) dest-tokens)
                                     (car s)
                                     (loop (cdr s))))))
            `(pop_exception ,restore-token))))
    (define (pop-handler-list src-tokens dest-tokens lab)
      (if (eq? src-tokens dest-tokens)
          #f
          (let loop ((s src-tokens)
                     (l '()))
            (if (not (pair? s))
                (if (null? lab)
                  (error "Attempt to jump into catch block")
                  (error (string "cannot goto label \"" lab "\" inside try/catch block"))))
            (if (eq? (cdr s) dest-tokens)
                (cons (car s) l)
                (loop (cdr s) (cons (car s) l))))))
    (define (emit-return tail x)
      (define (emit- x)
        (let* ((tmp (if ((if (null? catch-token-stack) valid-ir-return? simple-atom?) x)
                        #f
                        (make-ssavalue))))
          (if tmp
              (begin (emit `(= ,tmp ,x)) tmp)
              x)))
      (define (actually-return x)
        (let* ((x (begin0 (emit- x)
                          ;; if we are adding an implicit return then mark it as having no location
                          (if (not (eq? tail 'explicit))
                              (emit '(line #f)))))
               (x (if rett
                      (compile (convert-for-type-decl x rett #t lam) '() #t #f)
                      x))
               (x (emit- x)))
          (let ((pexc (pop-exc-expr catch-token-stack '())))
            (if pexc (emit pexc)))
          (emit `(return ,x))))
      (if x
          (if (null? handler-token-stack)
              (actually-return x)
              (let ((tmp (cond ((and (simple-atom? x) (or (not (ssavalue? x)) (not finally-handler))) #f)
                               (finally-handler  (new-mutable-var))
                               (else             (make-ssavalue)))))
                (if tmp (emit `(= ,tmp ,x)))
                (if finally-handler
                    (enter-finally-block `(return ,(or tmp x)))
                    (begin (emit `(leave ,@handler-token-stack))
                           (actually-return (or tmp x))))
                (or tmp x)))))
    (define (emit-break labl)
      (let ((dest-handler-tokens (caddr labl))
            (dest-tokens (cadddr labl)))
        (if (and finally-handler (> (length (cadddr finally-handler)) (length dest-handler-tokens)))
            (enter-finally-block `(break ,labl))
            (begin
              (let ((pexc (pop-exc-expr catch-token-stack dest-tokens)))
                (if pexc (emit pexc)))
              (let ((plist (pop-handler-list handler-token-stack dest-handler-tokens '())))
                (if plist (emit `(leave ,@plist))))
              (emit `(goto ,(cadr labl)))))))
    (define (new-mutable-var . name)
      (let ((g (if (null? name) (gensy) (named-gensy (car name)))))
        (set-car! (lam:vinfo lam) (append (car (lam:vinfo lam)) `((,g Any 2))))
        g))
    ;; give an error for misplaced top-level-only expressions
    (define (check-top-level e)
      (define (head-to-text h)
        (case h
          ((abstract_type)     "\"abstract type\" expression")
          ((primitive_type)    "\"primitive type\" expression")
          ((struct_type)       "\"struct\" expression")
          ((method)            "method definition")
          ((set_binding_type!) (string "type declaration for global \"" (deparse (cadr e)) "\""))
          (else                (string "\"" h "\" expression"))))
      (if (not (null? (cadr lam)))
          (error (string (head-to-text (car e)) " not at top level"))))
    (define (valid-body-ir-argument? aval)
      (or (valid-ir-argument? aval)
          (and (symbol? aval) ; Arguments are always defined slots
               (or (memq aval (lam:args lam))
                   (let ((vi (get vinfo-table aval #f)))
                     (and vi (vinfo:never-undef vi)))))))
    (define (single-assign-var? aval)
      (and (symbol? aval) ; Arguments are always sa
           (or (memq aval (lam:args lam))
               (let ((vi (get vinfo-table aval #f)))
                 (and vi (vinfo:sa vi))))))
    ;; TODO: We could also allow const globals here
    (define (const-read-arg? x)
      ;; Even if we have side effects, we know that singly-assigned
      ;; locals cannot be affected them, so we can inline them anyway.
      (or (simple-atom? x) (single-assign-var? x)
        (and (pair? x)
          (memq (car x) '(quote inert top core)))))
    ;; evaluate the arguments of a call, creating temporary locations as needed
    (define (compile-args lst break-labels)
      (if (null? lst) '()
        ;; First check if all the arguments as simple (and therefore side-effect free).
        ;; Otherwise, we need to use ssa values for all arguments to ensure proper
        ;; left-to-right evaluation semantics.
        (let ((simple? (every (lambda (x) (or (simple-atom? x) (symbol? x)
                                              (and (pair? x)
                                                   (memq (car x) '(quote inert top core globalref)))))
                              lst)))
          (let loop ((lst  lst)
                     (vals '()))
            (if (null? lst)
                (reverse! vals)
                (let* ((arg (car lst))
                       (aval (or (compile arg break-labels #t #f)
                                 ;; TODO: argument exprs that don't yield a value?
                                 '(null))))
                  (loop (cdr lst)
                        (cons (if (and
                                   (or simple? (const-read-arg? aval))
                                   (valid-body-ir-argument? aval))
                                  aval
                                  (let ((tmp (make-ssavalue)))
                                    (emit `(= ,tmp ,aval))
                                    tmp))
                              vals))))))))
    (define (compile-cond ex break-labels)
      (let ((cnd (or (compile ex break-labels #t #f)
                     ;; TODO: condition exprs that don't yield a value?
                     '(null))))
        (if (valid-body-ir-argument? cnd) cnd
            (let ((tmp (make-ssavalue)))
              (emit `(= ,tmp ,cnd))
              tmp))))
    (define (emit-cond cnd break-labels endl)
      (let* ((cnd (if (and (pair? cnd) (eq? (car cnd) 'block))
                      (flatten-ex 'block cnd)
                      cnd))
             (cnd (if (and (pair? cnd) (eq? (car cnd) 'block))
                       (begin (if (length> cnd 2) (compile (butlast cnd) break-labels #f #f))
                              (last cnd))
                       cnd))
             (or? (and (pair? cnd) (eq? (car cnd) '|\|\||)))
             (tests (if or?
                        (let ((short-circuit `(goto _)))
                          (for-each
                            (lambda (clause)
                              (let ((jmp (emit `(gotoifnot ,(compile-cond clause break-labels) ,endl))))
                                (emit short-circuit)
                                (set-car! (cddr jmp) (make&mark-label))))
                            (butlast (cdr cnd)))
                          (let ((last-jmp (emit `(gotoifnot ,(compile-cond (last (cdr cnd)) break-labels) ,endl))))
                            (set-car! (cdr short-circuit) (make&mark-label))
                            (list last-jmp)))
                        (map (lambda (clause)
                               (emit `(gotoifnot ,(compile-cond clause break-labels) ,endl)))
                             (if (and (pair? cnd) (eq? (car cnd) '&&))
                                 (cdr cnd)
                                 (list cnd))))))
          tests))
    (define (emit-assignment lhs rhs)
      (if rhs
          (if (valid-ir-rvalue? lhs rhs)
              (emit `(= ,lhs ,rhs))
              (let ((rr (make-ssavalue)))
                (emit `(= ,rr ,rhs))
                (emit `(= ,lhs ,rr))))
          (emit `(= ,lhs (null)))) ; in unreachable code (such as after return), still emit the assignment so that the structure of those uses is preserved
      #f)
    ;; the interpreter loop. `break-labels` keeps track of the labels to jump to
    ;; for all currently closing break-blocks.
    ;; `value` means we are in a context where a value is required; a meaningful
    ;; value must be returned.
    ;; `tail` means we are in tail position, where a value needs to be `return`ed
    ;; from the current function.
    (define (compile e break-labels value tail)
      (if (or (not (pair? e)) (memq (car e) '(null true false ssavalue quote inert top core copyast the_exception $
                                                   globalref thismodule cdecl stdcall fastcall thiscall llvmcall)))
          (let ((e1 (if (and arg-map (symbol? e))
                        (get arg-map e e)
                        e)))
            (if (and value (or (underscore-symbol? e)
                               (and (pair? e) (eq? (car e) 'globalref)
                                    (underscore-symbol? (cadr e)))))
                (error (string "all-underscore identifiers are write-only and their values cannot be used in expressions" (format-loc current-loc))))
            (cond (tail  (emit-return tail e1))
                  (value e1)
                  ((symbol? e1) (emit e1) #f)  ;; keep symbols for undefined-var checking
                  ((and (pair? e1) (eq? (car e1) 'globalref)) (emit e1) #f) ;; keep globals for undefined-var checking
                  (else #f)))
          (case (car e)
            ((call new splatnew foreigncall cfunction new_opaque_closure)
             (define (atom-or-not-tuple-call? fptr)
               (or (atom? fptr)
                   (not (tuple-call? fptr))))
             (let* ((args
                     (cond ((eq? (car e) 'foreigncall)
                            ;; NOTE: 2nd to 5th arguments of ccall must be left in place
                            ;;       the 1st should be compiled if an atom.
                            (append (if (atom-or-not-tuple-call? (cadr e))
                                        (compile-args (list (cadr e)) break-labels)
                                        (list (cadr e)))
                                    (list-head (cddr e) 4)
                                    (compile-args (list-tail e 6) break-labels)))
                           ;; NOTE: arguments of cfunction must be left in place
                           ;;       except for argument 2 (fptr)
                           ((eq? (car e) 'cfunction)
                            (let ((fptr (car (compile-args (list (caddr e)) break-labels))))
                              (cons (cadr e) (cons fptr (cdddr e)))))
                           ;; Leave a literal lambda in place for later global expansion
                           ((eq? (car e) 'new_opaque_closure)
                            (let* ((oc_method (car (list-tail (cdr e) 4))) ;; opaque_closure_method
                                   (lambda (list-ref oc_method 5))
                                   (lambda (linearize lambda)))
                              (append
                               (compile-args (list-head (cdr e) 4) break-labels)
                               (list (append (butlast oc_method) (list lambda)))
                               (compile-args (list-tail (cdr e) 5) break-labels))))
                           ;; NOTE: 1st argument to cglobal treated same as for ccall
                           ((and (length> e 2)
                                 (or (eq? (cadr e) 'cglobal)
                                     (equal? (cadr e) '(globalref (thismodule) cglobal))))
                            (append (list (cadr e))
                                    (if (atom-or-not-tuple-call? (caddr e))
                                        (compile-args (list (caddr e)) break-labels)
                                        (list (caddr e)))
                                    (compile-args (cdddr e) break-labels)))
                           (else
                            (compile-args (cdr e) break-labels))))
                    (callex (cons (car e) args)))
               (cond (tail (emit-return tail callex))
                     (value callex)
                     (else (emit callex)))))
            ((=)
             (let ((lhs (cadr e)))
               (if (and (symbol? lhs) (underscore-symbol? lhs))
                   (compile (caddr e) break-labels value tail)
                   (let* ((rhs (compile (caddr e) break-labels #t #f))
                          (lhs (if (and arg-map (symbol? lhs))
                                   (get arg-map lhs lhs)
                                   lhs)))
                     (if (and value rhs)
                         (let ((rr (if (or (atom? rhs) (ssavalue? rhs) (eq? (car rhs) 'null))
                                       rhs (make-ssavalue))))
                           (if (not (eq? rr rhs))
                               (emit `(= ,rr ,rhs)))
                           (emit `(= ,lhs ,rr))
                           (if tail (emit-return tail rr))
                           rr)
                         (emit-assignment lhs rhs))))))
            ((block)
             (let* ((last-fname filename)
                    (fnm        (first-non-meta e))
                    (fname      (if (and (length> e 1) (linenum? fnm)
                                         (length> fnm 2))
                                    (caddr fnm)
                                    filename))
                    (file-diff  (not (eq? fname last-fname)))
                    ;; don't need a filename node for start of function
                    (need-meta  (and file-diff last-fname
                                     (not (eq? e (lam:body lam)))))
                    (emit-final-meta (lambda ())))
               (if file-diff (set! filename fname))
               (if need-meta (emit `(meta push_loc ,fname)))
               (let ((v (let loop ((xs (cdr e)))
                  (if (only-meta? (cdr xs))
                      (begin (set! emit-final-meta (lambda () (map (lambda (v) (compile v break-labels #f #f)) (cdr xs))))
                             (compile (car xs) break-labels value tail))
                      (begin (compile (car xs) break-labels #f #f)
                             (loop (cdr xs)))))))
                  (if need-meta
                    (cond (tail
                           ;; If we need to return the last non-meta expression
                           ;; attempt to splice the pop_loc before the return
                           ;; so that the return location always gets
                           ;; attributed to the right level of macro
                           (if (and (pair? code) (return? (car code)))
                               (let ((retv (cadr (car code))))
                                 (set! code (cdr code))
                                 (if (not (simple-atom? retv))
                                   (let ((tmp (make-ssavalue)))
                                     (emit `(= ,tmp ,retv))
                                     (set! retv tmp)))
                                 (emit-final-meta)
                                 (emit '(meta pop_loc))
                                 (emit `(return ,retv)))
                               (emit '(meta pop_loc))))
                          ((and v value (not (simple-atom? v)))
                           (let ((tmp (make-ssavalue)))
                             (emit `(= ,tmp ,v))
                             (set! v tmp)
                             (emit-final-meta)
                             (emit `(meta pop_loc))))
                          (else
                           (emit-final-meta)
                           (emit `(meta pop_loc))))
                    (emit-final-meta))
                  (if file-diff (set! filename last-fname))
                  v)))
            ((return)
             (compile (cadr e) break-labels #t 'explicit)
             #f)
            ((unnecessary)
             ;; `unnecessary` marks expressions generated by lowering that
             ;; do not need to be evaluated if their value is unused.
             (if value
                 (compile (cadr e) break-labels value tail)
                 #f))
            ((if elseif)
             (let* ((tests (emit-cond (cadr e) break-labels '_))
                    (end-jump `(goto _))
                    (val (if (and value (not tail)) (new-mutable-var) #f)))
               (let ((v1 (compile (caddr e) break-labels value tail)))
                 (if val (emit-assignment val v1))
                 (if (and (not tail) (or (length> e 3) val))
                     (begin (emit `(line #f))
                            (emit end-jump)))
                 (let ((elselabel (make&mark-label)))
                   (for-each (lambda (test)
                               (set-car! (cddr test) elselabel))
                             tests))
                 (let ((v2 (if (length> e 3)
                               (compile (cadddr e) break-labels value tail)
                               '(null))))
                   (if val (emit-assignment val v2))
                   (if (not tail)
                       (set-car! (cdr end-jump) (make&mark-label))
                       (if (length= e 3)
                           (emit-return tail v2)))
                   val))))
            ((_while)
             (let* ((endl (make-label))
                    (topl (make&mark-label)))
               (emit-cond (cadr e) break-labels endl)
               (compile (caddr e) break-labels #f #f)
               (emit `(goto ,topl))
               (mark-label endl))
             (if value (compile '(null) break-labels value tail)))
            ((_do_while)
             (let* ((endl (make-label))
                    (topl (make&mark-label)))
               (compile (cadr e) break-labels #f #f)
               (let ((test (compile-cond (caddr e) break-labels)))
                 (emit `(gotoifnot ,test ,endl)))
               (emit `(goto ,topl))
               (mark-label endl))
             (if value (compile '(null) break-labels value tail)))
            ((break-block)
             (let ((endl (make-label)))
               (compile (caddr e)
                        (cons (list (cadr e) endl handler-token-stack catch-token-stack)
                              break-labels)
                        #f #f)
               (mark-label endl))
             (if value (compile '(null) break-labels value tail)))
            ((break)
             (let ((labl (assq (cadr e) break-labels)))
               (if (not labl)
                   (error "break or continue outside loop")
                   (emit-break labl))))
            ((label symboliclabel)
             (if (eq? (car e) 'symboliclabel)
                 (if (has? label-nesting (cadr e))
                     (error (string "label \"" (cadr e) "\" defined multiple times"))
                     (put! label-nesting (cadr e) (list handler-token-stack catch-token-stack))))
             (let ((m (get label-map (cadr e) #f)))
               (if m
                   (emit `(label ,m))
                   (put! label-map (cadr e) (make&mark-label)))
               (if tail
                   (emit-return tail '(null))
                   (if value (error "misplaced label")))))
            ((symbolicgoto)
             (let* ((m (get label-map (cadr e) #f))
                    (m (or m (let ((l (make-label)))
                               (put! label-map (cadr e) l)
                               l))))
               (emit `(null))  ;; save space for `leave` that might be needed
               (emit `(goto ,m))
               (set! handler-goto-fixups
                     (cons (list code handler-token-stack catch-token-stack (cadr e)) handler-goto-fixups))
               #f))

            ;; exception handlers are lowered using
            ;; (= tok (enter L scope))
            ;;      push handler with catch block at label L and scope `scope`, yielding token
            ;;      `scope` is only recognized for tryfinally and may be omitted in the lowering
            ;; (leave n) - pop N exception handlers
            ;; (pop_exception tok) - pop exception stack back to state of associated enter
            ((trycatch tryfinally trycatchelse)
             (let ((handler-token (make-ssavalue))
                   (catch (make-label))
                   (catchcode (if (eq? (car e) 'tryfinally) '(call (top rethrow)) (caddr e)))
                   (els   (and (eq? (car e) 'trycatchelse) (make-label)))
                   (endl  (make-label))
                   (last-finally-handler finally-handler)
                   ;; Special case optimization: If the finally block is trivially empty, don't perform finally
                   ;; lowering, just lower this as a try/catch block with rethrow and scope hnadling.
                   (finally           (if (and (eq? (car e) 'tryfinally) (not (code-trivially-effect-free? (caddr e)))) (new-mutable-var) #f))
                   (scope             (if (eq? (car e) 'tryfinally) (cdddr e) '()))
                   (my-finally-handler #f))
               ;; handler block entry
               (emit `(= ,handler-token (enter ,catch ,@(compile-args scope break-labels))))
               (set! handler-token-stack (cons handler-token handler-token-stack))
               (if finally (begin (set! my-finally-handler (list finally endl '() handler-token-stack catch-token-stack))
                                  (set! finally-handler my-finally-handler)
                                  (emit `(= ,finally -1))))
               (let* ((v1 (compile (cadr e) break-labels value #f)) ;; emit try block code
                      (val (if (and value (not tail))
                               (new-mutable-var) #f)))
                 ;; handler block postfix
                 (if (and val v1) (emit-assignment val v1))
                 (if tail
                     (begin (if els
                                (begin (if (and (not val) v1) (emit v1))
                                       (emit `(leave ,handler-token)))
                                (if v1 (emit-return tail v1)))
                            (if (not finally) (set! endl #f)))
                     (begin (emit `(leave ,handler-token))
                            (emit `(goto ,(or els endl)))))
                 (set! handler-token-stack (cdr handler-token-stack))
                 ;; emit else block
                 (if els
                     (begin (mark-label els)
                            (let ((v3 (compile (cadddr e) break-labels value tail))) ;; emit else block code
                              (if val (emit-assignment val v3)))
                            (if endl (emit `(goto ,endl)))))
                 ;; emit either catch or finally block. A combined try/catch/finally block was split into
                 ;; separate trycatch and tryfinally blocks earlier.
                 (mark-label catch)
                 (if finally
                     (begin (enter-finally-block catchcode #f) ;; enter block via exception
                            (mark-label endl) ;; non-exceptional control flow enters here
                            (set! finally-handler last-finally-handler)
                            (compile (caddr e) break-labels #f #f)
                            ;; emit actions to be taken at exit of finally
                            ;; block, depending on the tag variable `finally`
                            (let loop ((actions (caddr my-finally-handler)))
                              (if (pair? actions)
                                  (let ((skip (if (and tail (null? (cdr actions))
                                                       (eq? (car (cdar actions)) 'return))
                                                  #f
                                                  (make-label))))
                                    (if skip
                                        (let ((tmp (make-ssavalue)))
                                          (emit `(= ,tmp (call (core ===) ,finally ,(caar actions))))
                                          (emit `(gotoifnot ,tmp ,skip))))
                                    (let ((ac (cdar actions)))
                                      (cond ((eq? (car ac) 'return) (emit-return tail (cadr ac)))
                                            ((eq? (car ac) 'break)  (emit-break (cadr ac)))
                                            (else ;; assumed to be a rethrow
                                             (emit ac))))
                                    (if skip (mark-label skip))
                                    (loop (cdr actions))))))
                     (begin (set! catch-token-stack (cons handler-token catch-token-stack))
                            (let ((v2 (compile catchcode break-labels value tail)))
                              (if val (emit-assignment val v2))
                              (if (not tail) (emit `(pop_exception ,handler-token)))
                                             ;; else done in emit-return from compile
                              (if endl (mark-label endl)))
                            (set! catch-token-stack (cdr catch-token-stack))))
                 val)))

            ((newvar)
             ;; avoid duplicate newvar nodes
             (if (and (not (and (pair? code) (equal? (car code) e)))
                      ;; exclude deleted vars
                      (has? vinfo-table (cadr e)))
                 (emit e)
                 #f))
            ((global) ; keep global declarations as statements
             (if value (error "misplaced \"global\" declaration"))
             (emit e))
            ((globaldecl)
             (if value (error "misplaced \"global\" declaration"))
             (if (atom? (caddr e)) (emit e)
              (let ((rr (make-ssavalue)))
                (emit `(= ,rr ,(caddr e)))
                (emit `(globaldecl ,(cadr e) ,rr)))))
            ((local-def) #f)
            ((local) #f)
            ((moved-local)
             (set-car! (lam:vinfo lam) (append (car (lam:vinfo lam)) `((,(cadr e) Any 2))))
             #f)
            ((const)
             (if (local-in? (cadr e) lam)
                 (error (string "unsupported `const` declaration on local variable" (format-loc current-loc)))
                 (if (pair? (cadr lam))
                     ;; delay this error to allow "misplaced struct" errors to happen first
                     (if (not global-const-error)
                         (set! global-const-error current-loc))
                     (emit e))))
            ((atomic) (error "misplaced atomic declaration"))
            ((isdefined throw_undef_if_not) (if tail (emit-return tail e) e))
            ((boundscheck) (if tail (emit-return tail e) e))

            ((method)
             (if (not (null? (cadr lam)))
                 (error (string "Global method definition" (linenode-string current-loc)
                                " needs to be placed at the top level, or use \"eval\".")))
             (if (length> e 2)
                 (let* ((sig (let ((sig (compile (caddr e) break-labels #t #f)))
                               (if (valid-ir-argument? sig)
                                   sig
                                   (let ((l (make-ssavalue)))
                                     (emit `(= ,l ,sig))
                                     l))))
                        (lam (cadddr e))
                        (lam (if (and (pair? lam) (eq? (car lam) 'lambda))
                                 (linearize lam)
                                 (let ((l  (make-ssavalue)))
                                   (emit `(= ,l ,(compile lam break-labels #t #f)))
                                   l))))
                   (emit `(method ,(or (cadr e) '(false)) ,sig ,lam))
                   (if value (compile '(null) break-labels value tail)))
                 (cond (tail  (emit-return tail e))
                       (value e)
                       (else  (emit e)))))
            ((lambda)
             (let ((temp (linearize e)))
               (cond (tail  (emit-return tail temp))
                     (value temp)
                     (else  (emit temp)))))

            ;; top level expressions
            ((thunk module)
             (check-top-level e)
             (emit e)
             (if tail (emit-return tail '(null)))
             '(null))
            ((toplevel-only)
             (check-top-level (cdr e))
             '(null))

            ((toplevel)
             (check-top-level e)
             (let ((val (make-ssavalue)))
               (emit `(= ,val ,e))
               (if tail (emit-return tail val))
               val))

            ;; other top level expressions
            ((import using export public)
             (check-top-level e)
             (emit e)
             (let ((have-ret? (and (pair? code) (pair? (car code)) (eq? (caar code) 'return))))
               (if (and tail (not have-ret?))
                   (emit-return tail '(null))))
             '(null))

            ((gc_preserve_begin)
             (let ((args (compile-args (cdr e) break-labels)))
               (cons (car e) args)))

            ;; metadata expressions
            ((lineinfo line meta inbounds loopinfo gc_preserve_end aliasscope popaliasscope inline noinline purity)
             (let ((have-ret? (and (pair? code) (pair? (car code)) (eq? (caar code) 'return))))
               (cond ((eq? (car e) 'line)
                      (set! current-loc e)
                      (if first-line
                          (begin (set! first-line #f)
                                 (emit e))
                          ;; strip filenames out of non-initial line nodes
                          (emit `(line ,(cadr e)))))
                     ((and (eq? (car e) 'meta) (length> e 2) (eq? (cadr e) 'ret-type))
                      (assert (or (not value) tail))
                      (assert (not rett))
                      (set! rett (caddr e)))
                     (else
                      (emit e)))
               (if (and tail (not have-ret?))
                   (emit-return tail '(null)))
               '(null)))

            ;; unsupported assignment operators
            ((≔ ⩴ ≕ :=)
             (error (string "unsupported assignment operator \"" (deparse (car e)) "\"")))

            ;; bare :escape
            ((escape)
             (error (string "\"esc(...)\" used outside of macro expansion")))

            ((error)
             (error (cadr e)))
            (else
             (error (string "invalid syntax " (deparse e)))))))
    ;; introduce new slots for assigned arguments
    (for-each (lambda (v)
                (if (vinfo:asgn v)
                    (begin
                      (if (not arg-map)
                          (set! arg-map (table)))
                      (put! arg-map (car v) (new-mutable-var (car v))))))
              (list-head vi (length (lam:args lam))))
    (compile e '() #t #t)
    (for-each (lambda (x)
                (let ((point (car x))
                      (src-handler-tokens (cadr x))
                      (src-catch-tokens (caddr x))
                      (lab   (cadddr x)))
                  (let ((target-nesting (get label-nesting lab #f)))
                    (if (not target-nesting)
                        (error (string "label \"" lab "\" referenced but not defined")))
                    (let ((target-handler-tokens (car target-nesting))
                          (target-catch-tokens (cadr target-nesting)))
                      (let ((plist (pop-handler-list src-handler-tokens target-handler-tokens lab)))
                        (if plist (set-car! (cdr point) `(leave ,@plist))))
                      (let ((pexc (pop-exc-expr src-catch-tokens target-catch-tokens)))
                        (if pexc (set-cdr! point (cons pexc (cdr point)))))))))
              handler-goto-fixups)
    (if global-const-error
        (error (string "`global const` declaration not allowed inside function" (format-loc global-const-error))))
    (let* ((stmts (reverse! code))
           (di    (definitely-initialized-vars stmts vi))
           (body  (cons 'block (filter (lambda (e)
                                         (not (and (pair? e) (eq? (car e) 'newvar)
                                                   (has? di (cadr e)))))
                                       stmts))))
      (if arg-map
          (insert-after-meta
           body
           (table.foldl (lambda (k v lst) (cons `(= ,v ,k) lst))
                        '() arg-map))
          body))))

(define (for-each-isdefined f e)
  (cond ((or (atom? e) (quoted? e)) #f)
        ((and (pair? e) (eq? (car e) 'isdefined))
         (f (cadr e)))
        (else
         (for-each (lambda (x) (for-each-isdefined f x))
                   (cdr e)))))

;; Find newvar nodes that are unnecessary because (1) the variable is not
;; captured, and (2) the variable is assigned before any branches.
;; This is used to remove newvar nodes that are not needed for re-initializing
;; variables to undefined (see issue #11065).
;; It doesn't look for variable *uses*, because any variables used-before-def
;; that also pass this test are *always* used undefined, and therefore don't need
;; to be *re*-initialized.
;; The one exception to that is `@isdefined`, which can observe an undefined
;; variable without throwing an error.
(define (definitely-initialized-vars stmts vi)
  (let ((vars (table))
        (di   (table)))
    (let loop ((stmts stmts))
      (if (null? stmts)
          di
          (begin
            (let ((e (car stmts)))
              (for-each-isdefined (lambda (x) (if (has? vars x) (del! vars x)))
                                  e)
              (cond ((and (pair? e) (eq? (car e) 'newvar))
                     (let ((vinf (var-info-for (cadr e) vi)))
                       (if (and vinf (not (vinfo:capt vinf)))
                           (put! vars (cadr e) #t))))
                    ((and (pair? e) (or (memq (car e) '(goto gotoifnot))
                                        (and (eq? (car e) '=) (pair? (caddr e))
                                             (eq? (car (caddr e)) 'enter))))
                     (set! vars (table)))
                    ((and (pair? e) (eq? (car e) '=))
                     (if (has? vars (cadr e))
                         (begin (del! vars (cadr e))
                                (put! di (cadr e) #t))))))
            (loop (cdr stmts)))))))

;; pass 6: renumber slots and labels

(define (listify-lambda lam)
  ;; insert `list` expression heads to make the lambda vinfo lists valid expressions
  (let ((vi (lam:vinfo lam)))
    `(lambda (list ,@(cadr lam))
       (list (list ,@(map (lambda (l) (cons 'list l))
                          (car vi)))
             (list ,@(cadr vi)) ,(caddr vi) (list ,@(cadddr vi)))
       ,@(cdddr lam))))

(define (make-lineinfo file line (inlined-at #f))
  `(lineinfo ,file ,line ,(or inlined-at 0)))

(define (set-lineno! lineinfo num)
  (set-car! (cddr lineinfo) num))

(define (compact-ir body file line)
  (let ((code         '(block))
        (locs         '(list))
        (linetable    '(list))
        (linetablelen 0)
        (labltable    (table))
        (ssavtable    (table))
        (current-loc  0)
        (nowhere      #f)
        (current-file file)
        (current-line line)
        (locstack     '())
        (i            1))
    (define (emit e)
      (or e (raise "missing value in IR"))
      (if (and (null? (cdr linetable))
               (not (and (pair? e) (eq? (car e) 'meta))))
          (begin (set! linetable (cons (make-lineinfo file line) linetable))
                 (set! linetablelen (+ linetablelen 1))
                 (set! current-loc 1)))
      (set! code (cons e code))
      (set! i (+ i 1))
      (set! locs (cons (if nowhere 0 current-loc) locs))
      (set! nowhere #f))
    (let loop ((stmts (cdr body)))
      (if (pair? stmts)
          (let ((e (car stmts)))
            (cond ((atom? e) (emit e))
                  ((eq? (car e) 'line)
                   (cond ((and (length= e 2) (not (cadr e)))
                          ;; (line #f) marks that we are entering a generated statement
                          ;; that should not be counted as belonging to the previous marked location,
                          ;; for example `return` after a not-executed `if` arm in tail position.
                          (set! nowhere #t))
                         ((and (= current-line 0) (length= e 2) (pair? linetable))
                          ;; (line n) after push_loc just updates the line for the new file
                          (begin (set-lineno! (car linetable) (cadr e))
                                 (set! current-line (cadr e))))
                         (else
                          (begin
                            (set! current-line (cadr e))
                            (if (pair? (cddr e))
                                (set! current-file (caddr e)))
                            (set! linetable (cons (if (null? locstack)
                                                      (make-lineinfo current-file current-line)
                                                      (make-lineinfo current-file current-line (caar locstack)))
                                                  linetable))
                            (set! linetablelen (+ linetablelen 1))
                            (set! current-loc linetablelen)))))
                  ((and (length> e 2) (eq? (car e) 'meta) (eq? (cadr e) 'push_loc))
                   (set! locstack (cons (list current-loc current-line current-file) locstack))
                   (set! current-file (caddr e))
                   (set! current-line 0)
                   (set! linetable (cons (make-lineinfo current-file current-line current-loc) linetable))
                   (set! linetablelen (+ linetablelen 1))
                   (set! current-loc linetablelen))
                  ((and (length= e 2) (eq? (car e) 'meta) (eq? (cadr e) 'pop_loc))
                   (let ((l (car locstack)))
                     (set! locstack (cdr locstack))
                     (set! current-loc (car l))
                     (set! current-line (cadr l))
                     (set! current-file (caddr l))))
                  ((eq? (car e) 'label)
                   (put! labltable (cadr e) i))
                  ((and (assignment? e) (ssavalue? (cadr e)))
                   (let ((idx (and (ssavalue? (caddr e)) (get ssavtable (cadr (caddr e)) #f))))
                     ;; if both lhs and rhs are ssavalues, merge them
                     (if idx
                         (put! ssavtable (cadr (cadr e)) idx)
                         (begin
                           (put! ssavtable (cadr (cadr e)) i)
                           (emit (caddr e))))))
                  (else
                   (emit e)))
            (loop (cdr stmts)))))
    (vector (reverse code) (reverse locs) (reverse linetable) ssavtable labltable)))

(define (renumber-lambda lam file line)
  (let* ((stuff (compact-ir (lam:body lam)
                            file line))
         (code (aref stuff 0))
         (locs (aref stuff 1))
         (linetab (aref stuff 2))
         (ssavalue-table (aref stuff 3))
         (label-table (aref stuff 4)))
    (set-car! (cdddr lam) code)
    (define nslots (length (car (lam:vinfo lam))))
    (define slot-table (symbol-to-idx-map (map car (car (lam:vinfo lam)))))
    (define sp-table (symbol-to-idx-map (lam:sp lam)))
    (define (renumber-stuff e)
      (cond ((eq? e UNUSED) (error "Attempted to use slot marked unused"))
            ((symbol? e)
             (let ((idx (get slot-table e #f)))
               (if idx
                   `(slot ,idx)
                   (let ((idx (get sp-table e #f)))
                     (if idx
                         `(static_parameter ,idx)
                         e)))))
            ((nospecialize-meta? e)
             ;; convert nospecialize vars to slot numbers
             `(meta ,(cadr e) ,@(map renumber-stuff (cddr e))))
            ((or (atom? e) (quoted? e) (memq (car e) '(using import export public global toplevel)))
             e)
            ((ssavalue? e)
             (let ((idx (get ssavalue-table (cadr e) #f)))
               (if (not idx) (begin (prn e) (prn lam) (error "ssavalue with no def")))
               `(ssavalue ,idx)))
            ((eq? (car e) 'goto)
             `(goto ,(get label-table (cadr e))))
            ((eq? (car e) 'enter)
             `(enter ,(get label-table (cadr e)) ,@(map renumber-stuff (cddr e))))
            ((eq? (car e) 'gotoifnot)
             `(gotoifnot ,(renumber-stuff (cadr e)) ,(get label-table (caddr e))))
            ((eq? (car e) 'lambda)
             (renumber-lambda e 'none 0))
            (else
             (let ((e (cons (car e)
                            (map renumber-stuff (cdr e)))))
               (if (and (eq? (car e) 'foreigncall)
                        (tuple-call? (cadr e))
                        (expr-contains-p (lambda (x) (or (ssavalue? x) (slot? x))) (cadr e)))
                   (error "ccall function name and library expression cannot reference local variables"))
               e))))
    (let ((body (renumber-stuff (lam:body lam)))
          (vi   (lam:vinfo lam)))
      (listify-lambda
       `(lambda ,(cadr lam)
          (,(car vi) ,(cadr vi) ,(length (cdr body)) ,(last vi))
          ,body
          ,locs
          ,linetab)))))

(define (compact-and-renumber ex file line)
  (if (atom? ex) ex
      (if (eq? (car ex) 'lambda)
          (renumber-lambda ex
                           (if (null? (cadr ex)) file 'none)
                           (if (null? (cadr ex)) line 0))
          (cons (car ex)
                (map (lambda (e) (compact-and-renumber e file line))
                     (cdr ex))))))

;; expander entry point

(define (julia-expand1 ex file line)
  (compact-and-renumber
   (linearize
    (closure-convert
     (analyze-variables!
      (resolve-scopes ex)))) file line))

(define *current-desugar-loc* #f)

(define (julia-expand0 ex lno)
  (with-bindings ((*current-desugar-loc* lno))
   (trycatch (expand-forms ex)
             (lambda (e)
               (if (and (pair? e) (eq? (car e) 'error))
                   ; Add location for desugaring errors. This is approximate:
                   ; - Line number nodes are sparse in the AST
                   ; - Line number nodes apply to the next statement, so
                   ;   tracking by `set!`ing *current-desugar-loc* relies on
                   ;   AST traversal being in program order.
                   (error (string (cadr e) (format-loc *current-desugar-loc*))))
                   (raise e)))))

(define (julia-expand ex (file 'none) (line 0))
  (julia-expand1
   (julia-expand0
    (julia-expand-macroscope ex) `(line ,line ,file)) file line))