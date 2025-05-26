document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('chatForm');
    const userInput = document.getElementById('userInput');
    const chatMessages = document.getElementById('chatMessages');
    const fileUpload = document.getElementById('file-upload');
    const modeToggle = document.getElementById('modeToggle');
    const chatbotType = document.querySelector('.chat-header h1').textContent.toLowerCase().includes('professional') ? 'professional' : 'general';
    let selectedDocumentId = null;

    // Add initial bot message based on chatbot type
    if (chatbotType === 'professional') {
        addMessage('Welcome to ArguLex Professional Assistant. You can ask legal questions or upload legal documents for analysis.', 'bot');
    } else {
        addMessage('Welcome to ArguLex General Assistant. How can I help you with your legal questions today?', 'bot');
    }

    // Dark mode handling
    const savedMode = localStorage.getItem('darkMode') === 'true';
    if (savedMode) {
        document.body.classList.add('dark-mode');
        modeToggle.querySelector('i').classList.replace('fa-moon', 'fa-sun');
    }

    modeToggle.addEventListener('click', function() {
        document.body.classList.toggle('dark-mode');
        const icon = modeToggle.querySelector('i');
        if (document.body.classList.contains('dark-mode')) {
            icon.classList.replace('fa-moon', 'fa-sun');
            localStorage.setItem('darkMode', 'true');
        } else {
            icon.classList.replace('fa-sun', 'fa-moon');
            localStorage.setItem('darkMode', 'false');
        }
    });

    // Handle document selection
    const documentItems = document.querySelectorAll('.document-item');
    documentItems.forEach(item => {
        item.addEventListener('click', () => {
            // Remove selection from other items
            documentItems.forEach(i => i.classList.remove('selected'));
            // Add selection to clicked item
            item.classList.add('selected');
            selectedDocumentId = item.dataset.documentId;
            
            // Add a message indicating which document is selected
            addMessage(`Selected document: ${item.querySelector('.document-name').textContent}`, 'bot');
        });
    });

    // Auto-resize textarea
    userInput.addEventListener('input', () => {
        userInput.style.height = 'auto';
        userInput.style.height = userInput.scrollHeight + 'px';
    });

    // Handle file upload (only in professional mode)
    if (fileUpload) {
        fileUpload.addEventListener('change', async function(e) {
            const file = e.target.files[0];
            if (!file) return;

            if (!file.name.toLowerCase().endsWith('.pdf')) {
                addMessage('❌ Error: Only PDF files are supported.', 'bot');
                return;
            }

            const formData = new FormData();
            formData.append('file', file);

            // Show uploading message
            addMessage('📤 Uploading document...', 'bot');

            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (data.error) {
                    addMessage(`❌ Error: ${data.error}`, 'bot');
                } else {
                    addMessage('✅ Document uploaded successfully!', 'bot');
                    if (data.report) {
                        addMessage(data.report, 'bot');
                    }
                }
            } catch (error) {
                addMessage('❌ Error uploading document. Please try again.', 'bot');
                console.error('Upload error:', error);
            }

            // Reset file input
            fileUpload.value = '';
        });
    }

    // Handle chat form submission
    chatForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const message = userInput.value.trim();
        if (!message) return;

        // Add user message
        addMessage(message, 'user');
        userInput.value = '';

        // Show typing indicator
        const typingIndicator = addMessage('Typing...', 'bot');

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    message,
                    chatbot_type: chatbotType
                })
            });

            const data = await response.json();

            // Remove typing indicator
            typingIndicator.remove();

            if (data.error) {
                addMessage(`❌ Error: ${data.error}`, 'bot');
            } else {
                addMessage(data.response, 'bot');
            }
        } catch (error) {
            typingIndicator.remove();
            addMessage('❌ Error: Could not get response. Please try again.', 'bot');
            console.error('Chat error:', error);
        }
    });

    // Helper function to add messages
    function addMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        messageDiv.innerHTML = `
            <div class="message-content">
                ${text}
            </div>
        `;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return messageDiv;
    }

    // Handle Enter key
    userInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            chatForm.dispatchEvent(new Event('submit'));
        }
    });
}); 