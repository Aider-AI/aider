---
parent: Screen recordings
nav_order: 1
layout: minimal
---

# Don't /drop read-only files added at launch

<link rel="stylesheet" type="text/css" href="/assets/asciinema/asciinema-player.css" />

<style>
{% include recording.css %}
</style>

<script src="/assets/asciinema/asciinema-player.min.js"></script>
<script>
const recording_url = "https://gist.githubusercontent.com/paul-gauthier/c2e7b2751925fb7bb47036cdd37ec40d/raw/08e62ab539e2b5d4b52c15c31d9a0d241377c17c/707583.cast";
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

- 0:01 We're going to update the /drop command to keep any read only files that were originally specified at launch.
- 0:10 We've added files that handle the main C.L.I. and in-chat slash commands like /drop.
- 0:20 Explain the needed change to aider.
- 1:20 Ok, let's look at the code.
- 1:30 I'd prefer not to use "hasattr()", let's ask for improvements.
- 1:45 Let's try some manual testing.
- 2:10 Looks good. Let's check the existing test suite to ensure we didn't break anything.
- 2:19 Let's ask aider to add tests for this.
- 2:50 Tests look reasonable, we're done!







