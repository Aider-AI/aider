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
        [1.0, "Hello!"],
        [5.0, "Hello, this is a test. This is only a test."],
      ],
    }
  );
  
  // Function to display toast notification
  function showToast(text) {
    // Get the appropriate container based on fullscreen state
    let container = document.getElementById('toast-container');
    const isFullscreen = document.fullscreenElement || 
                         document.webkitFullscreenElement || 
                         document.mozFullScreenElement || 
                         document.msFullscreenElement;
    
    // If in fullscreen, check if we need to create a fullscreen toast container
    if (isFullscreen) {
      // Target the fullscreen element as the container parent
      const fullscreenElement = document.fullscreenElement || 
                               document.webkitFullscreenElement || 
                               document.mozFullScreenElement || 
                               document.msFullscreenElement;
      
      // Look for an existing fullscreen toast container
      let fsContainer = fullscreenElement.querySelector('.fs-toast-container');
      
      if (!fsContainer) {
        // Create a new container for fullscreen mode
        fsContainer = document.createElement('div');
        fsContainer.className = 'toast-container fs-toast-container';
        fsContainer.id = 'fs-toast-container';
        fullscreenElement.appendChild(fsContainer);
      }
      
      container = fsContainer;
    }
    
    // Create toast element
    const toast = document.createElement('div');
    toast.className = 'toast-notification';
    toast.textContent = text;
    
    // Add to container
    container.appendChild(toast);
    
    // Trigger animation
    setTimeout(() => {
      toast.style.opacity = '1';
    }, 10);
    
    // Remove after 3 seconds
    setTimeout(() => {
      toast.style.opacity = '0';
      setTimeout(() => {
        if (container && container.contains(toast)) {
          container.removeChild(toast);
        }
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
