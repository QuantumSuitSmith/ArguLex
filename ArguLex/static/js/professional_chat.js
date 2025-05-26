document.addEventListener('DOMContentLoaded', function() {
    // Document chat elements
    const documentChatForm = document.getElementById('documentChatForm');
    const documentUserInput = document.getElementById('documentUserInput');
    const documentChatMessages = document.getElementById('documentChatMessages');
    
    // General chat elements
    const generalChatForm = document.getElementById('generalChatForm');
    const generalUserInput = document.getElementById('generalUserInput');
    const generalChatMessages = document.getElementById('generalChatMessages');
    
    // Common elements
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
        formData.append('chatbot_type', 'professional');

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || `HTTP error! status: ${response.status}`);
            }

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

            // Add success message to document chat
            addMessage(documentChatMessages, `
                <p>✅ Document uploaded and analyzed successfully!</p>
                <p>You can now ask questions about the document.</p>
            `, 'bot');

        } catch (error) {
            console.error('Upload error:', error);
            documentContent.innerHTML = `
                <div class="error">
                    <i class="fas fa-exclamation-circle"></i>
                    <p>Error uploading document: ${error.message}</p>
                </div>
            `;
        }
    });

    // Handle document chat form submission
    documentChatForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const message = documentUserInput.value.trim();
        if (!message) return;

        if (!currentDocumentId) {
            addMessage(documentChatMessages, `
                <p>❌ Please upload a document first before asking questions about it.</p>
            `, 'bot');
            return;
        }

        // Add user message
        addMessage(documentChatMessages, message, 'user');
        documentUserInput.value = '';

        // Show typing indicator
        const typingIndicator = addMessage(documentChatMessages, 'Typing...', 'bot');

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message,
                    chatbot_type: 'professional',
                    document_id: currentDocumentId
                })
            });

            const data = await response.json();

            // Remove typing indicator
            typingIndicator.remove();

            if (data.error) {
                addMessage(documentChatMessages, `❌ Error: ${data.error}`, 'bot');
            } else {
                addMessage(documentChatMessages, data.response, 'bot');
            }
        } catch (error) {
            typingIndicator.remove();
            addMessage(documentChatMessages, '❌ Error: Could not get response. Please try again.', 'bot');
            console.error('Chat error:', error);
        }
    });

    // Handle general chat form submission
    generalChatForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const message = generalUserInput.value.trim();
        if (!message) return;

        // Add user message
        addMessage(generalChatMessages, message, 'user');
        generalUserInput.value = '';

        // Show typing indicator
        const typingIndicator = addMessage(generalChatMessages, 'Typing...', 'bot');

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message,
                    chatbot_type: 'professional'
                })
            });

            const data = await response.json();

            // Remove typing indicator
            typingIndicator.remove();

            if (data.error) {
                addMessage(generalChatMessages, `❌ Error: ${data.error}`, 'bot');
            } else {
                addMessage(generalChatMessages, data.response, 'bot');
            }
        } catch (error) {
            typingIndicator.remove();
            addMessage(generalChatMessages, '❌ Error: Could not get response. Please try again.', 'bot');
            console.error('Chat error:', error);
        }
    });

    // Handle Enter key for both chat forms
    [documentUserInput, generalUserInput].forEach(input => {
        input.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                const form = this.closest('form');
                form.dispatchEvent(new Event('submit'));
            }
        });
    });

    // Handle dark mode toggle
    modeToggle.addEventListener('click', function() {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        document.documentElement.setAttribute('data-theme', isDark ? 'light' : 'dark');
        localStorage.setItem('theme', isDark ? 'light' : 'dark');
    });

    // Helper function to add messages
    function addMessage(container, text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        messageDiv.innerHTML = `
            <div class="message-content">
                ${text}
            </div>
        `;
        container.appendChild(messageDiv);
        container.scrollTop = container.scrollHeight;
        return messageDiv;
    }

    // Load saved theme
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
}); 