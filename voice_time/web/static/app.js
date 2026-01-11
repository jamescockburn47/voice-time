/**
 * TimeBrief App JavaScript
 * Handles: Command bar, Chat interface, Timer widget, Keyboard shortcuts
 */

// ==================== State Management ====================

const AppState = {
    darkMode: false,
    currentConversation: null,
    isRecording: false,
    activeTimer: null,
    preferences: {},
    undoStack: [],

    init() {
        this.loadPreferences();
        this.setupEventListeners();
        this.loadConversationHistory();
        this.checkActiveTimer();
    },

    loadPreferences() {
        const saved = localStorage.getItem('timebrief_preferences');
        if (saved) {
            this.preferences = JSON.parse(saved);
            if (this.preferences.darkMode) {
                this.toggleDarkMode(true);
            }
        }
    },

    savePreferences() {
        localStorage.setItem('timebrief_preferences', JSON.stringify(this.preferences));
    },

    toggleDarkMode(force = null) {
        this.darkMode = force !== null ? force : !this.darkMode;
        this.preferences.darkMode = this.darkMode;
        document.documentElement.setAttribute('data-theme', this.darkMode ? 'dark' : 'light');
        this.savePreferences();
    },

    setupEventListeners() {
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => KeyboardShortcuts.handle(e));

        // Command bar focus
        const cmdBar = document.getElementById('command-bar');
        if (cmdBar) {
            cmdBar.addEventListener('keydown', (e) => CommandBar.handleKey(e));
        }
    },

    async loadConversationHistory() {
        try {
            const response = await fetch('/api/conversation/history');
            const data = await response.json();
            if (data.success && data.messages) {
                ChatInterface.renderHistory(data.messages);
            }
        } catch (e) {
            console.log('No conversation history');
        }
    },

    async checkActiveTimer() {
        try {
            const response = await fetch('/api/timer/status');
            const data = await response.json();
            if (data.active) {
                this.activeTimer = data;
                TimerWidget.show(data);
            }
        } catch (e) {
            console.log('No active timer');
        }
    }
};

// ==================== Command Bar ====================

const CommandBar = {
    element: null,
    suggestionsEl: null,
    isOpen: false,

    init() {
        this.element = document.getElementById('command-bar');
        this.suggestionsEl = document.getElementById('command-suggestions');
    },

    focus() {
        if (this.element) {
            this.element.focus();
            this.element.select();
        }
    },

    blur() {
        if (this.element) {
            this.element.blur();
        }
        this.hideSuggestions();
    },

    handleKey(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            this.execute();
        } else if (e.key === 'Escape') {
            this.blur();
        } else if (e.key === 'ArrowDown' && this.suggestionsEl) {
            e.preventDefault();
            this.selectNextSuggestion();
        } else if (e.key === 'ArrowUp' && this.suggestionsEl) {
            e.preventDefault();
            this.selectPrevSuggestion();
        }
    },

    async execute() {
        const input = this.element?.value?.trim();
        if (!input) return;

        // Add to chat as user message
        ChatInterface.addMessage('user', input);

        // Clear input
        this.element.value = '';
        this.hideSuggestions();

        // Process command
        try {
            const response = await fetch('/api/command', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command: input })
            });

            const result = await response.json();
            ChatInterface.addResponse(result);

            // Handle navigation
            if (result.navigate) {
                window.location.href = result.navigate;
            }

            // Update undo stack
            if (result.can_undo) {
                AppState.undoStack.push(result.action_id);
            }

            // Refresh if needed
            if (result.refresh) {
                setTimeout(() => location.reload(), 500);
            }

        } catch (error) {
            ChatInterface.addMessage('error', `Error: ${error.message}`);
        }
    },

    showSuggestions(suggestions) {
        if (!this.suggestionsEl || !suggestions.length) return;

        this.suggestionsEl.innerHTML = suggestions.map((s, i) =>
            `<div class="suggestion ${i === 0 ? 'selected' : ''}" data-index="${i}">${s}</div>`
        ).join('');

        this.suggestionsEl.style.display = 'block';
        this.isOpen = true;
    },

    hideSuggestions() {
        if (this.suggestionsEl) {
            this.suggestionsEl.style.display = 'none';
        }
        this.isOpen = false;
    },

    selectNextSuggestion() {
        const items = this.suggestionsEl?.querySelectorAll('.suggestion');
        if (!items?.length) return;

        const current = this.suggestionsEl.querySelector('.suggestion.selected');
        if (current) {
            current.classList.remove('selected');
            const next = current.nextElementSibling || items[0];
            next.classList.add('selected');
        }
    },

    selectPrevSuggestion() {
        const items = this.suggestionsEl?.querySelectorAll('.suggestion');
        if (!items?.length) return;

        const current = this.suggestionsEl.querySelector('.suggestion.selected');
        if (current) {
            current.classList.remove('selected');
            const prev = current.previousElementSibling || items[items.length - 1];
            prev.classList.add('selected');
        }
    }
};

