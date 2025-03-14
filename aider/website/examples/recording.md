---
parent: Example chat transcripts
nav_order: 9999
layout: minimal
---

# Recording

<link rel="stylesheet" type="text/css" href="/assets/asciinema/asciinema-player.css" />

<style>
{% include recording.css %}
</style>

<script src="/assets/asciinema/asciinema-player.min.js"></script>
<script>
{% include recording.js %}
</script>

<div class="page-container">
<div class="toast-container" id="toast-container"></div>
<div class="terminal-container">
  <div class="terminal-header">
    <div class="terminal-buttons">
      <div class="terminal-button terminal-close"></div>
      <div class="terminal-button terminal-minimize"></div>
      <div class="terminal-button terminal-expand"></div>
    </div>
    <div class="terminal-title">aider</div>
  </div>
  <div id="demo"></div>
</div>
</div>

# Transcript

- 0:01 We're going to add 130 new languages to aider via tree-sitter-language-pack.
- 0:10 First, lets try and find which languages it supports.
- 1:00 Ok, there's a language definitions json file
- 1:10 Does it have the github repos for each language?
- 1:57 We need all the tags files from each language's repository. Let's have aider write a script to fetch them all.
- 3:37 Looks like it can't find most of the tags.scm files.
- 4:00 Have it try other branches besides master.
- 5:02 Ok, it's downloading them now.
- 5:55 Let's make it so we can re-run and avoid re-downloading.
- 6:12 I see lots of tags files.
- 6:30 Ok, restart to run with latest code. This will take awhile to fetch them all.
- 9:02 The grep AST module needs to know about all the new languages.
- 9:45 Let's have aider add them all, including their file extensions.
- 10:15 Some of the languages need to be recognized by their base name, not extension.
- 11:15 Let's sanity check if grep AST can handle PowerShell now.
- 12:00 Looks like it's parsing PowerShell fine.





