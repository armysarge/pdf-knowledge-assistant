document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const chatMessages = document.getElementById('chat-messages');

    function createMessage(content, isUser) {
        const div = document.createElement('div');
        div.className = `message ${isUser ? 'user-message' : 'assistant-message'}`;
        div.textContent = content;
        return div;
    }

    function createTypingIndicator() {
        const div = document.createElement('div');
        div.className = 'typing-indicator assistant-message';
        div.innerHTML = `
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        `;
        return div;
    }

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const question = userInput.value.trim();
        if (!question) return;

        // Add user message
        chatMessages.appendChild(createMessage(question, true));
        userInput.value = '';
        chatMessages.scrollTop = chatMessages.scrollHeight;

        // Add typing indicator
        const typingIndicator = createTypingIndicator();
        chatMessages.appendChild(typingIndicator);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        try {
            const response = await fetch('/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query: question })
            });

            const data = await response.json();

            // Remove typing indicator
            typingIndicator.remove();

            // Add assistant response
            chatMessages.appendChild(createMessage(data.answer, false));

            // Add sources if available
            if (data.sources && data.sources.length > 0) {
                const sourcesDiv = document.createElement('div');
                sourcesDiv.className = 'text-xs text-gray-500 mt-2 ml-4';
                sourcesDiv.innerHTML = '<strong>Sources:</strong><br>' +
                    data.sources.map(s => `- ${s}`).join('<br>');
                chatMessages.appendChild(sourcesDiv);
            }
        } catch (error) {
            typingIndicator.remove();
            chatMessages.appendChild(
                createMessage('Sorry, there was an error processing your request.', false)
            );
        }

        chatMessages.scrollTop = chatMessages.scrollHeight;
    });

    // Handle Ctrl+Enter to submit
    userInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && e.ctrlKey) {
            chatForm.dispatchEvent(new Event('submit'));
        }
    });
});