// ==================== Chat Interface ====================

const ChatInterface = {
    container: null,
    messagesEl: null,

    init() {
        this.container = document.getElementById('chat-container');
        this.messagesEl = document.getElementById('chat-messages');
    },

    addMessage(role, content, extra = {}) {
        if (!this.messagesEl) return;

        const msgEl = document.createElement('div');
        msgEl.className = `chat-message ${role}`;

        let html = '';

        // Timestamp
        const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        html += `<span class="msg-time">${time}</span>`;

        // Role indicator
        const roleLabel = role === 'user' ? 'You' : role === 'assistant' ? 'TimeBrief' : 'System';
        html += `<span class="msg-role">${roleLabel}</span>`;

        // Content
        html += `<div class="msg-content">${this.escapeHtml(content)}</div>`;

        // Transcript (for voice)
        if (extra.transcript && extra.transcript !== content) {
            html += `<div class="msg-transcript">Heard: "${this.escapeHtml(extra.transcript)}"</div>`;
        }

        // Parsed info
        if (extra.parsed) {
            html += `<div class="msg-parsed">`;
            if (extra.parsed.intent) html += `<span class="parsed-intent">${extra.parsed.intent}</span>`;
            if (extra.parsed.matter) html += `<span class="parsed-matter">${extra.parsed.matter}</span>`;
            if (extra.parsed.activity) html += `<span class="parsed-activity">${extra.parsed.activity}</span>`;
            if (extra.parsed.duration) html += `<span class="parsed-duration">${extra.parsed.duration}h</span>`;
            html += `</div>`;
        }

        // Error
        if (extra.error) {
            html += `<div class="msg-error">${this.escapeHtml(extra.error.message)}</div>`;
        }

        // Suggestions
        if (extra.suggestions?.length) {
            html += `<div class="msg-suggestions">`;
            html += `<span>Did you mean:</span>`;
            extra.suggestions.forEach(s => {
                html += `<button class="suggestion-btn" onclick="CommandBar.element.value='${s}'; CommandBar.execute()">${s}</button>`;
            });
            html += `</div>`;
        }

        // Action
        if (extra.action?.can_undo) {
            html += `<button class="undo-btn" onclick="AppActions.undo()">Undo</button>`;
        }

        msgEl.innerHTML = html;
        this.messagesEl.appendChild(msgEl);
        this.scrollToBottom();
    },

    addResponse(result) {
        const extra = {
            transcript: result.transcript,
            parsed: result.parsed,
            suggestions: result.suggestions,
            action: result.action ? { can_undo: result.can_undo } : null
        };

        if (result.error_type) {
            extra.error = {
                type: result.error_type,
                message: result.error_message || result.message
            };
            this.addMessage('error', result.message, extra);
        } else {
            this.addMessage('assistant', result.message, extra);
        }

        // Handle clarification
        if (result.needs_clarification) {
            this.showClarification(result.clarification_question, result.clarification_options);
        }
    },

    showClarification(question, options) {
        const html = `
            <div class="clarification">
                <p>${this.escapeHtml(question)}</p>
                <div class="clarification-options">
                    ${options.map(o => `<button class="option-btn" onclick="ChatInterface.answerClarification('${o}')">${o}</button>`).join('')}
                </div>
            </div>
        `;
        const el = document.createElement('div');
        el.className = 'chat-message assistant clarification-msg';
        el.innerHTML = html;
        this.messagesEl.appendChild(el);
        this.scrollToBottom();
    },

    async answerClarification(answer) {
        // Remove clarification UI
        const clarif = this.messagesEl.querySelector('.clarification-msg');
        if (clarif) clarif.remove();

        // Process as new command
        CommandBar.element.value = answer;
        await CommandBar.execute();
    },

    renderHistory(messages) {
        if (!this.messagesEl) return;

        messages.forEach(msg => {
            const extra = {
                transcript: msg.transcript,
                parsed: msg.parsed,
                error: msg.error,
                suggestions: msg.suggestions,
                action: msg.action
            };
            this.addMessage(msg.role, msg.content, extra);
        });
    },

    scrollToBottom() {
        if (this.messagesEl) {
            this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
        }
    },

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
};

