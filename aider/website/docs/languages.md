---
parent: More info
nav_order: 900
description: Aider supports pretty much all popular coding languages.
---
# Supported languages

Aider supports almost all popular coding languages.
This is because top LLMs are fluent in most mainstream languages,
and familiar with popular libraries, packages and frameworks.

Aider uses tree-sitter to do code analysis and help
the LLM navigate larger code bases by producing
a [repository map](https://aider.chat/docs/repomap.html).
Aider can currently produce repository maps for many popular
mainstream languages, listed below.

Aider should work quite well for other languages, even without repo map support.

<!--[[[cog
from aider.repomap import get_supported_languages_md
cog.out(get_supported_languages_md())
]]]-->

| Language | File extension |
|:--------:|:--------------:|
| c                    | .c                   |
| c_sharp              | .cs                  |
| cpp                  | .cc                  |
| cpp                  | .cpp                 |
| elisp                | .el                  |
| elixir               | .ex                  |
| elm                  | .elm                 |
| go                   | .go                  |
| java                 | .java                |
| javascript           | .js                  |
| javascript           | .mjs                 |
| ocaml                | .ml                  |
| php                  | .php                 |
| python               | .py                  |
| ql                   | .ql                  |
| ruby                 | .rb                  |
| rust                 | .rs                  |
| typescript           | .ts                  |
| typescript           | .tsx                 |

<!--[[[end]]]-->

