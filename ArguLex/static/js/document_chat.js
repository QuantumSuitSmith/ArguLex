document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('chatForm');
    const userInput = document.getElementById('userInput');
    const chatMessages = document.getElementById('chatMessages');
    const fileUpload = document.getElementById('file-upload');
    const documentContent = document.getElementById('documentContent');
    const modeToggle = document.getElementById('modeToggle');

    let currentDocumentId = null;
    let currentPdfText = null;

    // Handle file upload
    fileUpload.addEventListener('change', async function(e) {
        const file = e.target.files[0];
        if (!file) return;

        // Show loading state
        documentContent.innerHTML = `
            <div class="loading">
                <i class="fas fa-spinner fa-spin"></i>
                <p>Analyzing document...</p>
            </div>
        `;

        const formData = new FormData();
        formData.append('file', file);
        formData.append('chatbot_type', 'document');

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.error) {
                documentContent.innerHTML = `
                    <div class="error">
                        <i class="fas fa-exclamation-circle"></i>
                        <p>${data.error}</p>
                    </div>
                `;
                return;
            }

            // Store document information
            currentDocumentId = data.document_id;
            currentPdfText = data.pdf_text;

            // Display the report
            documentContent.innerHTML = data.report;

            // Add success message to chat
            addMessage(`
                <p>✅ Document uploaded and analyzed successfully!</p>
                <p>You can now ask questions about the document.</p>
            `, 'bot');

        } catch (error) {
            console.error('Upload error:', error);
            documentContent.innerHTML = `
                <div class="error">
                    <i class="fas fa-exclamation-circle"></i>
                    <p>Error uploading document. Please try again.</p>
                </div>
            `;
        }
    });

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
                    chatbot_type: 'document',
                    document_id: currentDocumentId
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

    // Handle Enter key (Shift+Enter for new line)
    userInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            chatForm.dispatchEvent(new Event('submit'));
        }
    });

    // Handle dark mode toggle
    modeToggle.addEventListener('click', function() {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        document.documentElement.setAttribute('data-theme', isDark ? 'light' : 'dark');
        localStorage.setItem('theme', isDark ? 'light' : 'dark');
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

    // Load saved theme
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
}); 