// ==================== Timer Widget ====================

const TimerWidget = {
    element: null,
    interval: null,
    data: null,

    init() {
        this.element = document.getElementById('timer-widget');
    },

    show(timerData) {
        this.data = timerData;

        if (!this.element) {
            this.createElement();
        }

        this.element.style.display = 'flex';
        this.update();
        this.startInterval();
    },

    hide() {
        if (this.element) {
            this.element.style.display = 'none';
        }
        this.stopInterval();
    },

    createElement() {
        this.element = document.createElement('div');
        this.element.id = 'timer-widget';
        this.element.className = 'timer-widget';
        this.element.innerHTML = `
            <div class="timer-indicator"></div>
            <div class="timer-matter"></div>
            <div class="timer-time">00:00:00</div>
            <div class="timer-controls">
                <button class="timer-btn pause" onclick="TimerWidget.togglePause()" title="Pause/Resume">⏸</button>
                <button class="timer-btn stop" onclick="TimerWidget.stop()" title="Stop">⏹</button>
            </div>
        `;

        // Make draggable
        this.element.style.cursor = 'move';
        this.makeDraggable();

        document.body.appendChild(this.element);
    },

    update() {
        if (!this.element || !this.data) return;

        const matterEl = this.element.querySelector('.timer-matter');
        const timeEl = this.element.querySelector('.timer-time');
        const indicator = this.element.querySelector('.timer-indicator');
        const pauseBtn = this.element.querySelector('.timer-btn.pause');

        if (matterEl) matterEl.textContent = this.data.matter_name || 'Timer';
        if (timeEl) timeEl.textContent = this.formatTime(this.data.elapsed_seconds);
        if (indicator) indicator.className = `timer-indicator ${this.data.is_paused ? 'paused' : 'running'}`;
        if (pauseBtn) pauseBtn.textContent = this.data.is_paused ? '▶' : '⏸';
    },

    formatTime(seconds) {
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = seconds % 60;
        return [h, m, s].map(v => v.toString().padStart(2, '0')).join(':');
    },

    startInterval() {
        this.stopInterval();
        this.interval = setInterval(() => {
            if (this.data && !this.data.is_paused) {
                this.data.elapsed_seconds++;
                this.update();
            }
        }, 1000);
    },

    stopInterval() {
        if (this.interval) {
            clearInterval(this.interval);
            this.interval = null;
        }
    },

    async togglePause() {
        try {
            const endpoint = this.data.is_paused ? '/api/timer/resume' : '/api/timer/pause';
            const response = await fetch(endpoint, { method: 'POST' });
            const result = await response.json();
            if (result.success) {
                this.data.is_paused = !this.data.is_paused;
                this.update();
            }
        } catch (e) {
            console.error('Timer pause error:', e);
        }
    },

    async stop() {
        try {
            const response = await fetch('/api/timer/stop', { method: 'POST' });
            const result = await response.json();
            if (result.success) {
                this.hide();
                AppState.activeTimer = null;
                ChatInterface.addMessage('assistant', result.message);
            }
        } catch (e) {
            console.error('Timer stop error:', e);
        }
    },

    makeDraggable() {
        let pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;

        this.element.onmousedown = (e) => {
            if (e.target.tagName === 'BUTTON') return;
            e.preventDefault();
            pos3 = e.clientX;
            pos4 = e.clientY;
            document.onmouseup = closeDrag;
            document.onmousemove = elementDrag;
        };

        const elementDrag = (e) => {
            e.preventDefault();
            pos1 = pos3 - e.clientX;
            pos2 = pos4 - e.clientY;
            pos3 = e.clientX;
            pos4 = e.clientY;
            this.element.style.top = (this.element.offsetTop - pos2) + "px";
            this.element.style.left = (this.element.offsetLeft - pos1) + "px";
            this.element.style.right = 'auto';
            this.element.style.bottom = 'auto';
        };

        const closeDrag = () => {
            document.onmouseup = null;
            document.onmousemove = null;
        };
    }
};

