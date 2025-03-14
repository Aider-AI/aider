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

- 0:01 We're going to add a ton of new languages to aider via tree-sitter-language-pack.
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
- 13:00 Ok, let's download the tags into the right spot in the aider repo.
- 14:00 This will take a minute...
- 16:30 Delete some bad or empty tags files.
- 16:50 Add the tags to the repo.
- 17:50 The tags files need to be modified to work with the repo-map.
- 17:30 Let's use bash to script aider to modify each tags file.
- 18:25 I'm giving aider a read-only example of working tags file, as an example to follow.
- 19:37 Looks like it correctly updated the first couple of tags files.
- 20:22 Let's grep to watch how many name tags are left to be updated.
- 21:00 This is going to take a little while...
- 25:00 Let's add a README file with attribution for these tags files.
- 27:26 Ok, all the tags files are updated.
- 27:40 Let's add test coverage to be sure these languages work with the repo-map.
- 27:50 Dump the fixtures directory structure to a file, to give aider so it knows the layout.
- 28:30 Use a bash script to ask aider to add test coverage for each tags file.
- 28:45 Let aider read the fixtures directory listing.
- 29:20 Just fixing the bash to correctly iterate through the list of tags files.
- 30:11 Improve the prompt to make sure aider creates a fixture for each language.
- 31:00 Lets run the repo-map tests to see if the new test works.
- 31:11 Arduino failed, with an empty repo-map?
- 33:16 Oh! I'm not using the updated grep AST yet.
- 33:26 Ok, now we're parsing Arduino code properly.
- 33:41 A regression with tsx?
- 34:11 Can aider figure out why?
- 34:40 Let's check the parsers map.
- 35:30 Well, that's all for this recording.











