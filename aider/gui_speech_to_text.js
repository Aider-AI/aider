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
            // Try to access React internals
            const reactProps = Object.keys(chatInput).find(key => key.startsWith('__reactProps$'));
            
            if (reactProps && chatInput[reactProps] && chatInput[reactProps].onChange) {
                // If we can access React props, use the onChange handler directly
                
                // Append to the existing value
                chatInput.value = chatInput.value + ' ' + text;
                
                // Create a synthetic event that React's onChange will accept
                const syntheticEvent = {
                    target: chatInput,
                    currentTarget: chatInput,
                    preventDefault: () => {},
                    stopPropagation: () => {},
                    persist: () => {},
                    isDefaultPrevented: () => false,
                    isPropagationStopped: () => false,
                    bubbles: true,
                    cancelable: true,
                    nativeEvent: new Event('input', { bubbles: true })
                };
                
                // Call React's onChange handler
                chatInput[reactProps].onChange(syntheticEvent);
            } else {
                // Fallback to standard DOM approach with multiple event types
                
                // Focus first
                chatInput.focus();
                
                // Append to the existing value
                chatInput.value = chatInput.value + text;
                
                // Dispatch multiple event types to ensure detection
                ['input', 'change', 'blur', 'keydown', 'keyup'].forEach(eventType => {
                    const event = new Event(eventType, { bubbles: true, cancelable: true });
                    chatInput.dispatchEvent(event);
                });
                
                // For Streamlit specifically, try to trigger any MutationObservers or polling
                // that might be watching for changes
                setTimeout(() => {
                    chatInput.dispatchEvent(new Event('change', { bubbles: true }));
                    chatInput.dispatchEvent(new Event('blur', { bubbles: true }));
                }, 100);
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
    recognition.lang = 'en-US';
    
    // Setup button click handler
    button.addEventListener('click', function() {
        led.style.backgroundColor = 'green';
        recognition.start();
    });
    
    recognition.onresult = function(event) {
        const transcript = event.results[0][0].transcript;
        led.style.backgroundColor = 'gray';
        
        // Try to populate the chat input directly
        const success = populateChatInput(transcript);
        
        if (!success) {
            console.error('populateChatInput failed');
            
            // Add a debug display with the transcribed text
            const debugContainer = document.createElement('div');
            debugContainer.style.padding = '10px';
            debugContainer.style.marginTop = '10px';
            debugContainer.style.backgroundColor = '#ffeeee';
            debugContainer.style.border = '1px solid #ffcccc';
            debugContainer.innerHTML = `
                <div><strong>Debug: Transcribed text</strong></div>
                <div><textarea style="width: 100%; height: 80px;">${transcript}</textarea></div>
            `;
            container.appendChild(debugContainer);
        }
    };
    
    recognition.onerror = function(event) {
        console.error('Speech recognition error', event.error);
        led.style.backgroundColor = 'gray';
    };
    
    recognition.onend = function() {
        led.style.backgroundColor = 'gray';
    };
})();
