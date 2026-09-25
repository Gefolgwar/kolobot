
// ---- Documents ----

const QUEUED_OCR_HINT = '⏳ Документ у черзі на розпізнавання. Текст з\'явиться після завершення обробки.';
const PROCESSING_OCR_HINT = '🔄 Документ у процесі обробки. Текст з\'явиться після завершення.';

function getOcrPlaceholder(status) {
    if (status === 'queued') return QUEUED_OCR_HINT;
    if (status === 'processing_ocr' || status === 'processing_emb') return PROCESSING_OCR_HINT;
    return '(Розпізнаний текст відсутній)';
}

const DOC_STATUS_BADGES = {
    queued: { label: '⏳ В черзі', cls: 'badge-queued' },
    processing_ocr: { label: '🔄 Розпізнавання', cls: 'badge-ocr' },
    processing_emb: { label: '🧠 Embeddings', cls: 'badge-emb' },
    completed: { label: '✅ Готово', cls: 'badge-import' },
    error: { label: '❌ Помилка', cls: 'badge-expense' },
};

function docStatusBadge(doc) {
    const status = doc.status || 'completed';
    const known = DOC_STATUS_BADGES[status];
    const errMsg = doc.error_message ? ` title="${esc(doc.error_message)}"` : '';
    if (known) {
        return `<span class="px-2 py-0.5 rounded-full text-[11px] font-medium whitespace-nowrap ${known.cls}"${errMsg}>${known.label}</span>`;
    }
    return `<span class="px-2 py-0.5 rounded-full text-[11px] font-medium whitespace-nowrap badge-import"${errMsg}>${esc(status)}</span>`;
}

let smartPollingTimer = null;
let hadActiveDocs = false;

function checkSmartPolling() {
    const hasActive = allDocs.some(d => d.status === 'queued' || (d.status && d.status.startsWith('processing_')));
    if (hasActive) {
        hadActiveDocs = true;
        if (!smartPollingTimer) {
            smartPollingTimer = setTimeout(smartPollTick, 3000);
        }
    } else {
        if (smartPollingTimer) {
            clearTimeout(smartPollingTimer);
            smartPollingTimer = null;
        }
        if (hadActiveDocs) {
            hadActiveDocs = false;
            fetchItems();
        }
    }
}

async function smartPollTick() {
    smartPollingTimer = null;
    await fetchDocs();
    if (currentViewingDocId) {
        const curDoc = allDocs.find(d => d.id === currentViewingDocId);
        if (curDoc && (curDoc.status === 'queued' || (curDoc.status && curDoc.status.startsWith('processing_')))) {
            loadDocumentOcr(currentViewingDocId);
        }
    }
    const openImpactRows = document.querySelectorAll('[id^="doc-impact-row-"]:not(.hidden)');
    for (const row of openImpactRows) {
        const docId = parseInt(row.id.replace('doc-impact-row-', ''));
        if (docId) {
            const d = allDocs.find(x => x.id === docId);
            if (d && (d.status === 'queued' || (d.status && d.status.startsWith('processing_')))) {
                reloadDocImpact(docId);
            }
        }
    }
    checkSmartPolling();
}

// ---- Repeat ----

// Повтор замінює дані документа, тож ручні правки буде втрачено — але питаємо
// лише тоді, коли правки справді були. Інакше повтор іде одразу.
function retryDocument(docId) {
    const d = allDocs.find(x => x.id === docId);
    if (d && d.manual_edited) {
        openRetryModal(docId, d.filename);
        return;
    }
    executeRetry(docId);
}
function openRetryModal(docId, filename) {
    document.getElementById('retry-doc-name').innerText = filename;
    document.getElementById('confirm-retry-btn').onclick = () => executeRetry(docId);
    document.getElementById('retry-modal').classList.remove('hidden');
}
function closeRetryModal() {
    document.getElementById('retry-modal').classList.add('hidden');
}
async function executeRetry(docId) {
    closeRetryModal();
    try {
        const res = await fetch('/api/warehouse/documents/' + docId + '/retry', { method: 'POST' });
        const data = await res.json();
        if (!res.ok || data.error) {
            alert(data.error || 'Помилка повтору');
            return;
        }
        await fetchDocs();
    } catch(e) {
        alert('Помилка: ' + e.message);
    }
}

async function fetchDocs() {
    try {
        const res = await fetch('/api/warehouse/documents');
        allDocs = await res.json();
        document.getElementById('docs-count').innerText = allDocs.length;
        filterDocs();
        checkSmartPolling();
    } catch(e) {
        console.error(e);
    }
}
