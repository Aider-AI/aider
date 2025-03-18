---
title: Screen recordings
has_children: true
nav_order: 75
has_toc: false
description: Screen recordings of aider building aider.
highlight_image: /assets/recordings.jpg
---

# Screen recordings

Below are a series of screen recordings of the aider developer using aider
to enhance aider.
They contain commentary that describes how aider is being used,
and might provide some inspiration for your own use of aider.

- [Add --auto-accept-architect feature](./auto-accept-architect.html) - See how a new command-line option is added to automatically accept edits proposed by the architect model, with implementation. Aider also updates the project's HISTORY file.

- [Add language support via tree-sitter-language-pack](./tree-sitter-language-pack.html) - Watch how aider adds support for tons of new programming languages by integrating with tree-sitter-language-pack. Demonstrates using aider to script downloading a collection of files, and using ad-hoc bash scripts to have aider modify a collection of files.

- [Don't /drop read-only files added at launch](./dont-drop-original-read-files.html) - Follow along as aider is modified to preserve read-only files specified at launch when using the /drop command. Aider does this implementation and adds test coverage.

- [Warn when users apply unsupported reasoning settings](./model-accepts-settings.html) - Watch the implementation of a warning system that alerts users when they try to apply reasoning settings to models that don't support them. Includes adding model metadata, confirmation dialogs, a debugging wild goose chase, a small refactoring, adding test coverage, updating docs and project history.

