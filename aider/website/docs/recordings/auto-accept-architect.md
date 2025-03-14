---
parent: Screen recordings
nav_order: 1
layout: minimal
---

# Add --auto-accept-architect feature

<link rel="stylesheet" type="text/css" href="/assets/asciinema/asciinema-player.css" />

<style>
{% include recording.css %}
</style>

<script src="/assets/asciinema/asciinema-player.min.js"></script>
<script>
const recording_url = "https://gist.githubusercontent.com/paul-gauthier/e7383fbc29c9bb343ee6fb7ee5d77e15/raw/c2194334085304bb1c6bb80814d791704d9719b6/707774.cast";
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

<div class="keyboard-shortcuts">
    <kbd>Space</kbd> Play/pause —
    <kbd>f</kbd> Fullscreen —
    <kbd>←</kbd><kbd>→</kbd> ±5s
</div>

## Commentary

- 0:01 We're going to add a new feature to automatically accept edits proposed by the architect model.
- 0:11 First, let's add the new switch.
- 0:40 Aider figured out that it should be passed to the Coder class.
- 0:48 Now we need to implement the functionality.
- 1:00 Let's do some manual testing.
- 1:28 That worked. Let's make sure we can turn it off too.
- 1:44 That worked too. Let's have aider update the HISTORY file to document the new feature.
- 2:00 Quickly tidy up the changes to HISTORY.
- 2:05 All done!



