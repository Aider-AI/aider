(FnProto
  (IDENTIFIER) @name.definition.function) @definition.function

(VarDecl
  "const"
  (IDENTIFIER) @name.definition.constant) @definition.constant

(VarDecl
  "var"
  (IDENTIFIER) @name.definition.variable) @definition.variable

(
  (SuffixExpr
    (BUILTINIDENTIFIER) @func
    (FnCallArguments
      (ErrorUnionExpr
        (SuffixExpr
          (STRINGLITERALSINGLE) @name.reference.import)))) @reference.import
  (#eq? @func "@import")
)