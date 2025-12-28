/**
 * ComplianceGPT - Frontend Application v2
 * Interactive chat with enhanced features
 */

// DOM Elements
const chatMessages = document.getElementById('chatMessages');
const questionInput = document.getElementById('questionInput');
const sendBtn = document.getElementById('sendBtn');
const statusDot = document.querySelector('.status-dot');
const statusText = document.querySelector('.status-text');
const chunkCount = document.getElementById('chunkCount');
const llmProvider = document.getElementById('llmProvider');

// State
let isLoading = false;
let selectedRegulation = 'All';

// API Base
const API_BASE = '';

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
    setupEventListeners();
    questionInput.focus();
});

async function initializeApp() {
    questionInput.disabled = false;
    await checkHealth();
}

function setupEventListeners() {
    // Input handling
    questionInput.addEventListener('input', handleInputChange);
    questionInput.addEventListener('keydown', handleKeyDown);
    sendBtn.addEventListener('click', handleSend);

    // Example questions
    document.querySelectorAll('.example-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const question = btn.dataset.question;
            questionInput.value = question;
            handleInputChange();
            handleSend();
        });
    });

    // Regulation pills
    document.querySelectorAll('.reg-pill').forEach(pill => {
        pill.addEventListener('click', () => {
            document.querySelectorAll('.reg-pill').forEach(p => p.classList.remove('active'));
            pill.classList.add('active');
            selectedRegulation = pill.dataset.reg;
        });
    });

    // Suggestion chips
    document.querySelectorAll('.suggestion-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            const text = chip.dataset.text;
            questionInput.value = text + ' ';
            questionInput.focus();
            handleInputChange();
        });
    });

    // Auto-resize textarea
    questionInput.addEventListener('input', () => {
        questionInput.style.height = 'auto';
        questionInput.style.height = Math.min(questionInput.scrollHeight, 120) + 'px';
    });

    // Click on textarea to focus
    document.querySelector('.input-wrapper').addEventListener('click', () => {
        questionInput.focus();
    });
}

function handleInputChange() {
    sendBtn.disabled = !questionInput.value.trim() || isLoading;
}

function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (!sendBtn.disabled) {
            handleSend();
        }
    }
}