// ==================== Keyboard Shortcuts ====================

const KeyboardShortcuts = {
    shortcuts: {
        '/': { desc: 'Focus command bar', action: () => CommandBar.focus() },
        'Escape': { desc: 'Blur command bar', action: () => CommandBar.blur() },
        '?': { desc: 'Show shortcuts', action: () => KeyboardShortcuts.showOverlay() },
        'ctrl+z': { desc: 'Undo', action: () => AppActions.undo() },
        'ctrl+shift+z': { desc: 'Redo', action: () => AppActions.redo() },
        'ctrl+d': { desc: 'Toggle dark mode', action: () => AppState.toggleDarkMode() },
        'ctrl+t': { desc: 'Quick timer toggle', action: () => AppActions.toggleTimer() },
        'ctrl+r': { desc: 'Start recording', action: () => VoiceRecorder.toggle() },
        'g h': { desc: 'Go to Home', action: () => window.location.href = '/' },
        'g p': { desc: 'Go to Planning', action: () => window.location.href = '/planning' },
        'g r': { desc: 'Go to Review', action: () => window.location.href = '/review' },
        'g m': { desc: 'Go to Matters', action: () => window.location.href = '/matters' },
        'g c': { desc: 'Go to Chat', action: () => window.location.href = '/chat' },
    },

    overlay: null,
    pendingKey: null,

    handle(e) {
        // Don't trigger in input fields
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
            if (e.key === 'Escape') {
                e.target.blur();
            }
            return;
        }

        // Build key string
        let keyStr = '';
        if (e.ctrlKey) keyStr += 'ctrl+';
        if (e.shiftKey) keyStr += 'shift+';
        if (e.altKey) keyStr += 'alt+';
        keyStr += e.key.toLowerCase();

        // Check for two-key shortcuts (g + letter)
        if (this.pendingKey) {
            const combo = `${this.pendingKey} ${e.key.toLowerCase()}`;
            if (this.shortcuts[combo]) {
                e.preventDefault();
                this.shortcuts[combo].action();
            }
            this.pendingKey = null;
            return;
        }

        // Check for 'g' prefix
        if (e.key === 'g' && !e.ctrlKey && !e.altKey) {
            this.pendingKey = 'g';
            setTimeout(() => { this.pendingKey = null; }, 1000);
            return;
        }

        // Check single-key shortcuts
        if (this.shortcuts[keyStr]) {
            e.preventDefault();
            this.shortcuts[keyStr].action();
        } else if (this.shortcuts[e.key]) {
            e.preventDefault();
            this.shortcuts[e.key].action();
        }
    },

    showOverlay() {
        if (this.overlay) {
            this.hideOverlay();
            return;
        }

        this.overlay = document.createElement('div');
        this.overlay.className = 'shortcuts-overlay';
        this.overlay.onclick = () => this.hideOverlay();

        let html = '<div class="shortcuts-content" onclick="event.stopPropagation()">';
        html += '<h2>Keyboard Shortcuts</h2>';
        html += '<div class="shortcuts-grid">';

        for (const [key, info] of Object.entries(this.shortcuts)) {
            const displayKey = key.replace('ctrl+', '⌘/Ctrl+').replace('shift+', '⇧+');
            html += `<div class="shortcut-item">
                <kbd>${displayKey}</kbd>
                <span>${info.desc}</span>
            </div>`;
        }

        html += '</div>';
        html += '<p class="shortcuts-hint">Press ? or click outside to close</p>';
        html += '</div>';

        this.overlay.innerHTML = html;
        document.body.appendChild(this.overlay);
    },

    hideOverlay() {
        if (this.overlay) {
            this.overlay.remove();
            this.overlay = null;
        }
    }
};

