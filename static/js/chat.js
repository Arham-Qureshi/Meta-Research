/* ============================================================
   Chat With Paper – Client-Side Logic
   Handles message sending, AI responses, and paper summarization.
   ============================================================ */

// This function is called by paper_chat.html after __PAPER_DATA__ is set
function initChatLogic() {
    // --- DOM Elements ---
    const chatMessages = document.getElementById('chatMessages');
    const chatInput = document.getElementById('chatInput');
    const chatSendBtn = document.getElementById('chatSendBtn');
    const summarizeBtn = document.getElementById('summarizeBtn');

    if (!chatMessages || !chatInput || !chatSendBtn) return;

    // --- Paper data is embedded in a <script> tag by the template ---
    const paperData = window.__PAPER_DATA__ || null;

    if (!paperData) {
        chatMessages.innerHTML = '<div class="chat-error">Paper data could not be loaded. Please go back and try again.</div>';
        return;
    }

    // --- Helper: simple Markdown to HTML ---
    function mdToHtml(text) {
        if (!text) return '';
        let html = text
            // Escape HTML entities
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            // Headers
            .replace(/^### (.+)$/gm, '<h3>$1</h3>')
            .replace(/^## (.+)$/gm, '<h2>$1</h2>')
            // Bold
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            // Italic
            .replace(/\*(.+?)\*/g, '<em>$1</em>')
            // Inline code
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            // Unordered list items
            .replace(/^[\-\*] (.+)$/gm, '<li>$1</li>')
            // Ordered list items
            .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
            // Wrap consecutive <li> in <ul>
            .replace(/((?:<li>.*<\/li>\n?)+)/g, '<ul>$1</ul>')
            // Paragraphs (double newlines)
            .replace(/\n\n/g, '</p><p>')
            // Single newlines inside paragraphs
            .replace(/\n/g, '<br>');

        // Wrap in <p> if needed
        if (!html.startsWith('<h') && !html.startsWith('<ul') && !html.startsWith('<p')) {
            html = '<p>' + html + '</p>';
        }

        return html;
    }

    // --- Helper: create a message bubble ---
    function addMessage(role, content, isHtml) {
        // Remove welcome message if present
        const welcome = chatMessages.querySelector('.chat-welcome');
        if (welcome) welcome.remove();

        const msg = document.createElement('div');
        msg.className = `chat-msg ${role}`;

        const avatarText = role === 'user' ? '👤' : '🤖';
        const bubble = isHtml ? content : escapeHtml(content);

        msg.innerHTML = `
            <div class="chat-msg-avatar">${avatarText}</div>
            <div class="chat-msg-bubble">${bubble}</div>
        `;

        chatMessages.appendChild(msg);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return msg;
    }

    // --- Helper: show typing indicator ---
    function showTyping() {
        const typing = document.createElement('div');
        typing.className = 'chat-typing';
        typing.id = 'chatTypingIndicator';
        typing.innerHTML = `
            <div class="chat-typing-avatar">🤖</div>
            <div class="chat-typing-dots">
                <span></span><span></span><span></span>
            </div>
        `;
        chatMessages.appendChild(typing);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function hideTyping() {
        const typing = document.getElementById('chatTypingIndicator');
        if (typing) typing.remove();
    }

    // --- Helper: show inline error ---
    function showError(message) {
        const err = document.createElement('div');
        err.className = 'chat-error';
        err.textContent = message;
        chatMessages.appendChild(err);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // --- Send Message ---
    async function sendMessage(messageText) {
        const text = (messageText || chatInput.value).trim();
        if (!text) return;

        // Show user message
        addMessage('user', text, false);
        chatInput.value = '';
        chatInput.style.height = 'auto';
        chatSendBtn.disabled = true;

        // Show typing
        showTyping();

        try {
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    paper: paperData,
                    message: text
                })
            });

            hideTyping();

            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                showError(errData.error || 'Failed to get a response. Please try again.');
                return;
            }

            const data = await res.json();
            addMessage('ai', mdToHtml(data.reply), true);

        } catch (err) {
            hideTyping();
            showError('Network error. Please check your connection.');
            console.error('Chat error:', err);
        } finally {
            chatSendBtn.disabled = false;
            chatInput.focus();
        }
    }

    // --- Summarize Paper ---
    async function summarizePaper() {
        if (summarizeBtn) summarizeBtn.disabled = true;

        // Remove welcome if present
        const welcome = chatMessages.querySelector('.chat-welcome');
        if (welcome) welcome.remove();

        addMessage('user', '📝 Generate a comprehensive summary of this paper', false);
        showTyping();

        try {
            const res = await fetch('/api/chat/summarize', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ paper: paperData })
            });

            hideTyping();

            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                showError(errData.error || 'Failed to generate summary.');
                return;
            }

            const data = await res.json();
            addMessage('ai', mdToHtml(data.summary), true);

        } catch (err) {
            hideTyping();
            showError('Network error. Please check your connection.');
            console.error('Summarize error:', err);
        } finally {
            if (summarizeBtn) summarizeBtn.disabled = false;
        }
    }

    // --- Event Listeners ---

    // Send button
    chatSendBtn.addEventListener('click', () => sendMessage());

    // Enter key (Shift+Enter for newline)
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Auto-resize textarea
    chatInput.addEventListener('input', () => {
        chatInput.style.height = 'auto';
        chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
    });

    // Summarize button
    if (summarizeBtn) {
        summarizeBtn.addEventListener('click', summarizePaper);
    }

    // Suggestion chips
    document.querySelectorAll('.chat-suggestion-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            sendMessage(chip.textContent.trim());
        });
    });

    // --- Escape helper ---
    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

}

// Register so paper_chat.html can trigger init after data loads
window.__initChatAfterLoad = initChatLogic;
// Also try to init immediately (if data already set)
if (window.__PAPER_DATA__) initChatLogic();
