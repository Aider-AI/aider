---
parent: More info
nav_order: 900
description: Aider supports pretty much all popular coding languages.
---
# Supported languages

Aider supports pretty much all the popular coding languages.
This is partly because top LLMs are fluent in most mainstream languages,
and familiar with popular libraries, packages and frameworks.

In fact, coding with aider is sometimes the most magical
when you're working in a language that you
are less familiar with.
the LLM often knows the language better than you,
and can generate all the boilerplate to get to the heart of your
problem.
The LLM will often solve your problem in an elegant way
using a library or package that you weren't even aware of.

Aider uses tree-sitter to do code analysis and help
the LLM navigate larger code bases by producing
a [repository map](https://aider.chat/docs/repomap.html).

Aider can currently produce repository maps for most mainstream languages, listed below.
But aider should work quite well for other languages, even without repo map support.

<!--[[[cog
from aider.repomap import get_supported_languages_md
cog.out(get_supported_languages_md())
]]]-->

| Language | File extension |
|:--------:|:--------------:|
| bash                 | .bash                |
| c                    | .c                   |
| c_sharp              | .cs                  |
| commonlisp           | .cl                  |
| cpp                  | .cc                  |
| cpp                  | .cpp                 |
| css                  | .css                 |
| dockerfile           | .dockerfile          |
| dot                  | .dot                 |
| elisp                | .el                  |
| elixir               | .ex                  |
| elm                  | .elm                 |
| embedded_template    | .et                  |
| erlang               | .erl                 |
| go                   | .go                  |
| gomod                | .gomod               |
| hack                 | .hack                |
| haskell              | .hs                  |
| hcl                  | .hcl                 |
| html                 | .html                |
| java                 | .java                |
| javascript           | .js                  |
| javascript           | .mjs                 |
| jsdoc                | .jsdoc               |
| json                 | .json                |
| julia                | .jl                  |
| kotlin               | .kt                  |
| lua                  | .lua                 |
| make                 | .mk                  |
| objc                 | .m                   |
| ocaml                | .ml                  |
| perl                 | .pl                  |
| php                  | .php                 |
| python               | .py                  |
| ql                   | .ql                  |
| r                    | .R                   |
| r                    | .r                   |
| regex                | .regex               |
| rst                  | .rst                 |
| ruby                 | .rb                  |
| rust                 | .rs                  |
| scala                | .scala               |
| sql                  | .sql                 |
| sqlite               | .sqlite              |
| toml                 | .toml                |
| tsq                  | .tsq                 |
| typescript           | .ts                  |
| typescript           | .tsx                 |
| yaml                 | .yaml                |

<!--[[[end]]]-->

