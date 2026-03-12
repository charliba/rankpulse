/**
 * Aura Chat Support Widget — RankPulse
 * Assistente IA com chat flutuante (bottom-right).
 *
 * Padrão: IIFE que cria o DOM inteiro via JS,
 * identico ao modelo Gia/Beezle adaptado para indigo/cyan.
 */

(function () {
    'use strict';

    /* ── capture JS errors for feedback context ─────────── */
    window.__rkp_errors = window.__rkp_errors || [];
    window.addEventListener('error', function (e) {
        window.__rkp_errors.push({
            msg: e.message, file: e.filename, line: e.lineno, col: e.colno, ts: Date.now()
        });
        if (window.__rkp_errors.length > 20) window.__rkp_errors.shift();
    });

    /* ── config ─────────────────────────────────────────── */
    const CONFIG = {
        apiBase: '/chat/',
        csrfToken: '',           // preenchido em init()
    };

    let state = {
        isOpen: false,
        isLoading: false,
        messages: [],
        sessionId: null,       // tracks current chat session UUID
    };

    let el = {};  // referências DOM

    /* ── init ───────────────────────────────────────────── */
    function init() {
        // Pegar CSRF do body attribute (HTMX pattern)
        const body = document.body;
        try {
            const hxHeaders = body.getAttribute('hx-headers');
            if (hxHeaders) {
                const parsed = JSON.parse(hxHeaders);
                CONFIG.csrfToken = parsed['X-CSRFToken'] || '';
            }
        } catch (_) { /* ignore */ }

        // Tentar meta tag também
        if (!CONFIG.csrfToken) {
            const metaCsrf = document.querySelector('meta[name="csrf-token"]');
            if (metaCsrf) CONFIG.csrfToken = metaCsrf.content;
        }

        // Fallback: cookie
        if (!CONFIG.csrfToken) {
            const match = document.cookie.match(/csrftoken=([^;]+)/);
            if (match) CONFIG.csrfToken = match[1];
        }

        createWidget();
        bindEvents();
        loadMessages();
    }

    /* ── criar widget DOM ───────────────────────────────── */
    function createWidget() {
        const container = document.createElement('div');
        container.id = 'aura-chat-widget';
        container.innerHTML = `
            <!-- FAB Button -->
            <button class="aura-chat-button" id="auraToggleBtn" aria-label="Abrir chat Aura">
                <span class="aura-pulse"></span>
                <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 2C6.48 2 2 6.48 2 12c0 1.74.5 3.37 1.36 4.75L2 22l5.25-1.36C8.63 21.5 10.26 22 12 22c5.52 0 10-4.48 10-10S17.52 2 12 2zm-1 15h-2v-2h2v2zm2.07-7.75l-.9.92C11.45 10.9 11 11.5 11 13h-2v-.5c0-1.1.45-2.1 1.17-2.83l1.24-1.26c.37-.36.59-.86.59-1.41 0-1.1-.9-2-2-2s-2 .9-2 2H6c0-2.21 1.79-4 4-4s4 1.79 4 4c0 .88-.36 1.68-.93 2.25z"/>
                </svg>
            </button>

            <!-- Chat Window -->
            <div class="aura-chat-window" id="auraChatWindow">
                <!-- Header -->
                <div class="aura-chat-header">
                    <div class="aura-chat-header-info">
                        <div class="aura-chat-header-avatar">
                            <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 15h-2v-2h2v2zm2.07-7.75l-.9.92C11.45 10.9 11 11.5 11 13h-2v-.5c0-1.1.45-2.1 1.17-2.83l1.24-1.26c.37-.36.59-.86.59-1.41 0-1.1-.9-2-2-2s-2 .9-2 2H6c0-2.21 1.79-4 4-4s4 1.79 4 4c0 .88-.36 1.68-.93 2.25z"/>
                            </svg>
                        </div>
                        <div class="aura-chat-header-text">
                            <h4>Aura — RankPulse</h4>
                            <p id="auraStatus">Online — Resposta instantânea</p>
                        </div>
                    </div>
                    <button class="aura-chat-close" id="auraCloseBtn" aria-label="Fechar chat">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                        </svg>
                    </button>
                </div>

                <!-- Messages -->
                <div class="aura-chat-messages" id="auraMessages"></div>

                <!-- Quick Actions -->
                <div class="aura-quick-actions" id="auraQuickActions">
                    <button class="aura-quick-action" data-msg="Como configurar o GA4?">Configurar GA4</button>
                    <button class="aura-quick-action" data-msg="Como verificar o Search Console?">Search Console</button>
                    <button class="aura-quick-action" data-msg="Qual a diferença de evento server-side vs client-side?">Eventos GA4</button>
                    <button class="aura-quick-action" data-msg="Como definir boas metas KPI?">Metas KPI</button>
                </div>

                <!-- Input -->
                <div class="aura-chat-input-area">
                    <input type="text"
                           class="aura-chat-input"
                           id="auraInput"
                           placeholder="Pergunte à Aura..."
                           autocomplete="off">
                    <button class="aura-chat-send" id="auraSendBtn" aria-label="Enviar">
                        <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                        </svg>
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(container);

        el = {
            toggleBtn: document.getElementById('auraToggleBtn'),
            window: document.getElementById('auraChatWindow'),
            closeBtn: document.getElementById('auraCloseBtn'),
            messages: document.getElementById('auraMessages'),
            input: document.getElementById('auraInput'),
            sendBtn: document.getElementById('auraSendBtn'),
            quickActions: document.getElementById('auraQuickActions'),
            status: document.getElementById('auraStatus'),
        };
    }

    /* ── events ─────────────────────────────────────────── */
    function bindEvents() {
        el.toggleBtn.addEventListener('click', toggleChat);
        el.closeBtn.addEventListener('click', toggleChat);

        el.sendBtn.addEventListener('click', sendMessage);
        el.input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        el.quickActions.querySelectorAll('.aura-quick-action').forEach((btn) => {
            btn.addEventListener('click', function () {
                el.input.value = this.getAttribute('data-msg');
                sendMessage();
            });
        });

    }

    /* ── toggle ─────────────────────────────────────────── */
    function toggleChat() {
        state.isOpen = !state.isOpen;
        el.window.classList.toggle('open', state.isOpen);
        if (state.isOpen) {
            el.input.focus();
            scrollToBottom();
            // Esconder pulse após primeiro uso
            const pulse = el.toggleBtn.querySelector('.aura-pulse');
            if (pulse) pulse.style.display = 'none';
        }
    }

    /* ── load messages ──────────────────────────────────── */
    async function loadMessages() {
        try {
            const res = await fetch(CONFIG.apiBase + 'messages/', {
                credentials: 'same-origin',
            });
            if (res.ok) {
                const data = await res.json();
                if (data.success && data.messages) {
                    state.messages = data.messages;
                    renderAll();
                }
            }
        } catch (err) {
            console.error('[Aura] Erro ao carregar mensagens:', err);
        }
    }

    /* ── send ───────────────────────────────────────────── */
    async function sendMessage() {
        const msg = el.input.value.trim();
        if (!msg || state.isLoading) return;

        state.isLoading = true;
        el.sendBtn.disabled = true;
        el.input.value = '';

        addMessage('user', msg);
        showTyping();

        try {
            const headers = { 'Content-Type': 'application/json' };
            if (CONFIG.csrfToken) headers['X-CSRFToken'] = CONFIG.csrfToken;

            const res = await fetch(CONFIG.apiBase + 'send/', {
                method: 'POST',
                headers,
                credentials: 'same-origin',
                body: JSON.stringify({ message: msg }),
            });

            hideTyping();

            if (res.ok) {
                const data = await res.json();
                if (data.success) {
                    addMessage('ai', data.response);
                    if (data.session_id) state.sessionId = data.session_id;
                }
            } else {
                addMessage('system', 'Erro ao obter resposta. Tente novamente.');
            }
        } catch (err) {
            hideTyping();
            addMessage('system', 'Erro de conexão. Tente novamente.');
            console.error('[Aura] Erro:', err);
        }

        state.isLoading = false;
        el.sendBtn.disabled = false;
        el.input.focus();
    }

    /* ── render helpers ─────────────────────────────────── */
    function addMessage(sender, content) {
        const msg = { sender, content, created_at: new Date().toISOString() };
        state.messages.push(msg);
        renderMessage(msg);
        scrollToBottom();
    }

    function renderAll() {
        el.messages.innerHTML = '';
        state.messages.forEach((m) => renderMessage(m));
        scrollToBottom();
    }

    function renderMessage(msg) {
        const div = document.createElement('div');
        div.className = `aura-chat-message ${msg.sender}`;

        const time = new Date(msg.created_at).toLocaleTimeString('pt-BR', {
            hour: '2-digit', minute: '2-digit',
        });

        // Markdown básico → HTML
        let html = msg.content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/^### (.*$)/gm, '<strong style="font-size:14px">$1</strong>')
            .replace(/^## (.*$)/gm, '<strong style="font-size:15px">$1</strong>')
            .replace(/^- /gm, '• ')
            .replace(/^\d+\.\s/gm, (m) => m)
            .replace(/\n/g, '<br>');

        div.innerHTML = `
            <div class="aura-chat-bubble">${html}</div>
            <span class="aura-chat-time">${time}</span>
        `;

        el.messages.appendChild(div);
    }

    function showTyping() {
        const t = document.createElement('div');
        t.id = 'auraTypingIndicator';
        t.className = 'aura-chat-message ai';
        t.innerHTML = `
            <div class="aura-typing">
                <span class="aura-typing-dot"></span>
                <span class="aura-typing-dot"></span>
                <span class="aura-typing-dot"></span>
            </div>
        `;
        el.messages.appendChild(t);
        scrollToBottom();
    }

    function hideTyping() {
        const t = document.getElementById('auraTypingIndicator');
        if (t) t.remove();
    }

    function scrollToBottom() {
        requestAnimationFrame(() => {
            el.messages.scrollTop = el.messages.scrollHeight;
        });
    }

    /* ── boot ───────────────────────────────────────────── */
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
