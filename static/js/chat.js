
function initChatLogic() {
    const chatMessages = document.getElementById('chatMessages');
    const chatInput = document.getElementById('chatInput');
    const chatSendBtn = document.getElementById('chatSendBtn');
    const summarizeBtn = document.getElementById('summarizeBtn');
    if (!chatMessages || !chatInput || !chatSendBtn) return;
    const paperData = window.__PAPER_DATA__ || null;
    if (!paperData) {
        chatMessages.innerHTML = '<div class="chat-error">Paper data could not be loaded. Please go back and try again.</div>';
        return;
    }
    function mdToHtml(text) {
        if (!text) return '';
        let html = text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/^### (.+)$/gm, '<h3>$1</h3>')
            .replace(/^## (.+)$/gm, '<h2>$1</h2>')
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.+?)\*/g, '<em>$1</em>')
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/^[\-\*] (.+)$/gm, '<li>$1</li>')
            .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
            .replace(/((?:<li>.*<\/li>\n?)+)/g, '<ul>$1</ul>')
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>');
        if (!html.startsWith('<h') && !html.startsWith('<ul') && !html.startsWith('<p')) {
            html = '<p>' + html + '</p>';
        }
        return html;
    }
    function addMessage(role, content, isHtml) {
        const welcome = chatMessages.querySelector('.chat-welcome');
        if (welcome) welcome.remove();
        const msg = document.createElement('div');
        msg.className = `chat-msg ${role}`;
        const avatarText = role === 'user'
            ? '<i data-lucide="user" style="width: 20px; height: 20px;"></i>'
            : '<i data-lucide="bot" style="width: 20px; height: 20px;"></i>';
        const bubble = isHtml ? content : escapeHtml(content);
        msg.innerHTML = `
            <div class="chat-msg-avatar">${avatarText}</div>
            <div class="chat-msg-bubble">${bubble}</div>
        `;
        chatMessages.appendChild(msg);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        if (window.lucide) window.lucide.createIcons();
        return msg;
    }
    function showTyping() {
        const typing = document.createElement('div');
        typing.className = 'chat-typing';
        typing.id = 'chatTypingIndicator';
        typing.innerHTML = `
            <div class="chat-typing-avatar"><i data-lucide="bot" style="width: 20px; height: 20px;"></i></div>
            <div class="chat-typing-dots">
                <span></span><span></span><span></span>
            </div>
        `;
        chatMessages.appendChild(typing);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        if (window.lucide) window.lucide.createIcons();
    }
    function hideTyping() {
        const typing = document.getElementById('chatTypingIndicator');
        if (typing) typing.remove();
    }
    function showError(message) {
        const err = document.createElement('div');
        err.className = 'chat-error';
        err.textContent = message;
        chatMessages.appendChild(err);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    async function sendMessage(messageText) {
        const text = (messageText || chatInput.value).trim();
        if (!text) return;
        addMessage('user', text, false);
        chatInput.value = '';
        chatInput.style.height = 'auto';
        chatSendBtn.disabled = true;
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
            const replyText = (data.data && data.data.reply) || data.reply;
            addMessage('ai', mdToHtml(replyText), true);
        } catch (err) {
            hideTyping();
            showError('Network error. Please check your connection.');
            console.error('Chat error:', err);
        } finally {
            chatSendBtn.disabled = false;
            chatInput.focus();
        }
    }
    async function summarizePaper() {
        if (summarizeBtn) summarizeBtn.disabled = true;
        const welcome = chatMessages.querySelector('.chat-welcome');
        if (welcome) welcome.remove();
        addMessage('user', 'Generate a comprehensive summary of this paper', false);
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
            const summaryText = (data.data && data.data.summary) || data.summary;
            addMessage('ai', mdToHtml(summaryText), true);
        } catch (err) {
            hideTyping();
            showError('Network error. Please check your connection.');
            console.error('Summarize error:', err);
        } finally {
            if (summarizeBtn) summarizeBtn.disabled = false;
        }
    }
    chatSendBtn.addEventListener('click', () => sendMessage());
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    chatInput.addEventListener('input', () => {
        chatInput.style.height = 'auto';
        chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
    });
    if (summarizeBtn) {
        summarizeBtn.addEventListener('click', summarizePaper);
    }
    document.querySelectorAll('.chat-suggestion-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            sendMessage(chip.textContent.trim());
        });
    });
    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}
window.__initChatAfterLoad = initChatLogic;
if (window.__PAPER_DATA__) initChatLogic();
