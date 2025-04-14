document.addEventListener('DOMContentLoaded', () => {
    const chatContainer = document.getElementById('chat-container');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    const typingIndicator = document.getElementById('typing-indicator');

    const addMessage = (content, isUser) => {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user-message' : 'assistant-message'}`;
        messageDiv.textContent = content;
        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    };

    const handleSubmit = async () => {
        const message = userInput.value.trim();
        if (!message) return;

        // Add user message
        addMessage(message, true);
        userInput.value = '';
        typingIndicator.classList.remove('hidden');

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message })
            });

            const data = await response.json();
            typingIndicator.classList.add('hidden');

            if (data.answer) {
                addMessage(data.answer, false);
                if (data.sources && data.sources.length > 0) {
                    const sourceDiv = document.createElement('div');
                    sourceDiv.className = 'source-citation';
                    sourceDiv.textContent = `Sources: ${data.sources.join(', ')}`;
                    chatContainer.lastElementChild.appendChild(sourceDiv);
                }
            }
        } catch (error) {
            typingIndicator.classList.add('hidden');
            addMessage('Error: Unable to get response', false);
            console.error('Error:', error);
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