// ==================== App Actions ====================

const AppActions = {
    async undo() {
        try {
            const response = await fetch('/api/undo', { method: 'POST' });
            const result = await response.json();
            ChatInterface.addMessage('assistant', result.message);
            if (result.refresh) {
                setTimeout(() => location.reload(), 500);
            }
        } catch (e) {
            ChatInterface.addMessage('error', 'Undo failed');
        }
    },

    async redo() {
        try {
            const response = await fetch('/api/redo', { method: 'POST' });
            const result = await response.json();
            ChatInterface.addMessage('assistant', result.message);
        } catch (e) {
            ChatInterface.addMessage('error', 'Redo failed');
        }
    },

    async toggleTimer() {
        if (AppState.activeTimer) {
            TimerWidget.stop();
        } else {
            CommandBar.element.value = 'start timer';
            CommandBar.focus();
        }
    }
};

// ==================== Voice Recorder ====================

const VoiceRecorder = {
    mediaRecorder: null,
    chunks: [],
    isRecording: false,

    async toggle() {
        if (this.isRecording) {
            this.stop();
        } else {
            await this.start();
        }
    },

    async start() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.mediaRecorder = new MediaRecorder(stream);
            this.chunks = [];

            this.mediaRecorder.ondataavailable = (e) => {
                this.chunks.push(e.data);
            };

            this.mediaRecorder.onstop = async () => {
                const blob = new Blob(this.chunks, { type: 'audio/webm' });
                await this.processAudio(blob);
                stream.getTracks().forEach(t => t.stop());
            };

            this.mediaRecorder.start();
            this.isRecording = true;
            this.updateUI(true);

        } catch (e) {
            console.error('Microphone access denied:', e);
            ChatInterface.addMessage('error', 'Microphone access denied');
        }
    },

    stop() {
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
            this.isRecording = false;
            this.updateUI(false);
        }
    },

    async processAudio(blob) {
        const formData = new FormData();
        formData.append('audio', blob, 'recording.webm');

        try {
            ChatInterface.addMessage('user', '🎤 [Voice input...]');

            const response = await fetch('/process-voice', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            ChatInterface.addResponse(result);

            if (result.refresh) {
                setTimeout(() => location.reload(), 500);
            }

        } catch (e) {
            ChatInterface.addMessage('error', 'Voice processing failed');
        }
    },

    updateUI(isRecording) {
        const btn = document.getElementById('voice-btn');
        if (btn) {
            btn.classList.toggle('recording', isRecording);
            btn.textContent = isRecording ? '⏹ Stop' : '🎤 Record';
        }
    }
};

// ==================== Contextual Sidebar ====================

