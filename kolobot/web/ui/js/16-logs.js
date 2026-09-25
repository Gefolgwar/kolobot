
let allLogs = [];
let lastLogId = 0;
let autoScroll = true;
let logEventSource = null;
let logPollInterval = null;

function toggleAutoScroll() {
    const el = document.getElementById('log-autoscroll');
    autoScroll = el ? el.checked : true;
    if (autoScroll) {
        scrollLogsToBottom();
    }
}

function scrollLogsToBottom() {
    const term = document.getElementById('log-terminal');
    if (term) {
        term.scrollTop = term.scrollHeight;
    }
}

async function fetchLogs() {
    try {
        const res = await fetch('/api/logs?since_id=' + lastLogId);
        if (!res.ok) return;
        const data = await res.json();
        if (data.logs && data.logs.length > 0) {
            appendLogs(data.logs);
        }
        if (data.last_id) {
            lastLogId = Math.max(lastLogId, data.last_id);
        }
        updateLogBadge(data.total_count || allLogs.length);
    } catch (e) {
        console.error('Fetch logs error:', e);
    }
}

function updateLogBadge(totalCount) {
    const badge = document.getElementById('logs-count');
    if (badge) {
        badge.textContent = totalCount;
    }
}

function appendLogs(newEntries) {
    if (!newEntries || newEntries.length === 0) return;
    const existingIds = new Set(allLogs.map(l => l.id));
    for (const entry of newEntries) {
        if (!existingIds.has(entry.id)) {
            allLogs.push(entry);
            existingIds.add(entry.id);
            if (entry.id > lastLogId) {
                lastLogId = entry.id;
            }
        }
    }
    if (allLogs.length > 5000) {
        allLogs = allLogs.slice(-5000);
    }
    renderLogs();
    updateLogBadge(allLogs.length);
}

function onLogFilterChange() {
    renderLogs();
}

function renderLogs() {
    const container = document.getElementById('log-lines');
    const emptyState = document.getElementById('log-empty-state');
    const ratioEl = document.getElementById('log-count-ratio');
    if (!container) return;

    const query = (document.getElementById('log-search-input')?.value || '').toLowerCase().trim();
    const showInfo = document.getElementById('lvl-info')?.checked ?? true;
    const showSuccess = document.getElementById('lvl-success')?.checked ?? true;
    const showWarn = document.getElementById('lvl-warn')?.checked ?? true;
    const showErr = document.getElementById('lvl-err')?.checked ?? true;

    const filtered = allLogs.filter(entry => {
        const lvl = (entry.level || 'INFO').toUpperCase();
        if (lvl === 'INFO' && !showInfo) return false;
        if (lvl === 'SUCCESS' && !showSuccess) return false;
        if (lvl === 'WARN' && !showWarn) return false;
        if (lvl === 'ERR' && !showErr) return false;

        if (query) {
            const text = (entry.timestamp + ' ' + entry.level + ' ' + entry.logger + ' ' + entry.message + ' ' + (entry.raw || '')).toLowerCase();
            if (!text.includes(query)) return false;
        }
        return true;
    });

    if (ratioEl) {
        ratioEl.textContent = filtered.length + '/' + allLogs.length;
    }

    if (filtered.length === 0) {
        container.innerHTML = '';
        if (emptyState) emptyState.classList.remove('hidden');
        return;
    }

    if (emptyState) emptyState.classList.add('hidden');

    let html = '';
    for (const l of filtered) {
        const lvl = (l.level || 'INFO').toUpperCase();
        let lvlBg = 'bg-sky-500/10 text-sky-400 border border-sky-500/20';
        if (lvl === 'SUCCESS') {
            lvlBg = 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20';
        } else if (lvl === 'WARN') {
            lvlBg = 'bg-amber-500/10 text-amber-400 border border-amber-500/20';
        } else if (lvl === 'ERR') {
            lvlBg = 'bg-rose-500/10 text-rose-400 border border-rose-500/20';
        } else if (lvl === 'DEBUG') {
            lvlBg = 'bg-purple-500/10 text-purple-400 border border-purple-500/20';
        }

        const ts = esc(l.timestamp || '');
        const lg = esc(l.logger || '');
        const msg = esc(l.message || '');

        let formattedMsg = msg;
        if (query) {
            const regex = new RegExp('(' + query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'gi');
            formattedMsg = formattedMsg.replace(regex, '<mark class="bg-yellow-500/30 text-yellow-200 px-0.5 rounded">$1</mark>');
        }

        html += `<div class="hover:bg-slate-900/60 py-0.5 px-1.5 rounded transition flex items-start gap-2 text-[11px] font-mono leading-relaxed border-b border-slate-900/40">
            <span class="text-slate-500 shrink-0 select-none">${ts}</span>
            <span class="px-1.5 py-0.2 rounded text-[10px] font-bold shrink-0 ${lvlBg}">${lvl}</span>
            <span class="text-slate-400 shrink-0 select-none">[${lg}]</span>
            <span class="text-slate-200 break-words flex-1 select-text ${lvl === 'ERR' ? 'text-rose-300 font-semibold' : ''}">${formattedMsg}</span>
        </div>`;
    }

    container.innerHTML = html;

    if (autoScroll) {
        scrollLogsToBottom();
    }
}

async function clearLogsServer() {
    try {
        await fetch('/api/logs/clear', { method: 'POST' });
        allLogs = [];
        lastLogId = 0;
        renderLogs();
        updateLogBadge(0);
    } catch (e) {
        console.error('Clear logs error:', e);
    }
}

function connectLogStream() {
    try {
        if (window.EventSource) {
            logEventSource = new EventSource('/api/logs/stream');
            logEventSource.onmessage = function(event) {
                try {
                    const entry = JSON.parse(event.data);
                    appendLogs([entry]);
                } catch (err) {
                    console.error('SSE parse error:', err);
                }
            };
            logEventSource.onerror = function() {
                if (!logPollInterval) {
                    logPollInterval = setInterval(fetchLogs, 2000);
                }
            };
        } else {
            logPollInterval = setInterval(fetchLogs, 2000);
        }
    } catch (e) {
        logPollInterval = setInterval(fetchLogs, 2000);
    }
}
