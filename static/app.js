document.addEventListener('DOMContentLoaded', () => {
    const chatContainer = document.getElementById('chat-container');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');

    // Check initial status
    fetch('/status')
        .then(response => response.json())
        .then(data => {
            if (data.status !== 'ready') {
                appendMessage('system', data.message);
            }
        })
        .catch(error => {
            appendMessage('error', 'Failed to connect to server');
        });

    function appendMessage(type, content, sources = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'p-4 rounded-lg ' +
            (type === 'user' ? 'bg-blue-100' :
             type === 'assistant' ? 'bg-gray-100' :
             type === 'error' ? 'bg-red-100' : 'bg-yellow-100');

        const textDiv = document.createElement('div');
        textDiv.className = 'text-gray-800';

        if (type === 'user') {
            textDiv.innerHTML = `<span class="font-bold">You:</span> ${content}`;
        } else if (type === 'assistant') {
            textDiv.innerHTML = `<span class="font-bold">Assistant:</span> ${content}`;
        } else if (type === 'error') {
            textDiv.innerHTML = `<span class="font-bold text-red-600">Error:</span> ${content}`;
        } else {
            textDiv.innerHTML = `<span class="font-bold text-yellow-600">System:</span> ${content}`;
        }

        messageDiv.appendChild(textDiv);

        if (sources) {
            const sourcesDiv = document.createElement('div');
            sourcesDiv.className = 'mt-2 text-sm text-gray-600 italic';
            sourcesDiv.textContent = `Sources: ${sources}`;
            messageDiv.appendChild(sourcesDiv);
        }

        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
        return messageDiv;
    }

    function sendQuery() {
        const query = userInput.value.trim();
        if (!query) return;

        // Disable input and button while processing
        userInput.disabled = true;
        sendButton.disabled = true;
        sendButton.classList.add('opacity-50');

        // Add user message
        appendMessage('user', query);

        // Clear input
        userInput.value = '';

        // Create assistant message with loader
        const assistantDiv = document.createElement('div');
        assistantDiv.className = 'p-4 rounded-lg bg-gray-100';

        const assistantContent = document.createElement('div');
        assistantContent.className = 'text-gray-800';
        assistantContent.innerHTML = `
            <div class="flex items-center space-x-2">
                <span class="font-bold">Assistant:</span>
                <div class="typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;

        assistantDiv.appendChild(assistantContent);
        chatContainer.appendChild(assistantDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;

        // Create EventSource connection
        const encodedMessage = encodeURIComponent(query);
        const eventSource = new EventSource(`/api/chat-stream?message=${encodedMessage}`);

        // Handle message events
        eventSource.onmessage = (event) => {
            const data = event.data;

            // Check for end of stream
            if (data === "[DONE]") {
                eventSource.close();
                enableInput();
                return;
            }

            // Extract sources if present
            let displayText = data;
            let sourceText = null;

            if (data.includes("Sources:")) {
                const parts = data.split("Sources:");
                displayText = parts[0].trim();
                sourceText = parts[1].trim();
            }

            // Hide the loading animation on first message
            const loadingElement = assistantContent.querySelector('.typing-dots')?.parentElement;
            if (loadingElement) {
                assistantContent.innerHTML = `<span class="font-bold">Assistant:</span> ${displayText}`;
            } else {
                // Update existing content
                assistantContent.innerHTML += displayText;
            }

            // Add sources if present
            if (sourceText) {
                let sourcesDiv = assistantDiv.querySelector('.sources');
                if (!sourcesDiv) {
                    sourcesDiv = document.createElement('div');
                    sourcesDiv.className = 'mt-2 text-sm text-gray-600 italic sources';
                    assistantDiv.appendChild(sourcesDiv);
                }
                sourcesDiv.textContent = `Sources: ${sourceText}`;
            }

            chatContainer.scrollTop = chatContainer.scrollHeight;
        };

        // Handle errors
        eventSource.onerror = (error) => {
            console.error('EventSource error:', error);

            if (assistantContent.querySelector('.typing-dots')) {
                assistantContent.innerHTML = `<span class="font-bold">Assistant:</span> <span class="text-red-600">Connection error. Please try again.</span>`;
            }

            eventSource.close();
            enableInput();
        };
    }

    function enableInput() {
        userInput.disabled = false;
        sendButton.disabled = false;
        sendButton.classList.remove('opacity-50');
        userInput.focus();
    }

    // Event listeners
    sendButton.addEventListener('click', sendQuery);
    userInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            sendQuery();
        }
    });
});
