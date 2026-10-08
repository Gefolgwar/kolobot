let allItems = [];
let allDocs = [];
let currentViewingDocId = null;
let activeFilter = '';

function isM11Doc(doc) {
    if (!doc) return false;
    const t = (doc.doc_type || '').trim().replace(/\s+/g, ' ').toUpperCase();
    return t === 'ВИМОГА М-11' || t === 'М-11' || t === 'ВИМОГА M-11' || t === 'M-11';
}

function isClassicVimoga(doc) {
    if (!doc || isM11Doc(doc)) return false;
    const t = (doc.doc_type || '').trim().replace(/\s+/g, ' ').toUpperCase();
    return t === 'ВИМОГА';
}

function switchTab(tab) {
    const wh = document.getElementById('panel-warehouse');
    const dc = document.getElementById('panel-documents');
    const lg = document.getElementById('panel-logs');
    const tw = document.getElementById('tab-warehouse');
    const td = document.getElementById('tab-documents');
    const tl = document.getElementById('tab-logs');

    wh.classList.add('hidden');
    dc.classList.add('hidden');
    lg.classList.add('hidden');

    tw.className = tw.className.replace('tab-active', 'tab-inactive');
    td.className = td.className.replace('tab-active', 'tab-inactive');
    tl.className = tl.className.replace('tab-active', 'tab-inactive');

    if (tab === 'warehouse') {
        wh.classList.remove('hidden');
        tw.className = tw.className.replace('tab-inactive', 'tab-active');
    } else if (tab === 'documents') {
        dc.classList.remove('hidden');
        td.className = td.className.replace('tab-inactive', 'tab-active');
    } else if (tab === 'logs') {
        lg.classList.remove('hidden');
        tl.className = tl.className.replace('tab-inactive', 'tab-active');
        if (allLogs.length === 0) {
            fetchLogs();
        }
        if (autoScroll) {
            scrollLogsToBottom();
        }
    }
}

async function refreshAll() {
    await Promise.all([fetchItems(), fetchDocs()]);
}
