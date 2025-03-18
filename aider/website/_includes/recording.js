document.addEventListener('DOMContentLoaded', function() {
  let player; // Store player reference to make it accessible to click handlers
  let globalAudio; // Global audio element to be reused
  
  // Detect if device likely has no physical keyboard
  function detectNoKeyboard() {
    // Check if it's a touch device (most mobile devices)
    const isTouchDevice = ('ontouchstart' in window) || 
                         (navigator.maxTouchPoints > 0) ||
                         (navigator.msMaxTouchPoints > 0);
                         
    // Check common mobile user agents as additional signal
    const isMobileUA = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    
    // If it's a touch device and has a mobile user agent, likely has no physical keyboard
    if (isTouchDevice && isMobileUA) {
      document.body.classList.add('no-physical-keyboard');
    }
  }
  
  // Run detection
  detectNoKeyboard();
  
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
      markers: markers,
      controls: true
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
  
  // Track active toast elements
  let activeToast = null;
  
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
    
    // Remove any existing toast
    if (activeToast) {
      hideToast(activeToast);
    }
    
    // Create toast element
    const toast = document.createElement('div');
    toast.className = 'toast-notification';
    toast.textContent = text;
    
    // Add to container
    container.appendChild(toast);
    
    // Store reference to active toast
    activeToast = {
      element: toast,
      container: container
    };
    
    // Trigger animation
    setTimeout(() => {
      toast.style.opacity = '1';
    }, 10);
    
    return activeToast;
  }
  
  // Function to hide a toast
  function hideToast(toastInfo) {
    if (!toastInfo || !toastInfo.element) return;
    
    toastInfo.element.style.opacity = '0';
    setTimeout(() => {
      if (toastInfo.container && toastInfo.container.contains(toastInfo.element)) {
        toastInfo.container.removeChild(toastInfo.element);
      }
      
      // If this was the active toast, clear the reference
      if (activeToast === toastInfo) {
        activeToast = null;
      }
    }, 300); // Wait for fade out animation
  }
  
  // Track if TTS is currently in progress to prevent duplicates
  let ttsInProgress = false;
  let currentToast = null;
  
  // Improved browser TTS function
  function useBrowserTTS(text) {
    // Don't start new speech if already in progress
    if (ttsInProgress) {
      console.log('Speech synthesis already in progress, skipping');
      return false;
    }
    
    if ('speechSynthesis' in window) {
      console.log('Using browser TTS fallback');
      
      // Set flag to prevent duplicate speech
      ttsInProgress = true;
      
      // Cancel any ongoing speech
      window.speechSynthesis.cancel();
      
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.0;
      utterance.pitch = 1.0;
      utterance.volume = 1.0;
      
      // For iOS, use a shorter utterance if possible
      if (/iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream) {
        utterance.text = text.length > 100 ? text.substring(0, 100) + '...' : text;
      }
      
      utterance.onstart = () => console.log('Speech started');
      utterance.onend = () => {
        console.log('Speech ended');
        ttsInProgress = false; // Reset flag when speech completes
        
        // Hide toast when speech ends
        if (currentToast) {
          hideToast(currentToast);
          currentToast = null;
        }
      };
      utterance.onerror = (e) => {
        console.warn('Speech error:', e);
        ttsInProgress = false; // Reset flag on error
        
        // Also hide toast on error
        if (currentToast) {
          hideToast(currentToast);
          currentToast = null;
        }
      };
      
      window.speechSynthesis.speak(utterance);
      return true;
    }
    console.warn('SpeechSynthesis not supported');
    return false;
  }
  
  // Function to play pre-generated TTS audio files
  function speakText(text, timeInSeconds) {
    // Show the toast and keep reference
    currentToast = showToast(text);
    
    // Format time for filename (MM-SS)
    const minutes = Math.floor(timeInSeconds / 60);
    const seconds = timeInSeconds % 60;
    const formattedTime = `${minutes.toString().padStart(2, '0')}-${seconds.toString().padStart(2, '0')}`;
    
    // Get recording_id from the page or use default from the URL
    const recordingId = typeof recording_id !== 'undefined' ? recording_id : 
                       window.location.pathname.split('/').pop().replace('.html', '');
                       
    // Construct audio file path
    const audioPath = `/assets/audio/${recordingId}/${formattedTime}.mp3`;
    
    // Log for debugging
    console.log(`Attempting to play audio: ${audioPath}`);
    
    // Detect iOS
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
    console.log(`Device is iOS: ${isIOS}`);
    
    // Flag to track if we've already fallen back to TTS
    let fallenBackToTTS = false;
    
    try {
      // Create or reuse audio element
      if (!globalAudio) {
        globalAudio = new Audio();
        console.log("Created new global Audio element");
      }
      
      // Set up event handlers
      globalAudio.onended = () => {
        console.log('Audio playback ended');
        // Hide toast when audio ends
        if (currentToast) {
          hideToast(currentToast);
          currentToast = null;
        }
      };
      
      globalAudio.onerror = (e) => {
        console.warn(`Audio error: ${e.type}`, e);
        if (!fallenBackToTTS) {
          fallenBackToTTS = true;
          useBrowserTTS(text);
        } else if (currentToast) {
          // If we've already tried TTS and that failed too, hide the toast
          hideToast(currentToast);
          currentToast = null;
        }
      };
      
      // For iOS, preload might help with subsequent plays
      if (isIOS) {
        globalAudio.preload = "auto";
      }
      
      // Set the new source
      globalAudio.src = audioPath;
      
      // Play with proper error handling
      const playPromise = globalAudio.play();
      
      if (playPromise !== undefined) {
        playPromise.catch(error => {
          console.warn(`Play error: ${error.message}`);
          
          // On iOS, a user gesture might be required
          if (isIOS) {
            console.log("iOS playback failed, trying SpeechSynthesis");
          }
          
          if (!fallenBackToTTS) {
            fallenBackToTTS = true;
            useBrowserTTS(text);
          }
        });
      }
    } catch (e) {
      console.error(`Exception in audio playback: ${e.message}`);
      useBrowserTTS(text);
    }
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
        
        // Speak the marker label (toast is now shown within speakText)
        speakText(label, time);
        
        // Highlight the corresponding timestamp in the transcript
        highlightTimestamp(time);
      } catch (error) {
        console.error('Error in marker event handler:', error);
      }
    });
  }
});
