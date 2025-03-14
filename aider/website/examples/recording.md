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

/* Toast notification styling */
.toast-container {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 1000;
  pointer-events: none;
}

.toast-notification {
  background-color: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 10px 20px;
  border-radius: 8px;
  margin-bottom: 10px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
  opacity: 0;
  transition: opacity 0.3s ease-in-out;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  font-size: 16px;
  text-align: center;
  max-width: 80%;
}

/* Page container styling */
.page-container {
  max-height: 80vh;
  max-width: 900px;
  margin-left: auto;
  margin-right: auto;
  position: relative;
}

.terminal-container {
  border-radius: 6px;
  overflow: hidden;
  box-shadow: 0 3px 10px rgba(0, 0, 0, 0.1);
  margin-bottom: 20px;
  position: relative;
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
<script src="/assets/asciinema/asciinema-player.min.js"></script>

<script>
document.addEventListener('DOMContentLoaded', function() {
  const url = "https://gist.githubusercontent.com/paul-gauthier/3011ab9455c2d28c0e5a60947202752f/raw/5a5b3dbf68a9c2b22b4954af287efedecdf79d52/tmp.redacted.cast";
  
  // Create player with a single call
  const player = AsciinemaPlayer.create(
    url,
    document.getElementById('demo'),
    {
      speed: 1.25,
      idleTimeLimit: 1,
      theme: "aider",
      poster: "npt:0:01",
      markers: [
        [3.0, "Hello!"],
        [300.0, "Hello!"],
      ],
    }
  );
  
  // Function to display toast notification
  function showToast(text) {
    const toastContainer = document.getElementById('toast-container');
    
    // Create toast element
    const toast = document.createElement('div');
    toast.className = 'toast-notification';
    toast.textContent = text;
    
    // Add to container
    toastContainer.appendChild(toast);
    
    // Trigger animation
    setTimeout(() => {
      toast.style.opacity = '1';
    }, 10);
    
    // Remove after 3 seconds
    setTimeout(() => {
      toast.style.opacity = '0';
      setTimeout(() => {
        toastContainer.removeChild(toast);
      }, 300); // Wait for fade out animation
    }, 3000);
  }
  
  // Function to speak text using the Web Speech API
  function speakText(text) {
    // Check if speech synthesis is supported
    if ('speechSynthesis' in window) {
      // Create a new speech synthesis utterance
      const utterance = new SpeechSynthesisUtterance(text);
      
      // Optional: Configure voice properties
      utterance.rate = 1.0; // Speech rate (0.1 to 10)
      utterance.pitch = 1.0; // Speech pitch (0 to 2)
      utterance.volume = 1.0; // Speech volume (0 to 1)
      
      // Speak the text
      window.speechSynthesis.speak(utterance);
    } else {
      console.warn('Speech synthesis not supported in this browser');
    }
  }

  // Add event listener with safety checks
  if (player && typeof player.addEventListener === 'function') {
    player.addEventListener('marker', function(event) {
      try {
        const { index, time, label } = event;
        console.log(`marker! ${index} - ${time} - ${label}`);
        
        // Speak the marker label and show toast
        speakText(label);
        showToast(label);
      } catch (error) {
        console.error('Error in marker event handler:', error);
      }
    });
  }
});
</script>

</div>


