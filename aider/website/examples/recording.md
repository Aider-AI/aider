---
parent: Example chat transcripts
nav_order: 9999
layout: minimal
---

# Recording

<link rel="stylesheet" type="text/css" href="/assets/asciinema/asciinema-player.css" />

<style>
/* Terminal header styling */
.terminal-header {
  background-color: #e0e0e0;
  border-top-left-radius: 6px;
  border-top-right-radius: 6px;
  padding: 4px 10px;
  display: flex;
  align-items: center;
  border-bottom: 1px solid #c0c0c0;
}

.terminal-buttons {
  display: flex;
  gap: 4px;
  margin-right: 10px;
}

.terminal-button {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.terminal-close {
  background-color: #ff5f56;
  border: 1px solid #e0443e;
}

.terminal-minimize {
  background-color: #ffbd2e;
  border: 1px solid #dea123;
}

.terminal-expand {
  background-color: #27c93f;
  border: 1px solid #1aab29;
}

.terminal-title {
  flex-grow: 1;
  text-align: center;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  font-size: 11px;
  color: #666;
}

.terminal-container {
  border-radius: 6px;
  overflow: hidden;
  box-shadow: 0 3px 10px rgba(0, 0, 0, 0.1);
  margin-bottom: 20px;
}
.asciinema-player-theme-aider {
  /* Foreground (default text) color */
  --term-color-foreground: #444444;  /* colour238 */

  /* Background color */
  --term-color-background: #dadada;  /* colour253 */

  /* Palette of 16 standard ANSI colors */
  --term-color-0: #21222c;
  --term-color-1: #ff5555;
  --term-color-2: #50fa7b;
  --term-color-3: #f1fa8c;
  --term-color-4: #bd93f9;
  --term-color-5: #ff79c6;
  --term-color-6: #8be9fd;
  --term-color-7: #f8f8f2;
  --term-color-8: #6272a4;
  --term-color-9: #ff6e6e;
  --term-color-10: #69ff94;
  --term-color-11: #ffffa5;
  --term-color-12: #d6acff;
  --term-color-13: #ff92df;
  --term-color-14: #a4ffff;
  --term-color-15: #ffffff;
}
</style>

<div class="terminal-container">
  <div class="terminal-header">
    <div class="terminal-buttons">
      <div class="terminal-button terminal-close"></div>
      <div class="terminal-button terminal-minimize"></div>
      <div class="terminal-button terminal-expand"></div>
    </div>
    <div class="terminal-title">aider</div>
  </div>
  <div id="demo" style="max-height: 80vh;"></div>
</div>
<script src="/assets/asciinema/asciinema-player.min.js"></script>

<script>
url = "https://gist.githubusercontent.com/paul-gauthier/3011ab9455c2d28c0e5a60947202752f/raw/5a5b3dbf68a9c2b22b4954af287efedecdf79d52/tmp.redacted.cast";
AsciinemaPlayer.create(
     url,
     document.getElementById('demo'),
     {
         speed: 1.25,
         idleTimeLimit: 1,
         theme : "aider",
         poster : "npt:0:01",
         markers : [
             [3.0, "Hello!"],
             [300.0, "Hello!"],
         ],
     }
 );
 
AsciinemaPlayer.create(
     url,
     document.getElementById('demo'),
     {
         speed: 1.25,
         idleTimeLimit: 1,
         theme : "aider",
         poster : "npt:0:01",
         markers : [
             [3.0, "Hello!"],
             [300.0, "Hello!"],
         ],
     }
 ).addEventListener('marker', ({ index, time, label }) => {
  console.log(`marker! ${index} - ${time} - ${label}`);
  
  // Add the marker label to the transcript
  const transcriptContent = document.getElementById('transcript-content');
  const markerElement = document.createElement('div');
  markerElement.textContent = label;
  markerElement.style.fontWeight = 'bold';
  markerElement.style.marginTop = '10px';
  transcriptContent.appendChild(markerElement);
});
</script>

<div class="transcript-container" style="margin-top: 30px; padding: 20px; background-color: #f8f8f8; border-radius: 6px; max-height: 50vh; overflow-y: auto; font-family: monospace; white-space: pre-wrap; line-height: 1.5;">
  <div id="transcript-content">
  </div>
</div>

  
