---
parent: More info
nav_order: 200
description: Aider supports pretty much all popular coding languages.
---
# Supported languages

Aider should work well with most popular coding languages.
This is because top LLMs are fluent in most mainstream languages,
and familiar with popular libraries, packages and frameworks.

Aider has specific support for linting many languages.
By default, aider runs the built in linter any time a file is edited.
If it finds syntax errors, aider will offer to fix them for you.
This helps catch small code issues and quickly fix them.

Aider also does code analysis to help
the LLM navigate larger code bases by producing
a [repository map](https://aider.chat/docs/repomap.html).
Aider can currently produce repository maps for many popular
mainstream languages, listed below.


## How to add support for another language

Aider should work quite well for other languages, even those
without repo map or linter support.
You should really try coding with aider before
assuming it needs better support for your language.

That said, if aider already has support for linting your language,
then it should be possible to add repo map support.
To build a repo map, aider needs the `tags.scm` file
from the given language's tree-sitter grammar.
If you can find and share that file in a 
[GitHub issue](https://github.com/Aider-AI/aider/issues),
then it may be possible to add repo map support.

If aider doesn't already support linting your language, 
it will be more complicated to add support.
Aider relies on
[tree-sitter-language-pack](https://github.com/Goldziher/tree-sitter-language-pack)
to provide pre-packaged versions of tree-sitter
language parsers.
This makes it easy for users to install aider in many diverse environments.
You probably need to work with that project to get your language
supported, which will easily allow aider to lint that language.
For repo-map support, you will also need to find or create a `tags.scm` file.

<!--[[[cog
from aider.repomap import get_supported_languages_md
cog.out(get_supported_languages_md())
]]]-->

| Language | File extension | Repo map | Linter |
|:--------:|:--------------:|:--------:|:------:|
| actionscript         | .as                  |          |   ✓    |
| ada                  | .adb                 |          |   ✓    |
| ada                  | .ads                 |          |   ✓    |
| agda                 | .agda                |          |   ✓    |
| arduino              | .ino                 |    ✓     |   ✓    |
| asm                  | .asm                 |          |   ✓    |
| asm                  | .s                   |          |   ✓    |
| astro                | .astro               |          |   ✓    |
| bash                 | .bash                |          |   ✓    |
| bash                 | .sh                  |          |   ✓    |
| bash                 | .zsh                 |          |   ✓    |
| beancount            | .bean                |          |   ✓    |
| bibtex               | .bib                 |          |   ✓    |
| bicep                | .bicep               |          |   ✓    |
| bitbake              | .bb                  |          |   ✓    |
| bitbake              | .bbappend            |          |   ✓    |
| bitbake              | .bbclass             |          |   ✓    |
| c                    | .c                   |    ✓     |   ✓    |
| c                    | .h                   |    ✓     |   ✓    |
| cairo                | .cairo               |          |   ✓    |
| capnp                | .capnp               |          |   ✓    |
| chatito              | .chatito             |    ✓     |   ✓    |
| clarity              | .clar                |          |   ✓    |
| clojure              | .clj                 |          |   ✓    |
| clojure              | .cljc                |          |   ✓    |
| clojure              | .cljs                |          |   ✓    |
| clojure              | .edn                 |          |   ✓    |
| cmake                | .cmake               |          |   ✓    |
| cmake                | CMakeLists.txt       |          |   ✓    |
| commonlisp           | .cl                  |    ✓     |   ✓    |
| commonlisp           | .lisp                |    ✓     |   ✓    |
| cpon                 | .cpon                |          |   ✓    |
| cpp                  | .cc                  |    ✓     |   ✓    |
| cpp                  | .cpp                 |    ✓     |   ✓    |
| cpp                  | .cxx                 |    ✓     |   ✓    |
| cpp                  | .h++                 |    ✓     |   ✓    |
| cpp                  | .hpp                 |    ✓     |   ✓    |
| cpp                  | .hxx                 |    ✓     |   ✓    |
| csharp               | .cs                  |    ✓     |   ✓    |
| css                  | .css                 |          |   ✓    |
| csv                  | .csv                 |          |   ✓    |
| cuda                 | .cu                  |          |   ✓    |
| cuda                 | .cuh                 |          |   ✓    |
| d                    | .d                   |    ✓     |   ✓    |
| dart                 | .dart                |    ✓     |   ✓    |
| dockerfile           | Dockerfile           |          |   ✓    |
| dtd                  | .dtd                 |          |   ✓    |
| elisp                | .el                  |    ✓     |   ✓    |
| elixir               | .ex                  |    ✓     |   ✓    |
| elixir               | .exs                 |    ✓     |   ✓    |
| elm                  | .elm                 |    ✓     |   ✓    |
| erlang               | .erl                 |          |   ✓    |
| erlang               | .hrl                 |          |   ✓    |
| fennel               | .fnl                 |          |   ✓    |
| firrtl               | .fir                 |          |   ✓    |
| fish                 | .fish                |          |   ✓    |
| fortran              | .f                   |          |   ✓    |
| fortran              | .f03                 |          |   ✓    |
| fortran              | .f08                 |          |   ✓    |
| fortran              | .f90                 |          |   ✓    |
| fortran              | .f95                 |          |   ✓    |
| func                 | .fc                  |          |   ✓    |
| gdscript             | .gd                  |          |   ✓    |
| gitattributes        | .gitattributes       |          |   ✓    |
| gitcommit            | .gitcommit           |          |   ✓    |
| gitignore            | .gitignore           |          |   ✓    |
| gleam                | .gleam               |    ✓     |   ✓    |
| glsl                 | .frag                |          |   ✓    |
| glsl                 | .glsl                |          |   ✓    |
| glsl                 | .vert                |          |   ✓    |
| gn                   | .gn                  |          |   ✓    |
| gn                   | .gni                 |          |   ✓    |
| go                   | .go                  |    ✓     |   ✓    |
| gomod                | go.mod               |          |   ✓    |
| gosum                | go.sum               |          |   ✓    |
| groovy               | .groovy              |          |   ✓    |
| gstlaunch            | .launch              |          |   ✓    |
| hack                 | .hack                |          |   ✓    |
| hare                 | .ha                  |          |   ✓    |
| haskell              | .hs                  |          |   ✓    |
| haxe                 | .hx                  |          |   ✓    |
| hcl                  | .hcl                 |    ✓     |   ✓    |
| hcl                  | .tf                  |    ✓     |   ✓    |
| hcl                  | .tfvars              |    ✓     |   ✓    |
| heex                 | .heex                |          |   ✓    |
| hlsl                 | .hlsl                |          |   ✓    |
| html                 | .htm                 |          |   ✓    |
| html                 | .html                |          |   ✓    |
| hyprlang             | .hypr                |          |   ✓    |
| ispc                 | .ispc                |          |   ✓    |
| janet                | .janet               |          |   ✓    |
| java                 | .java                |    ✓     |   ✓    |
| javascript           | .js                  |    ✓     |   ✓    |
| javascript           | .jsx                 |    ✓     |   ✓    |
| javascript           | .mjs                 |    ✓     |   ✓    |
| jsdoc                | .jsdoc               |          |   ✓    |
| json                 | .json                |          |   ✓    |
| jsonnet              | .jsonnet             |          |   ✓    |
| jsonnet              | .libsonnet           |          |   ✓    |
| julia                | .jl                  |          |   ✓    |
| kconfig              | Kconfig              |          |   ✓    |
| kdl                  | .kdl                 |          |   ✓    |
| kotlin               | .kt                  |    ✓     |   ✓    |
| kotlin               | .kts                 |    ✓     |   ✓    |
| latex                | .cls                 |          |   ✓    |
| latex                | .sty                 |          |   ✓    |
| latex                | .tex                 |          |   ✓    |
| linkerscript         | .ld                  |          |   ✓    |
| llvm                 | .ll                  |          |   ✓    |
| lua                  | .lua                 |    ✓     |   ✓    |
| luadoc               | .luadoc              |          |   ✓    |
| luap                 | .luap                |          |   ✓    |
| luau                 | .luau                |          |   ✓    |
| magik                | .magik               |          |   ✓    |
| make                 | .mk                  |          |   ✓    |
| make                 | Makefile             |          |   ✓    |
| markdown             | .markdown            |          |   ✓    |
| markdown             | .md                  |          |   ✓    |
| matlab               | .m                   |          |   ✓    |
| matlab               | .mat                 |          |   ✓    |
| mermaid              | .mermaid             |          |   ✓    |
| meson                | meson.build          |          |   ✓    |
| ninja                | .ninja               |          |   ✓    |
| nix                  | .nix                 |          |   ✓    |
| nqc                  | .nqc                 |          |   ✓    |
| objc                 | .mm                  |          |   ✓    |
| odin                 | .odin                |          |   ✓    |
| org                  | .org                 |          |   ✓    |
| pascal               | .pas                 |          |   ✓    |
| pascal               | .pp                  |          |   ✓    |
| pem                  | .pem                 |          |   ✓    |
| perl                 | .pl                  |          |   ✓    |
| perl                 | .pm                  |          |   ✓    |
| pgn                  | .pgn                 |          |   ✓    |
| php                  | .php                 |    ✓     |   ✓    |
| po                   | .po                  |          |   ✓    |
| po                   | .pot                 |          |   ✓    |
| pony                 | .pony                |    ✓     |   ✓    |
| powershell           | .ps1                 |          |   ✓    |
| powershell           | .psm1                |          |   ✓    |
| printf               | .printf              |          |   ✓    |
| prisma               | .prisma              |          |   ✓    |
| properties           | .properties          |    ✓     |   ✓    |
| proto                | .proto               |          |   ✓    |
| psv                  | .psv                 |          |   ✓    |
| purescript           | .purs                |          |   ✓    |
| pymanifest           | MANIFEST.in          |          |   ✓    |
| python               | .py                  |    ✓     |   ✓    |
| qmldir               | qmldir               |          |   ✓    |
| qmljs                | .qml                 |          |   ✓    |
| r                    | .R                   |    ✓     |   ✓    |
| r                    | .r                   |    ✓     |   ✓    |
| racket               | .rkt                 |    ✓     |   ✓    |
| re2c                 | .re2c                |          |   ✓    |
| readline             | .inputrc             |          |   ✓    |
| requirements         | requirements.txt     |          |   ✓    |
| ron                  | .ron                 |          |   ✓    |
| rst                  | .rst                 |          |   ✓    |
| ruby                 | .rb                  |    ✓     |   ✓    |
| rust                 | .rs                  |    ✓     |   ✓    |
| scala                | .sc                  |    ✓     |   ✓    |
| scala                | .scala               |    ✓     |   ✓    |
| scheme               | .scm                 |          |   ✓    |
| scheme               | .ss                  |          |   ✓    |
| scss                 | .scss                |          |   ✓    |
| smali                | .smali               |          |   ✓    |
| smithy               | .smithy              |          |   ✓    |
| solidity             | .sol                 |    ✓     |   ✓    |
| sparql               | .rq                  |          |   ✓    |
| sql                  | .sql                 |          |   ✓    |
| squirrel             | .nut                 |          |   ✓    |
| starlark             | .bzl                 |          |   ✓    |
| starlark             | BUILD                |          |   ✓    |
| starlark             | WORKSPACE            |          |   ✓    |
| svelte               | .svelte              |          |   ✓    |
| swift                | .swift               |    ✓     |   ✓    |
| tablegen             | .td                  |          |   ✓    |
| tcl                  | .tcl                 |          |   ✓    |
| thrift               | .thrift              |          |   ✓    |
| toml                 | .toml                |          |   ✓    |
| tsv                  | .tsv                 |          |   ✓    |
| twig                 | .twig                |          |   ✓    |
| typescript           | .ts                  |    ✓     |   ✓    |
| typescript           | .tsx                 |    ✓     |   ✓    |
| typst                | .typ                 |          |   ✓    |
| udev                 | .rules               |    ✓     |   ✓    |
| ungrammar            | .ungram              |          |   ✓    |
| uxntal               | .tal                 |          |   ✓    |
| verilog              | .sv                  |          |   ✓    |
| verilog              | .v                   |          |   ✓    |
| vhdl                 | .vhd                 |          |   ✓    |
| vhdl                 | .vhdl                |          |   ✓    |
| vim                  | .vim                 |          |   ✓    |
| vim                  | .vimrc               |          |   ✓    |
| vue                  | .vue                 |          |   ✓    |
| wgsl                 | .wgsl                |          |   ✓    |
| xcompose             | .XCompose            |          |   ✓    |
| xml                  | .svg                 |          |   ✓    |
| xml                  | .xml                 |          |   ✓    |
| xml                  | .xsl                 |          |   ✓    |
| yuck                 | .yuck                |          |   ✓    |
| zig                  | .zig                 |          |   ✓    |

<!--[[[end]]]-->


