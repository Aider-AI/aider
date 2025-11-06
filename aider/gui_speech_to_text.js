(function() {
    // Generate a unique ID for this component instance
    const compId = 'st-speech-to-text-' + Math.random().toString(36).substring(2, 9);
    
    // Find the container element
    const container = document.getElementById('speech-to-text-container');
    if (!container) {
        console.error('Could not find speech-to-text-container');
        return;
    }
    
    // Style the container
    container.style.display = 'flex';
    container.style.alignItems = 'center';
    container.style.padding = '5px';
    container.style.justifyContent = 'space-between';
    
    // Create LED indicator
    const led = document.createElement('div');
    led.id = 'led-' + compId;
    led.style.width = '12px';
    led.style.height = '12px';
    led.style.borderRadius = '50%';
    led.style.backgroundColor = 'gray';
    led.style.marginRight = '10px';
    
    // Create button
    const button = document.createElement('button');
    button.id = 'button-' + compId;
    button.textContent = 'Voice Input';
    button.style.padding = '4px 8px';
    
    // Create stop button (initially hidden)
    const stopButton = document.createElement('button');
    stopButton.id = 'stop-button-' + compId;
    stopButton.textContent = 'Stop';
    stopButton.style.padding = '4px 8px';
    stopButton.style.marginLeft = '5px';
    stopButton.style.display = 'none';
    
    // Create checkbox and label container
    const checkContainer = document.createElement('div');
    checkContainer.style.display = 'flex';
    checkContainer.style.alignItems = 'center';
    checkContainer.style.marginLeft = '10px';
    
    // Create auto-transcribe checkbox
    const autoTranscribe = document.createElement('input');
    autoTranscribe.id = 'auto-transcribe-' + compId;
    autoTranscribe.type = 'checkbox';
    autoTranscribe.style.marginRight = '5px';
    
    // Create label for checkbox
    const label = document.createElement('label');
    label.htmlFor = autoTranscribe.id;
    label.textContent = 'Auto Transcribe';
    label.style.fontSize = '14px';
    label.style.color = 'white';
    
    // Assemble components
    checkContainer.appendChild(autoTranscribe);
    checkContainer.appendChild(label);
    
    // Add elements to container
    container.appendChild(led);
    container.appendChild(button);
    container.appendChild(stopButton);
    container.appendChild(checkContainer);
    
    // Check if browser supports the Web Speech API
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        button.disabled = true;
        button.textContent = 'Not supported';
        return;
    }
    
    // Function to populate the chat input
    function populateChatInput(text) {
        const parentDoc = window.parent.document;
        let chatInput = parentDoc.querySelector('textarea[data-testid="stChatInputTextArea"]');
        const reactProps = Object.keys(chatInput).find(key => key.startsWith('__reactProps$'));
        const syntheticEvent = { target: chatInput, currentTarget: chatInput,
            preventDefault: () => {}, nativeEvent: new Event('input', { bubbles: true })};
        
        if (!chatInput || !reactProps) {
            if (!chatInput)
                console.error("Could not find chat input textarea");
            if (!reactProps)
                console.error("Error setting chat input value:", err);
            return false;
        }
        
        // Append to the existing value
        chatInput.value = chatInput.value + ' ' + text;
        // Call React's onChange handler
        chatInput[reactProps].onChange(syntheticEvent);
        return true;
    }

    // Initialize speech recognition
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    let isListening = false;
    
    recognition.continuous = false;
    recognition.interimResults = false;
    // Use browser's language or fall back to 'en-US'
    recognition.lang = navigator.language || 'en-US';
    console.log('Speech recognition language:', recognition.lang);
    
    // Setup button click handler
    button.addEventListener('click', function() {
        if (isListening) return;
        
        isListening = true;
        
        // Set initial LED color based on auto-transcribe mode
        if (autoTranscribe.checked) {
            led.style.backgroundColor = 'red'; // Red when waiting for voice
            stopButton.style.display = 'inline-block';
            recognition.continuous = true;
        } else {
            led.style.backgroundColor = 'lime';
        }
        
        recognition.start();
    });
    
    // Setup stop button click handler
    stopButton.addEventListener('click', function() {
        if (isListening) {
            recognition.stop();
            stopButton.style.display = 'none';
            isListening = false;
        }
    });
    
    // Handle speech detection
    recognition.onspeechstart = function() {
        console.log('Speech detected');
        if (autoTranscribe.checked) {
            led.style.backgroundColor = 'lime'; // Lime green when voice is detected
        }
    };
    
    // Handle speech end
    recognition.onspeechend = function() {
        console.log('Speech ended');
        if (autoTranscribe.checked && isListening) {
            led.style.backgroundColor = 'red'; // Red when waiting for voice
        }
    };
    
    // Combined event handler function for speech recognition events
    function handleSpeechEvent(eventType, event) {
        if (eventType === 'result') {
            // Get the latest transcript
            const resultIndex = event.resultIndex;
            const transcript = event.results[resultIndex][0].transcript;
            
            // Try to populate the chat input directly
            const success = populateChatInput(transcript);
            if (!success)
                console.error('populateChatInput failed');
            
            // If not in auto-transcribe mode, reset the LED
            if (!autoTranscribe.checked) {
                led.style.backgroundColor = 'gray';
            }
            // In auto-transcribe mode, we'll keep the LED color as is (lime while speaking)
            // The LED will be set back to red in the speechend event
        } 
        else if (eventType === 'error') {
            console.error('Speech recognition error', event.error);
            isListening = false;
            stopButton.style.display = 'none';
            led.style.backgroundColor = 'gray';
        }
        else if (eventType === 'end') {
            // If auto transcribe is enabled and we're still supposed to be listening,
            // restart recognition
            if (autoTranscribe.checked && isListening) {
                setTimeout(() => recognition.start(), 100);
            } else {
                isListening = false;
                stopButton.style.display = 'none';
                led.style.backgroundColor = 'gray';
            }
        }
    }
    
    // Set up event handlers using the combined function
    recognition.onresult = function(event) { handleSpeechEvent('result', event); };
    recognition.onerror = function(event) { handleSpeechEvent('error', event); };
    recognition.onend = function() { handleSpeechEvent('end'); };
})();
