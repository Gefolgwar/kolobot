let allM11Docs = [];

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
    if (doc.match_status !== 'full') return true;
    return false;
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
            <td colspan="7" class="py-12 text-center text-slate-500">
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
        const statusHtml = renderM11Status(doc);
        const vimogaHtml = renderLinkedVimoga(doc);

        html += `<tr class="hover:bg-slate-800/40 transition cursor-pointer" onclick="viewDocument(${doc.id}, '${escapeHtml(doc.filename || '')}', '${escapeHtml(doc.file_type || '')}')">
            <td class="py-4 px-3 font-medium text-slate-200" data-label="№ М-11">
                <span class="flex items-center gap-2">
                    <i class="fa-solid fa-file-invoice text-indigo-400"></i>
                    <span>${docNum}</span>
                </span>
            </td>
            <td class="py-4 px-3 text-slate-300" data-label="Дата">${docDate}</td>
            <td class="py-4 px-3 text-slate-300" data-label="Підстава/Кому">${req}</td>
            <td class="py-4 px-3 text-blue-400 font-medium" data-label="Позицій">${itemCount}</td>
            <td class="py-4 px-3" data-label="Статус">${statusHtml}</td>
            <td class="py-4 px-3" data-label="Пов'язана ВИМОГА">${vimogaHtml}</td>
            <td class="py-4 px-3 text-right" data-label="Дії">
                <button type="button" onclick="event.stopPropagation(); viewDocument(${doc.id}, '${escapeHtml(doc.filename || '')}', '${escapeHtml(doc.file_type || '')}')" class="p-2 text-slate-400 hover:text-sky-400 hover:bg-sky-500/10 rounded-lg transition" title="Переглянути документ">
                    <i class="fa-solid fa-eye"></i>
                </button>
            </td>
        </tr>`;
    });

    tbody.innerHTML = html;
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