const ContextualSidebar = {
    element: null,
    isOpen: false,
    currentMatter: null,
    data: {},

    init() {
        this.element = document.getElementById('contextual-sidebar');
        if (!this.element) {
            this.createElement();
        }
    },

    createElement() {
        this.element = document.createElement('aside');
        this.element.id = 'contextual-sidebar';
        this.element.className = 'contextual-sidebar';
        this.element.innerHTML = `
            <div class="sidebar-header">
                <span class="sidebar-title">Context</span>
                <button class="sidebar-close" onclick="ContextualSidebar.close()">&times;</button>
            </div>
            <div class="sidebar-content">
                <div class="sidebar-section" id="sidebar-matter-context">
                    <div class="sidebar-section-title">Current Matter</div>
                    <div class="sidebar-section-content">No matter selected</div>
                </div>
                <div class="sidebar-section" id="sidebar-productivity">
                    <div class="sidebar-section-title">Today's Progress</div>
                    <div class="sidebar-section-content">
                        <div class="mini-stat">
                            <span class="stat-label">Hours</span>
                            <span class="stat-value" id="sidebar-today-hours">0.0</span>
                        </div>
                        <div class="mini-stat">
                            <span class="stat-label">Entries</span>
                            <span class="stat-value" id="sidebar-today-entries">0</span>
                        </div>
                    </div>
                </div>
                <div class="sidebar-section" id="sidebar-gaps">
                    <div class="sidebar-section-title">Time Gaps</div>
                    <div class="sidebar-section-content" id="sidebar-gaps-list">No gaps detected</div>
                </div>
                <div class="sidebar-section" id="sidebar-suggestions">
                    <div class="sidebar-section-title">Suggestions</div>
                    <div class="sidebar-section-content" id="sidebar-suggestions-list"></div>
                </div>
            </div>
        `;
        document.body.appendChild(this.element);
    },

    toggle() {
        if (this.isOpen) {
            this.close();
        } else {
            this.open();
        }
    },

    open() {
        this.element.classList.add('open');
        this.isOpen = true;
        this.refresh();
    },

    close() {
        this.element.classList.remove('open');
        this.isOpen = false;
    },

    async refresh() {
        await Promise.all([
            this.loadProductivity(),
            this.loadGaps(),
            this.loadMatterContext()
        ]);
    },

    async loadProductivity() {
        try {
            const response = await fetch('/api/analytics/productivity');
            const data = await response.json();
            if (data.success) {
                document.getElementById('sidebar-today-hours').textContent =
                    data.stats.total_hours.toFixed(1);
                document.getElementById('sidebar-today-entries').textContent =
                    data.stats.entry_count;
            }
        } catch (e) {
            console.log('Failed to load productivity');
        }
    },

    async loadGaps() {
        try {
            const response = await fetch('/api/analytics/gaps');
            const data = await response.json();
            const container = document.getElementById('sidebar-gaps-list');

            if (data.success && data.gaps && data.gaps.length > 0) {
                container.innerHTML = data.gaps.slice(0, 3).map(gap => `
                    <div class="gap-item">
                        <span class="gap-time">${gap.start_time} - ${gap.end_time}</span>
                        <span class="gap-duration">${gap.duration_minutes}min</span>
                    </div>
                `).join('');
            } else {
                container.textContent = 'No gaps detected';
            }
        } catch (e) {
            console.log('Failed to load gaps');
        }
    },

    async loadMatterContext() {
        if (!this.currentMatter) return;

        try {
            const response = await fetch(`/api/matter/${this.currentMatter}/context`);
            const data = await response.json();
            const container = document.querySelector('#sidebar-matter-context .sidebar-section-content');

            if (data.success && data.context) {
                container.innerHTML = `
                    <div class="matter-context">
                        <div class="context-item">
                            <span class="context-label">Last Activity</span>
                            <span class="context-value">${data.context.last_activity_type || 'None'}</span>
                        </div>
                        <div class="context-item">
                            <span class="context-label">Recent Hours</span>
                            <span class="context-value">${data.context.recent_hours || 0}h</span>
                        </div>
                    </div>
                `;
            }
        } catch (e) {
            console.log('Failed to load matter context');
        }
    },

    setMatter(matterId) {
        this.currentMatter = matterId;
        if (this.isOpen) {
            this.loadMatterContext();
        }
    }
};

// ==================== Calendar View ====================

