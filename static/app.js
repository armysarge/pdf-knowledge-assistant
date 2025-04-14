document.addEventListener('DOMContentLoaded', () => {
    const chatContainer = document.getElementById('chat-container');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    const typingIndicator = document.getElementById('typing-indicator');

    const addMessage = (content, isUser) => {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user-message' : 'assistant-message'}`;

        // Split content by newlines and create paragraphs
        const paragraphs = content.split('\n').filter(p => p.trim());
        paragraphs.forEach(p => {
            const para = document.createElement('p');
            para.textContent = p;
            messageDiv.appendChild(para);
        });

        // Only add typing indicator for assistant messages
        if (!isUser) {
            const typing = document.createElement('div');
            typing.className = 'typing-animation hidden';
            typing.innerHTML = `
                <div class="dot"></div>
                <div class="dot"></div>
                <div class="dot"></div>
            `;
            messageDiv.appendChild(typing);
        }

        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
        return messageDiv;
    };

    const setLoading = (isLoading) => {
        sendButton.disabled = isLoading;
        userInput.disabled = isLoading;

        // Toggle typing animation on the last assistant message
        const lastMessage = chatContainer.querySelector('.message.assistant-message:last-child');
        if (lastMessage)
            lastMessage.querySelector('.typing-animation')?.remove();
    };

    const handleSubmit = async () => {
        const message = userInput.value.trim();
        if (!message) return;

        // Add user message
        addMessage(message, true);
        userInput.value = '';

        // Disable input and show loading state
        setLoading(true);

        try {
            // Create response message container
            const responseDiv = addMessage('', false);
            let currentParagraph = document.createElement('p');
            responseDiv.appendChild(currentParagraph);
            let responseText = '';

            // Make POST request with streaming
            const response = await fetch('/api/chat-stream', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message })
            });

            const data = await response.json();

            // Check if response was not ok (error status code)
            if (!response.ok || data.error) {
                setLoading(false);
                throw new Error(data.error || data.detail || 'An error occurred while getting a response');
            }

            // Set up streaming response handler
            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            try {
                while (true) {
                    const {value, done} = await reader.read();
                    if (done) break;

                    const text = decoder.decode(value);
                    const lines = text.split('\n');

                    lines.forEach(line => {
                        if (line.startsWith('data: ')) {
                            const data = line.slice(6);
                            if (data === '[DONE]') {
                                setLoading(false);
                                return;
                            }

                            // Handle sources separately
                            if (data.startsWith('Sources:')) {
                                const sourceDiv = document.createElement('div');
                                sourceDiv.className = 'source-citation';
                                sourceDiv.textContent = data;
                                responseDiv.appendChild(sourceDiv);
                                return;
                            }

                            // Append word and add space
                            responseText += data + ' ';
                            currentParagraph.textContent = responseText;
                            chatContainer.scrollTop = chatContainer.scrollHeight;
                        }
                    });
                }
            } catch (error) {
                console.error('Stream reading error:', error);
                if (!responseText) {
                    currentParagraph.textContent = error.message || 'Error: Unable to get response';
                }
                setLoading(false);
            }
        } catch (error) {
            //update last message with error
            const lastMessage = chatContainer.querySelector('.message.assistant-message:last-child');
            if (lastMessage) {
                const errorParagraph = document.createElement('p');
                errorParagraph.textContent = error.message || 'Error: Unable to get response';
                lastMessage.appendChild(errorParagraph);
            }
            setLoading(false);
        }
    };

    sendButton.addEventListener('click', handleSubmit);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
        }
    });
});
