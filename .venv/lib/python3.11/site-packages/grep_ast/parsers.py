import os

# Updated mapping of file extensions to parsers
PARSERS = {
    ".py": "python",
    ".js": "javascript",
    ".mjs": "javascript", # mjs file extension stands for "module JavaScript."
    ".go": "go",
    ".bash": "bash",
    ".c": "c",
    ".cc": "cpp",
    ".cs": "c_sharp",
    ".cl": "commonlisp",
    ".cpp": "cpp",
    ".css": "css",
    ".dockerfile": "dockerfile",
    ".dot": "dot",
    ".el": "elisp",
    ".ex": "elixir",
    ".elm": "elm",
    ".et": "embedded_template",
    ".erl": "erlang",
    ".gomod": "gomod",
    ".hack": "hack",
    ".hs": "haskell",
    ".hcl": "hcl",
    ".html": "html",
    ".java": "java",
    ".jsdoc": "jsdoc",
    ".json": "json",
    ".jl": "julia",
    ".kt": "kotlin",
    ".lua": "lua",
    ".mk": "make",
    # ".md": "markdown", # https://github.com/ikatyang/tree-sitter-markdown/issues/59
    ".m": "objc",
    ".ml": "ocaml",
    ".pl": "perl",
    ".php": "php",
    ".ql": "ql",
    ".r": "r",
    ".R": "r",
    ".regex": "regex",
    ".rst": "rst",
    ".rb": "ruby",
    ".rs": "rust",
    ".scala": "scala",
    ".sql": "sql",
    ".sqlite": "sqlite",
    ".toml": "toml",
    ".tsq": "tsq",
    ".tsx": "typescript",
    ".ts": "typescript",
    ".yaml": "yaml",
}


def filename_to_lang(filename):
    file_extension = os.path.splitext(filename)[1]
    lang = PARSERS.get(file_extension)
    return lang