const CalendarView = {
    container: null,
    currentMonth: new Date(),
    data: {},

    init(containerId) {
        this.container = document.getElementById(containerId);
        if (this.container) {
            this.render();
            this.loadData();
        }
    },

    render() {
        const year = this.currentMonth.getFullYear();
        const month = this.currentMonth.getMonth();
        const firstDay = new Date(year, month, 1);
        const lastDay = new Date(year, month + 1, 0);
        const startDayOfWeek = firstDay.getDay();

        const monthName = this.currentMonth.toLocaleDateString('en-US', {
            month: 'long',
            year: 'numeric'
        });

        let html = `
            <div class="calendar-controls">
                <button class="btn-icon" onclick="CalendarView.prevMonth()">&larr;</button>
                <span class="calendar-month-name">${monthName}</span>
                <button class="btn-icon" onclick="CalendarView.nextMonth()">&rarr;</button>
            </div>
            <div class="calendar-grid">
        `;

        // Headers
        const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        days.forEach(day => {
            html += `<div class="calendar-header">${day}</div>`;
        });

        // Empty cells before first day
        for (let i = 0; i < startDayOfWeek; i++) {
            html += `<div class="calendar-day empty"></div>`;
        }

        // Days of month
        const today = new Date();
        for (let day = 1; day <= lastDay.getDate(); day++) {
            const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            const isToday = today.getFullYear() === year &&
                           today.getMonth() === month &&
                           today.getDate() === day;
            const dayData = this.data[dateStr] || {};
            const hasEntries = dayData.hours && dayData.hours > 0;

            let classes = 'calendar-day';
            if (isToday) classes += ' today';
            if (hasEntries) classes += ' has-entries';

            html += `
                <div class="${classes}" data-date="${dateStr}" onclick="CalendarView.selectDay('${dateStr}')">
                    <div class="calendar-day-number">${day}</div>
                    ${hasEntries ? `<div class="calendar-day-hours">${dayData.hours.toFixed(1)}h</div>` : ''}
                </div>
            `;
        }

        html += '</div>';
        this.container.innerHTML = html;
    },

    async loadData() {
        const year = this.currentMonth.getFullYear();
        const month = this.currentMonth.getMonth() + 1;

        try {
            const response = await fetch(`/api/calendar/${year}/${month}`);
            const result = await response.json();
            if (result.success) {
                this.data = result.days || {};
                this.render();
            }
        } catch (e) {
            console.log('Failed to load calendar data');
        }
    },

    prevMonth() {
        this.currentMonth.setMonth(this.currentMonth.getMonth() - 1);
        this.render();
        this.loadData();
    },

    nextMonth() {
        this.currentMonth.setMonth(this.currentMonth.getMonth() + 1);
        this.render();
        this.loadData();
    },

    selectDay(dateStr) {
        // Navigate to review page for that day
        window.location.href = `/review?date=${dateStr}`;
    }
};

// ==================== Dashboard ====================

