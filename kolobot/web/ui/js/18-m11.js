let allM11Docs = [];
let currentM11BindDocId = null;
let availableVimogas = [];

function escapeHtml(s) {
    return String(s || '').replace(/[&<>"']/g, m => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    }[m]));
}

function isM11Problematic(doc) {
    if (!doc) return false;
    if (doc.needs_review) return true;
    if (!doc.linked_vimoga) return true;
    if (doc.match_status === 'none' || doc.match_status === 'unlinked') return true;
    if (doc.match_status === 'partial' || doc.match_status === 'conflict') return true;
    if (doc.match_status === 'full' || doc.match_status === 'manual') return false;
    return true;
}

function updateM11Badge(problematicCount) {
    const badge = document.getElementById('m11-badge');
    const problemEl = document.getElementById('problem-m11-count');
    const totalEl = document.getElementById('total-m11-count');

    const count = (typeof problematicCount === 'number')
        ? problematicCount
        : allM11Docs.filter(isM11Problematic).length;

    if (totalEl) totalEl.textContent = allM11Docs.length;
    if (problemEl) problemEl.textContent = count;

    if (badge) {
        badge.textContent = count;
        if (count > 0) {
            badge.className = 'ml-1.5 px-2 py-0.5 bg-rose-500/20 text-rose-400 border border-rose-500/30 rounded-full text-xs font-mono font-bold';
        } else {
            badge.className = 'ml-1.5 px-2 py-0.5 bg-slate-800 text-slate-500 rounded-full text-xs font-mono';
        }
    }
}

function renderM11Status(doc) {
    if (!doc) return '—';

    if (doc.needs_review) {
        return `<span class="inline-flex items-center gap-1.5 text-amber-400 font-medium" title="Потребує перевірки">
            <i class="fa-solid fa-triangle-exclamation"></i>
            <span>Потребує перевірки</span>
        </span>`;
    }

    if (doc.match_status === 'full') {
        return `<span class="inline-flex items-center gap-1.5 text-emerald-400 font-medium" title="Повний збіг">
            <i class="fa-solid fa-check text-base"></i>
            <span>Повний</span>
        </span>`;
    }

    if (doc.match_status === 'manual') {
        return `<span class="inline-flex items-center gap-1.5 text-sky-400 font-medium" title="Зв'язано вручну">
            <i class="fa-solid fa-link text-xs"></i>
            <span>Вручну</span>
        </span>`;
    }

    if (doc.match_status === 'partial') {
        return `<span class="inline-flex items-center gap-1.5 text-amber-400 font-medium" title="Частковий збіг">
            <i class="fa-solid fa-exclamation text-base"></i>
            <span>Частковий</span>
        </span>`;
    }

    return `<span class="inline-flex items-center gap-1.5 text-rose-400 font-medium" title="Немає збігу">
        <i class="fa-solid fa-circle text-rose-500 text-xs"></i>
        <span>Без збігу</span>
    </span>`;
}

function renderLinkedVimoga(doc) {
    if (!doc || !doc.linked_vimoga) {
        return '<span class="text-slate-500">—</span>';
    }

    const v = doc.linked_vimoga;
    const vNum = v.number || v.doc_number || ('ID ' + v.id);
    const vDate = v.date || v.doc_date || '';
    const label = '№ ' + escapeHtml(vNum) + (vDate ? ' (' + escapeHtml(vDate) + ')' : '');

    return `<button type="button" onclick="event.stopPropagation(); viewDocument(${v.id}, '${escapeHtml(v.filename || '')}', '${escapeHtml(v.file_type || '')}')" class="text-sky-400 hover:text-sky-300 hover:underline inline-flex items-center gap-1.5 transition text-left cursor-pointer" title="Переглянути пов'язану вимогу">
        <i class="fa-solid fa-link text-xs"></i>
        <span class="font-medium">${label}</span>
    </button>`;
}

function renderM11Table(docs) {
    const tbody = document.getElementById('m11-tbody');
    const visibleEl = document.getElementById('visible-m11-count');
    if (visibleEl) visibleEl.textContent = docs ? docs.length : 0;
    if (!tbody) return;

    if (!docs || docs.length === 0) {
        tbody.innerHTML = `<tr>
            <td colspan="9" class="py-12 text-center text-slate-500">
                <i class="fa-solid fa-file-invoice text-3xl mb-3 text-slate-600 block"></i>
                <p>Документів М-11 немає.</p>
            </td>
        </tr>`;
        return;
    }

    let html = '';
    docs.forEach(doc => {
        const docNum = escapeHtml(doc.doc_number || '—');
        const docDate = escapeHtml(doc.doc_date || '—');
        const req = escapeHtml(doc.requested_by || doc.requested_via || '—');
        const itemCount = doc.item_count || 0;
        const processingStatusHtml = docStatusBadge(doc);
        const matchStatusHtml = renderM11Status(doc);
        const vimogaHtml = renderLinkedVimoga(doc);

        let actionsHtml = `<div class="flex items-center justify-end gap-1.5 flex-wrap">`;
        if (doc.link_id) {
            if (doc.needs_review || doc.match_status === 'partial') {
                actionsHtml += `<button type="button" onclick="event.stopPropagation(); confirmM11Link(${doc.link_id})" class="px-2.5 py-1 text-xs font-medium text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 hover:bg-emerald-500/20 rounded-lg transition flex items-center gap-1 cursor-pointer" title="Підтвердити зв'язок">
                    <i class="fa-solid fa-check"></i>
                    <span>Підтвердити</span>
                </button>`;
            }
            actionsHtml += `<button type="button" onclick="event.stopPropagation(); unbindM11Link(${doc.link_id})" class="px-2.5 py-1 text-xs font-medium text-rose-400 bg-rose-500/10 border border-rose-500/30 hover:bg-rose-500/20 rounded-lg transition flex items-center gap-1 cursor-pointer" title="Відв'язати документ">
                <i class="fa-solid fa-unlink"></i>
                <span>Відв'язати</span>
            </button>`;
        } else {
            actionsHtml += `<button type="button" onclick="event.stopPropagation(); openBindModal(${doc.id}, '${docNum}')" class="px-2.5 py-1 text-xs font-medium text-sky-400 bg-sky-500/10 border border-sky-500/30 hover:bg-sky-500/20 rounded-lg transition flex items-center gap-1 cursor-pointer" title="Прив'язати до вимоги вручну">
                <i class="fa-solid fa-link"></i>
                <span>Прив'язати</span>
            </button>`;
        }
        actionsHtml += `<button type="button" onclick="event.stopPropagation(); viewDocument(${doc.id}, '${escapeHtml(doc.filename || '')}', '${escapeHtml(doc.file_type || '')}')" class="p-1.5 text-slate-400 hover:text-sky-400 hover:bg-sky-500/10 rounded-lg transition" title="Переглянути документ">
            <i class="fa-solid fa-eye"></i>
        </button></div>`;

        html += `<tr class="hover:bg-slate-800/40 transition cursor-pointer" onclick="toggleM11Accordion(${doc.id})">
            <td class="py-4 px-3 whitespace-nowrap"><i id="m11-chevron-${doc.id}" class="fa-solid fa-chevron-right text-[10px] text-slate-500 transition-transform"></i></td>
            <td class="py-4 px-3 font-medium text-slate-200" data-label="№ М-11">
                <span class="flex items-center gap-2">
                    <i class="fa-solid fa-file-invoice text-indigo-400"></i>
                    <span>${docNum}</span>
                </span>
            </td>
            <td class="py-4 px-3 text-slate-300" data-label="Дата">${docDate}</td>
            <td class="py-4 px-3 text-slate-300" data-label="Підстава/Кому">${req}</td>
            <td class="py-4 px-3 text-blue-400 font-medium" data-label="Позицій">${itemCount}</td>
            <td class="py-4 px-3" data-label="Статус">${processingStatusHtml}</td>
            <td class="py-4 px-3" data-label="Збіг">${matchStatusHtml}</td>
            <td class="py-4 px-3" data-label="Пов'язана ВИМОГА">${vimogaHtml}</td>
            <td class="py-4 px-3 text-right" data-label="Дії">${actionsHtml}</td>
        </tr>
        <tr id="m11-impact-row-${doc.id}" class="hidden">
            <td colspan="9" class="p-0">
                <div class="expand-row px-8 py-4 border-t border-slate-800/40">
                    <div id="m11-impact-content-${doc.id}" class="text-xs text-slate-400">Завантаження...</div>
                </div>
            </td>
        </tr>`;
    });

    tbody.innerHTML = html;
}

async function toggleM11Accordion(docId) {
    const row = document.getElementById('m11-impact-row-' + docId);
    const chevron = document.getElementById('m11-chevron-' + docId);
    if (!row) return;

    if (!row.classList.contains('hidden')) {
        row.classList.add('hidden');
        if (chevron) chevron.style.transform = '';
        return;
    }

    row.classList.remove('hidden');
    if (chevron) chevron.style.transform = 'rotate(90deg)';

    const content = document.getElementById('m11-impact-content-' + docId);
    if (content) {
        content.innerHTML = '<div class="py-4 text-center text-slate-500"><i class="fa-solid fa-spinner fa-spin mr-2"></i>Завантаження даних...</div>';
    }
    await reloadDocImpact(docId);
}

function filterM11Docs() {
    const q = (document.getElementById('search-m11')?.value || '').toLowerCase().trim();
    if (!q) {
        renderM11Table(allM11Docs);
        return;
    }

    const filtered = allM11Docs.filter(d => {
        const num = (d.doc_number || '').toLowerCase();
        const dt = (d.doc_date || '').toLowerCase();
        const req = (d.requested_by || '').toLowerCase();
        const via = (d.requested_via || '').toLowerCase();
        const vim = d.linked_vimoga
            ? ((d.linked_vimoga.number || d.linked_vimoga.doc_number || '') + ' ' + (d.linked_vimoga.date || d.linked_vimoga.doc_date || '')).toLowerCase()
            : '';
        return num.includes(q) || dt.includes(q) || req.includes(q) || via.includes(q) || vim.includes(q);
    });

    renderM11Table(filtered);
}

async function fetchM11Docs() {
    try {
        const res = await fetch('/api/warehouse/m11');
        if (!res.ok) return;
        allM11Docs = await res.json();
        updateM11Badge();
        filterM11Docs();
    } catch (e) {
        console.error('Fetch M-11 error:', e);
    }
}

async function confirmM11Link(linkId) {
    if (!linkId) return;
    try {
        const res = await fetch(`/api/m11/links/${linkId}/confirm`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            alert(err.error || 'Помилка підтвердження зв\'язку');
            return;
        }
        await fetchM11Docs();
    } catch (e) {
        console.error('Error confirming link:', e);
        alert('Помилка мережі при підтвердженні');
    }
}

async function unbindM11Link(linkId) {
    if (!linkId) return;
    if (!confirm('Ви дійсно бажаєте відв\'язати цей документ?')) {
        return;
    }
    try {
        const res = await fetch(`/api/m11/links/${linkId}`, {
            method: 'DELETE'
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            alert(err.error || 'Помилка видалення зв\'язку');
            return;
        }
        await fetchM11Docs();
    } catch (e) {
        console.error('Error deleting link:', e);
        alert('Помилка мережі при відв\'язанні');
    }
}

async function openBindModal(docId, docNum) {
    currentM11BindDocId = docId;
    const modal = document.getElementById('m11-bind-modal');
    const subtitle = document.getElementById('m11-bind-subtitle');
    const searchInput = document.getElementById('m11-bind-search');
    if (searchInput) searchInput.value = '';
    if (subtitle) {
        subtitle.textContent = (docNum && docNum !== '—')
            ? `Виберіть відповідну класичну вимогу для М-11 № ${docNum}`
            : 'Виберіть відповідну класичну вимогу для М-11';
    }
    if (modal) modal.classList.remove('hidden');

    const listEl = document.getElementById('m11-bind-list');
    if (listEl) {
        listEl.innerHTML = '<div class="py-12 text-center text-slate-500"><i class="fa-solid fa-spinner fa-spin text-2xl mb-2 block text-sky-400"></i>Завантаження вимог...</div>';
    }

    try {
        const res = await fetch('/api/m11/available-vimogas');
        if (!res.ok) {
            if (listEl) listEl.innerHTML = '<div class="py-12 text-center text-rose-400"><i class="fa-solid fa-circle-exclamation text-2xl mb-2 block"></i>Помилка завантаження вимог</div>';
            return;
        }
        availableVimogas = await res.json();
        renderAvailableVimogas(availableVimogas);
    } catch (e) {
        console.error('Error fetching available vimogas:', e);
        if (listEl) listEl.innerHTML = '<div class="py-12 text-center text-rose-400"><i class="fa-solid fa-circle-exclamation text-2xl mb-2 block"></i>Помилка завантаження вимог</div>';
    }
}

function closeBindModal() {
    currentM11BindDocId = null;
    const modal = document.getElementById('m11-bind-modal');
    if (modal) modal.classList.add('hidden');
}

function filterAvailableVimogas() {
    const q = (document.getElementById('m11-bind-search')?.value || '').toLowerCase().trim();
    if (!q) {
        renderAvailableVimogas(availableVimogas);
        return;
    }
    const filtered = availableVimogas.filter(v => {
        const num = (v.doc_number || '').toLowerCase();
        const dt = (v.doc_date || '').toLowerCase();
        const fn = (v.filename || '').toLowerCase();
        const req = (v.requested_by || '').toLowerCase();
        return num.includes(q) || dt.includes(q) || fn.includes(q) || req.includes(q);
    });
    renderAvailableVimogas(filtered);
}

function renderAvailableVimogas(list) {
    const listEl = document.getElementById('m11-bind-list');
    if (!listEl) return;
    if (!list || list.length === 0) {
        listEl.innerHTML = '<div class="py-12 text-center text-slate-500"><i class="fa-solid fa-file-lines text-2xl mb-2 block text-slate-600"></i>Вимог не знайдено</div>';
        return;
    }

    let html = '';
    list.forEach(v => {
        const vNum = escapeHtml(v.doc_number || 'б/н');
        const vDate = escapeHtml(v.doc_date || '');
        const fn = escapeHtml(v.filename || '');
        const req = escapeHtml(v.requested_by || '');

        if (v.is_linked) {
            const m11Num = escapeHtml(v.linked_m11_doc_number || '');
            const m11Suffix = m11Num ? ` (№ ${m11Num})` : '';
            html += `<div class="p-3 bg-slate-900/30 border border-slate-800/60 rounded-xl flex items-center justify-between opacity-50 cursor-not-allowed gap-3">
                <div class="flex items-center gap-3 min-w-0">
                    <div class="w-8 h-8 rounded-lg bg-slate-800 text-slate-500 flex items-center justify-center shrink-0">
                        <i class="fa-solid fa-file-lines text-sm"></i>
                    </div>
                    <div class="min-w-0">
                        <div class="font-medium text-slate-400 flex items-center gap-2 flex-wrap">
                            <span>№ ${vNum}</span>
                            ${vDate ? `<span class="text-xs text-slate-500">(${vDate})</span>` : ''}
                            <span class="px-2 py-0.5 rounded bg-slate-800 text-slate-400 text-xs border border-slate-700">вже має М-11${m11Suffix}</span>
                        </div>
                        <div class="text-xs text-slate-600 break-words">${req || fn}</div>
                    </div>
                </div>
                <span class="shrink-0 text-xs text-slate-600 px-3 py-1.5 font-medium">Прив'язано</span>
            </div>`;
        } else {
            html += `<div class="p-3 bg-slate-900/60 hover:bg-slate-800/70 border border-slate-800 hover:border-sky-500/40 rounded-xl flex items-center justify-between transition gap-3">
                <div class="flex items-center gap-3 min-w-0">
                    <div class="w-8 h-8 rounded-lg bg-sky-500/10 text-sky-400 flex items-center justify-center shrink-0">
                        <i class="fa-solid fa-file-lines text-sm"></i>
                    </div>
                    <div class="min-w-0">
                        <div class="font-medium text-slate-200 flex items-center gap-2 flex-wrap">
                            <span>№ ${vNum}</span>
                            ${vDate ? `<span class="text-xs text-slate-400">(${vDate})</span>` : ''}
                        </div>
                        <div class="text-xs text-slate-500 break-words">${req || fn}</div>
                    </div>
                </div>
                <button type="button" onclick="selectVimogaForBind(${v.id})" class="shrink-0 px-3 py-1.5 bg-sky-600 hover:bg-sky-500 text-white text-xs font-medium rounded-lg transition shadow-sm cursor-pointer flex items-center gap-1.5">
                    <i class="fa-solid fa-link text-xs"></i>
                    <span>Вибрати</span>
                </button>
            </div>`;
        }
    });
    listEl.innerHTML = html;
}

async function selectVimogaForBind(vimogaDocId) {
    if (!currentM11BindDocId || !vimogaDocId) return;
    try {
        const res = await fetch(`/api/m11/${currentM11BindDocId}/bind`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ vimoga_doc_id: vimogaDocId })
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            alert(err.error || 'Помилка прив\'язки документа');
            return;
        }
        closeBindModal();
        await fetchM11Docs();
    } catch (e) {
        console.error('Error binding document:', e);
        alert('Помилка мережі при прив\'язці');
    }
}

// Hook into tab switching and global refresh
const _origSwitchTab = switchTab;
switchTab = function(tab) {
    const pm = document.getElementById('panel-m11');
    const tm = document.getElementById('tab-m11');
    if (pm) pm.classList.add('hidden');
    if (tm) tm.className = tm.className.replace('tab-active', 'tab-inactive');

    if (typeof _origSwitchTab === 'function') {
        _origSwitchTab(tab);
    }

    if (tab === 'm11') {
        const wh = document.getElementById('panel-warehouse');
        const dc = document.getElementById('panel-documents');
        const lg = document.getElementById('panel-logs');
        if (wh) wh.classList.add('hidden');
        if (dc) dc.classList.add('hidden');
        if (lg) lg.classList.add('hidden');

        const tw = document.getElementById('tab-warehouse');
        const td = document.getElementById('tab-documents');
        const tl = document.getElementById('tab-logs');
        if (tw) tw.className = tw.className.replace('tab-active', 'tab-inactive');
        if (td) td.className = td.className.replace('tab-active', 'tab-inactive');
        if (tl) tl.className = tl.className.replace('tab-active', 'tab-inactive');

        if (pm) pm.classList.remove('hidden');
        if (tm) tm.className = tm.className.replace('tab-inactive', 'tab-active');
        fetchM11Docs();
    }
};

const _origRefreshAll = refreshAll;
refreshAll = async function() {
    if (typeof _origRefreshAll === 'function') {
        await Promise.all([_origRefreshAll(), fetchM11Docs()]);
    } else {
        await fetchM11Docs();
    }
};
