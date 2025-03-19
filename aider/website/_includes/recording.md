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

  <div class="macos-backdrop">
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
</div>

<div class="keyboard-shortcuts">
  <kbd>Space</kbd> Play/pause —
  <kbd>f</kbd> Fullscreen —
  <kbd>←</kbd><kbd>→</kbd> ±5s
</div>