const Dashboard = {
    container: null,

    init(containerId) {
        this.container = document.getElementById(containerId);
        if (this.container) {
            this.load();
        }
    },

    async load() {
        try {
            const [productivity, heatmap, health] = await Promise.all([
                fetch('/api/analytics/productivity').then(r => r.json()),
                fetch('/api/analytics/heatmap').then(r => r.json()),
                fetch('/api/analytics/matter-health').then(r => r.json())
            ]);

            this.render(productivity, heatmap, health);
        } catch (e) {
            console.error('Dashboard load error:', e);
        }
    },

    render(productivity, heatmap, health) {
        let html = '<div class="dashboard-grid">';

        // Productivity Stats Card
        if (productivity.success) {
            const stats = productivity.stats;
            const change = stats.comparison_to_average || 0;
            const changeClass = change >= 0 ? 'positive' : 'negative';
            const changeSign = change >= 0 ? '+' : '';

            html += `
                <div class="dash-card">
                    <div class="dash-card-header">
                        <span class="dash-card-title">Today's Hours</span>
                        <span class="dash-card-change ${changeClass}">${changeSign}${change.toFixed(0)}%</span>
                    </div>
                    <div class="dash-card-value">${stats.total_hours.toFixed(1)}h</div>
                    <div class="dash-card-subtitle">${stats.entry_count} entries</div>
                </div>
            `;
        }

        // Billable Ratio Card
        if (productivity.success && productivity.stats.billable_percentage !== undefined) {
            html += `
                <div class="dash-card">
                    <div class="dash-card-header">
                        <span class="dash-card-title">Billable</span>
                    </div>
                    <div class="dash-card-value">${productivity.stats.billable_percentage.toFixed(0)}%</div>
                    <div class="dash-card-subtitle">${productivity.stats.billable_hours.toFixed(1)}h billable</div>
                </div>
            `;
        }

        // Heatmap Card
        if (heatmap.success && heatmap.weeks) {
            html += `
                <div class="dash-card" style="grid-column: span 2;">
                    <div class="dash-card-header">
                        <span class="dash-card-title">Weekly Activity</span>
                    </div>
                    <div class="heatmap-container">
                        ${this.renderHeatmap(heatmap.weeks)}
                    </div>
                </div>
            `;
        }

        // Matter Health Card
        if (health.success && health.matters) {
            html += `
                <div class="dash-card">
                    <div class="dash-card-header">
                        <span class="dash-card-title">Matter Health</span>
                    </div>
                    ${health.matters.slice(0, 5).map(m => `
                        <div class="matter-health">
                            <div class="health-indicator ${m.status}"></div>
                            <span class="health-name">${m.name}</span>
                            <span class="health-stats">${m.recent_hours.toFixed(1)}h</span>
                        </div>
                    `).join('')}
                </div>
            `;
        }

        html += '</div>';
        this.container.innerHTML = html;
    },

    renderHeatmap(weeks) {
        let html = '<div class="heatmap">';

        // Day labels
        const dayLabels = ['', 'Mon', '', 'Wed', '', 'Fri', ''];
        html += '<div class="heatmap-row">';
        dayLabels.forEach(label => {
            html += `<div class="heatmap-label">${label}</div>`;
        });
        html += '</div>';

        // Weeks
        weeks.forEach(week => {
            html += '<div class="heatmap-row">';
            week.days.forEach(day => {
                const level = this.getHeatLevel(day.hours);
                html += `<div class="heatmap-cell level-${level}" title="${day.date}: ${day.hours.toFixed(1)}h"></div>`;
            });
            html += '</div>';
        });

        html += '</div>';
        return html;
    },

    getHeatLevel(hours) {
        if (hours === 0) return 0;
        if (hours < 2) return 1;
        if (hours < 4) return 2;
        if (hours < 6) return 3;
        if (hours < 8) return 4;
        return 5;
    }
};

// ==================== Dark Mode Integration ====================

const DarkModeManager = {
    storageKey: 'timebrief_dark_mode',

    init() {
        // Check stored preference
        const stored = localStorage.getItem(this.storageKey);
        if (stored !== null) {
            this.setTheme(stored === 'true');
        } else {
            // Check system preference
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            this.setTheme(prefersDark);
        }

        // Listen for system changes
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            if (localStorage.getItem(this.storageKey) === null) {
                this.setTheme(e.matches);
            }
        });
    },

    toggle() {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        this.setTheme(!isDark);
        localStorage.setItem(this.storageKey, !isDark);

        // Sync to server
        fetch('/api/preferences', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ dark_mode: !isDark })
        }).catch(() => {});
    },

    setTheme(isDark) {
        document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
        AppState.darkMode = isDark;
    }
};

// ==================== Initialization ====================

document.addEventListener('DOMContentLoaded', () => {
    AppState.init();
    CommandBar.init();
    ChatInterface.init();
    TimerWidget.init();
    ContextualSidebar.init();
    DarkModeManager.init();

    // Initialize dashboard if on dashboard page
    if (document.getElementById('dashboard-container')) {
        Dashboard.init('dashboard-container');
    }

    // Initialize calendar if on calendar page
    if (document.getElementById('calendar-container')) {
        CalendarView.init('calendar-container');
    }
});
