document.addEventListener('DOMContentLoaded', function() {
  let player; // Store player reference to make it accessible to click handlers
  
  // Parse the transcript section to create markers and convert timestamps to links
  function parseTranscript() {
    const markers = [];
    // Find the Commentary heading
    const transcriptHeading = Array.from(document.querySelectorAll('h2')).find(el => el.textContent.trim() === 'Commentary');
    
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
            timeLink.dataset.message = message;
            
            // Add click event to seek the player
            timeLink.addEventListener('click', function(e) {
              e.preventDefault();
              if (player && typeof player.seek === 'function') {
                player.seek(timeInSeconds);
                player.play();
                
                // Also trigger toast and speech
                showToast(message);
                speakText(message, timeInSeconds);
                
                // Highlight this timestamp
                highlightTimestamp(timeInSeconds);
              }
            });
            
            // Replace text with the link + message
            item.textContent = '';
            item.appendChild(timeLink);
            item.appendChild(document.createTextNode(' ' + message));
            
            // Add class and click handler to the entire list item
            item.classList.add('transcript-item');
            item.dataset.time = timeInSeconds;
            item.dataset.message = message;
            
            item.addEventListener('click', function(e) {
              // Prevent click event if the user clicked directly on the timestamp link
              // This prevents double-firing of the event
              if (e.target !== timeLink) {
                e.preventDefault();
                if (player && typeof player.seek === 'function') {
                  player.seek(timeInSeconds);
                  player.play();
                  
                  // Also trigger toast and speech
                  showToast(message);
                  speakText(message, timeInSeconds);
                  
                  // Highlight this timestamp
                  highlightTimestamp(timeInSeconds);
                }
              }
            });
            
            markers.push([timeInSeconds, message]);
          }
        });
        
        currentElement = currentElement.nextElementSibling;
      }
    }
    
    return markers;
  }

  // Parse transcript and create markers
  const markers = parseTranscript();
  
  // Create player with a single call
  player = AsciinemaPlayer.create(
    recording_url,
    document.getElementById('demo'),
    {
      speed: 1.25,
      idleTimeLimit: 1,
      theme: "aider",
      poster: "npt:0:01",
      markers: markers
    }
  );
  
  // Focus on the player element so keyboard shortcuts work immediately
  setTimeout(() => {
    // Use setTimeout to ensure the player is fully initialized
    if (player && typeof player.focus === 'function') {
      player.focus();
    } else {
      // If player doesn't have a focus method, try to find and focus the terminal element
      const playerElement = document.querySelector('.asciinema-terminal');
      if (playerElement) {
        playerElement.focus();
      } else {
        // Last resort - try to find element with tabindex
        const tabbableElement = document.querySelector('[tabindex]');
        if (tabbableElement) {
          tabbableElement.focus();
        }
      }
    }
  }, 100);
  
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
  
  // Function to use browser's TTS as fallback
  function useBrowserTTS(text) {
    if ('speechSynthesis' in window) {
      console.log('Using browser TTS fallback');
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.0;
      utterance.pitch = 1.0;
      utterance.volume = 1.0;
      window.speechSynthesis.speak(utterance);
      return true;
    }
    return false;
  }
  
  // Function to play pre-generated TTS audio files
  function speakText(text, timeInSeconds) {
    // Format time for filename (MM-SS)
    const minutes = Math.floor(timeInSeconds / 60);
    const seconds = timeInSeconds % 60;
    const formattedTime = `${minutes.toString().padStart(2, '0')}-${seconds.toString().padStart(2, '0')}`;
    
    // Get recording_id from the page or use default from the URL
    const recordingId = typeof recording_id !== 'undefined' ? recording_id : 
                       window.location.pathname.split('/').pop().replace('.html', '');
                       
    // Construct audio file path
    const audioPath = `/assets/audio/${recordingId}/${formattedTime}.mp3`;
    
    // Create and play audio
    const audio = new Audio(audioPath);
    
    // Flag to track if we've already used the TTS fallback
    let fallbackUsed = false;
    
    // Error handling with fallback to browser TTS
    audio.onerror = () => {
      console.warn(`Failed to load audio: ${audioPath}`);
      if (!fallbackUsed) {
        fallbackUsed = true;
        useBrowserTTS(text);
      }
    };
    
    // Play the audio
    audio.play().catch(e => {
      console.warn(`Error playing audio: ${e.message}`);
      // Also fall back to browser TTS if play() fails
      if (!fallbackUsed) {
        fallbackUsed = true;
        useBrowserTTS(text);
      }
    });
  }
  
  // Function to highlight the active timestamp in the transcript
  function highlightTimestamp(timeInSeconds) {
    // Remove previous highlights
    document.querySelectorAll('.timestamp-active').forEach(el => {
      el.classList.remove('timestamp-active');
    });
    
    document.querySelectorAll('.active-marker').forEach(el => {
      el.classList.remove('active-marker');
    });
    
    // Find the timestamp link with matching time
    const timestampLinks = document.querySelectorAll('.timestamp-link');
    let activeLink = null;
    
    for (const link of timestampLinks) {
      if (parseInt(link.dataset.time) === timeInSeconds) {
        activeLink = link;
        break;
      }
    }
    
    if (activeLink) {
      // Add highlight class to the link
      activeLink.classList.add('timestamp-active');
      
      // Also highlight the parent list item
      const listItem = activeLink.closest('li');
      if (listItem) {
        listItem.classList.add('active-marker');
        
        // No longer scrolling into view to avoid shifting focus
      }
    }
  }

  // Add event listener with safety checks
  if (player && typeof player.addEventListener === 'function') {
    player.addEventListener('marker', function(event) {
      try {
        const { index, time, label } = event;
        console.log(`marker! ${index} - ${time} - ${label}`);
        
        // Speak the marker label and show toast
        speakText(label, time);
        showToast(label);
        
        // Highlight the corresponding timestamp in the transcript
        highlightTimestamp(time);
      } catch (error) {
        console.error('Error in marker event handler:', error);
      }
    });
  }
});
