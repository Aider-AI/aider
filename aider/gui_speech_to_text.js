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
    
    // Add elements to container
    container.appendChild(led);
    container.appendChild(button);
    
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
        
        if (!chatInput) {
            console.error("Could not find chat input textarea");
            return false;
        }
        
        try {
            const reactProps = Object.keys(chatInput).find(key => key.startsWith('__reactProps$'));
            
            if (reactProps && chatInput[reactProps] && chatInput[reactProps].onChange) {                
                // Append to the existing value
                chatInput.value = chatInput.value + ' ' + text;
                
                // Create a simplified synthetic event with only essential properties
                const syntheticEvent = {
                    target: chatInput,
                    currentTarget: chatInput,
                    preventDefault: () => {},
                    nativeEvent: new Event('input', { bubbles: true })
                };
                
                // Call React's onChange handler
                chatInput[reactProps].onChange(syntheticEvent);
            } else {
                console.error("Could not find React props on chat input");
                return false;
            }
            
            return true;
        } catch (err) {
            console.error("Error setting chat input value:", err);
            return false;
        }
    }

    // Initialize speech recognition
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    
    recognition.continuous = false;
    recognition.interimResults = false;
    // Use browser's language or fall back to 'en-US'
    recognition.lang = navigator.language || 'en-US';
    console.log('Speech recognition language:', recognition.lang);
    
    // Setup button click handler
    button.addEventListener('click', function() {
        led.style.backgroundColor = 'lime';
        recognition.start();
    });
    
    // Combined event handler function for speech recognition events
    function handleSpeechEvent(eventType, event) {
        // Set LED back to gray for all events
        led.style.backgroundColor = 'gray';
        
        if (eventType === 'result') {
            const transcript = event.results[0][0].transcript;
            
            // Try to populate the chat input directly
            const success = populateChatInput(transcript);
            if (!success)
                console.error('populateChatInput failed');
        } 
        else if (eventType === 'error') {
            console.error('Speech recognition error', event.error);
        }
        // 'end' event requires no special handling beyond resetting the LED
    }
    
    // Set up event handlers using the combined function
    recognition.onresult = function(event) { handleSpeechEvent('result', event); };
    recognition.onerror = function(event) { handleSpeechEvent('error', event); };
    recognition.onend = function() { handleSpeechEvent('end'); };
})();
