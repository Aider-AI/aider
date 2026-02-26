---
parent: Architecture Overview
nav_order: 180
---

# Edit Formats

Aider supports several ways for the LLM to express code changes.  The main ones are `whole`, `diff`, `diff-fenced`, and `udiff`.  Each `Model` declares its preferred format in `models.yml`.  The CLI option `--edit-format` can override this choice.

At runtime `Coder.create()` inspects the requested format and picks the appropriate subclass (`WholeCoder`, `DiffCoder`, etc.).  The prompts for each format live in `aider/prompts/*`.

For details on the syntax of each format see [Edit formats](../more/edit-formats.html).