async function handleSend() {
    const question = questionInput.value.trim();
    if (!question || isLoading) return;

    // Clear input
    questionInput.value = '';
    questionInput.style.height = 'auto';
    handleInputChange();

    // Add user message
    addMessage('user', question);

    // Show loading
    const loadingId = showLoading();

    try {
        isLoading = true;
        sendBtn.disabled = true;

        const response = await fetch(`${API_BASE}/api/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question,
                regulation: selectedRegulation
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        removeLoading(loadingId);
        addMessage('assistant', data.answer, data.citations);

    } catch (error) {
        removeLoading(loadingId);
        addMessage('assistant', `❌ **Connection Error**\n\nCouldn't reach the API server.\n\n**To fix:**\n1. Make sure the server is running:\n   \`uvicorn api.main:app --port 8000\`\n2. Refresh this page\n\nError: ${error.message}`);
    } finally {
        isLoading = false;
        handleInputChange();
    }
}

function addMessage(role, content, citations = []) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${role}`;

    const avatar = role === 'user' ? '👤' : '⚖️';

    let citationsHTML = '';
    if (citations && citations.length > 0) {
        citationsHTML = `
            <div class="citations-container">
                <button class="citations-toggle" onclick="toggleCitations(this)">
                    📚 View ${citations.length} Sources
                    <span style="margin-left: 0.5rem;">▼</span>
                </button>
                <div class="citations-list">
                    ${citations.map(c => `
                        <div class="citation-card">
                            <div class="citation-header">
                                <span class="citation-number">${c.citation_id}</span>
                                <span class="citation-regulation">${c.regulation}</span>
                                <span class="citation-source">${c.source_file} • Page ${c.page_numbers.join(', ')}</span>
                            </div>
                            <div class="citation-text">"${escapeHtml(c.text.substring(0, 200))}..."</div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    messageDiv.innerHTML = `
        <div class="message-avatar">
            <span>${avatar}</span>
        </div>
        <div class="message-content">
            <div class="message-bubble glass-card">
                ${formatContent(content)}
            </div>
            ${citationsHTML}
        </div>
    `;

    chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatContent(content) {
    return content
        // Bold
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        // Italic
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        // Code blocks
        .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
        // Inline code
        .replace(/`([^`]+)`/g, '<code style="background: rgba(59,130,246,0.1); padding: 0.1rem 0.3rem; border-radius: 4px;">$1</code>')
        // Headers
        .replace(/^### (.*)$/gm, '<h4 style="margin: 1rem 0 0.5rem; color: var(--accent-blue);">$1</h4>')
        .replace(/^## (.*)$/gm, '<h3 style="margin: 1rem 0 0.5rem; color: var(--accent-blue);">$1</h3>')
        // Links
        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" style="color: var(--accent-blue);">$1 ↗</a>')
        // Lists
        .replace(/^- (.*)$/gm, '<li style="margin-left: 1rem;">$1</li>')
        // Horizontal rule
        .replace(/---/g, '<hr style="border: none; border-top: 1px solid var(--border-color); margin: 1rem 0;">')
        // Line breaks
        .replace(/\n/g, '<br>')
        // Emoji sections
        .replace(/📚 \*\*(.*?)\*\*/g, '<div style="margin-top: 1rem;"><span style="margin-right: 0.5rem;">📚</span><strong style="color: var(--accent-green);">$1</strong></div>')
        .replace(/🔧 \*\*(.*?)\*\*/g, '<div style="margin-top: 1rem;"><span style="margin-right: 0.5rem;">🔧</span><strong style="color: var(--accent-orange);">$1</strong></div>')
        .replace(/👤 \*\*(.*?)\*\*/g, '<div style="margin-top: 1rem;"><span style="margin-right: 0.5rem;">👤</span><strong style="color: var(--accent-purple);">$1</strong></div>')
        .replace(/🌐 \*\*(.*?)\*\*/g, '<div style="margin-top: 1rem;"><span style="margin-right: 0.5rem;">🌐</span><strong style="color: var(--accent-cyan);">$1</strong></div>');
}

function showLoading() {
    const id = 'loading-' + Date.now();
    const loadingDiv = document.createElement('div');
    loadingDiv.id = id;
    loadingDiv.className = 'message message-assistant';
    loadingDiv.innerHTML = `
        <div class="message-avatar">
            <span>⚖️</span>
        </div>
        <div class="message-content">
            <div class="message-bubble glass-card">
                <div class="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
                <p style="color: var(--text-muted); font-size: 0.85rem; margin-top: 0.5rem;">
                    Searching ${selectedRegulation === 'All' ? 'all regulations' : selectedRegulation}...
                </p>
            </div>
        </div>
    `;
    chatMessages.appendChild(loadingDiv);
    scrollToBottom();
    return id;
}

function removeLoading(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function scrollToBottom() {
    requestAnimationFrame(() => {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    });
}

function toggleCitations(btn) {
    const list = btn.nextElementSibling;
    list.classList.toggle('expanded');
    const arrow = btn.querySelector('span:last-child');
    arrow.textContent = list.classList.contains('expanded') ? '▲' : '▼';
}

async function checkHealth() {
    try {
        const response = await fetch(`${API_BASE}/api/health`);
        const data = await response.json();

        if (data.status === 'healthy') {
            statusDot.classList.add('connected');
            statusText.textContent = 'Connected';
        } else {
            statusDot.classList.add('error');
            statusText.textContent = 'Degraded';
        }

        chunkCount.textContent = data.indexed_chunks.toLocaleString();
        llmProvider.textContent = data.llm_provider?.toUpperCase() || 'GROQ';

    } catch (error) {
        statusDot.classList.add('error');
        statusText.textContent = 'Offline';
        chunkCount.textContent = '--';
        llmProvider.textContent = '--';
    }
}

// Global functions
window.toggleCitations = toggleCitations;
