document.addEventListener('DOMContentLoaded', function() {
  let player; // Store player reference to make it accessible to click handlers
  
  // Parse the transcript section to create markers and convert timestamps to links
  function parseTranscript() {
    const markers = [];
    // Find the Transcript heading
    const transcriptHeading = Array.from(document.querySelectorAll('h1')).find(el => el.textContent.trim() === 'Transcript');
    
    if (transcriptHeading) {
      // Get all list items after the transcript heading
      let currentElement = transcriptHeading.nextElementSibling;
      
      while (currentElement && currentElement.tagName === 'UL') {
        const listItems = currentElement.querySelectorAll('li');
        
        listItems.forEach(item => {
          const text = item.textContent.trim();
          const match = text.match(/(\d+):(\d+)\s+(.*)/);
          
          if (match) {
            const minutes = parseInt(match[1], 10);
            const seconds = parseInt(match[2], 10);
            const timeInSeconds = minutes * 60 + seconds;
            const formattedTime = `${minutes}:${seconds.toString().padStart(2, '0')}`;
            const message = match[3].trim();
            
            // Create link for the timestamp
            const timeLink = document.createElement('a');
            timeLink.href = '#';
            timeLink.textContent = formattedTime;
            timeLink.className = 'timestamp-link';
            timeLink.dataset.time = timeInSeconds;
            
            // Add click event to seek the player
            timeLink.addEventListener('click', function(e) {
              e.preventDefault();
              if (player && typeof player.seek === 'function') {
                player.seek(timeInSeconds);
                player.play();
              }
            });
            
            // Replace text with the link + message
            item.textContent = '';
            item.appendChild(timeLink);
            item.appendChild(document.createTextNode(' ' + message));
            
            markers.push([timeInSeconds, message]);
          }
        });
        
        currentElement = currentElement.nextElementSibling;
      }
    }
    
    return markers;
  }

  const url = "https://gist.githubusercontent.com/paul-gauthier/3011ab9455c2d28c0e5a60947202752f/raw/5a5b3dbf68a9c2b22b4954af287efedecdf79d52/tmp.redacted.cast";
  
  // Parse transcript and create markers
  const markers = parseTranscript();
  
  // Create player with a single call
  player = AsciinemaPlayer.create(
    url,
    document.getElementById('demo'),
    {
      speed: 1.25,
      idleTimeLimit: 1,
      theme: "aider",
      poster: "npt:0:01",
      markers: markers
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
