
// ---- Document viewing ----

let imgZoom = 1.0;
const MIN_ZOOM = 0.25;
const MAX_ZOOM = 3.0;
const ZOOM_STEP = 0.25;
let currentOcrText = '';

async function viewDocument(docId, filename, fileType, sourceRow) {
    if (fileType === 'excel') {
        let highlightRows = [];
        if (sourceRow) {
            const m = sourceRow.match(/Рядок\s+(\d+)/);
            if (m) highlightRows.push(parseInt(m[1]));
        }
        openExcelPreview(docId, filename, highlightRows);
        return;
    }
    currentViewingDocId = docId;
    const img = document.getElementById('img-modal-src');
    imgZoom = 1.0;
    img.onload = function() {
        applyImgZoom();
    };
    img.src = '/api/warehouse/documents/' + docId + '/view';
    if (img.complete && img.naturalWidth > 0) {
        applyImgZoom();
    }
    document.getElementById('img-modal-title').innerHTML = '<i class="fa-solid fa-image text-emerald-400"></i> ' + esc(filename);
    document.getElementById('img-modal').classList.remove('hidden');
    updateZoomUI();

    await loadDocumentOcr(docId);
}

async function loadDocumentOcr(docId) {
    const docTypeBadge = document.getElementById('ocr-doc-type-badge');
    const numEl = document.getElementById('ocr-meta-num');
    const dateEl = document.getElementById('ocr-meta-date');
    const opEl = document.getElementById('ocr-meta-op');
    const requestedByEl = document.getElementById('ocr-meta-requested-by');
    const requestedViaEl = document.getElementById('ocr-meta-requested-via');
    const rawEl = document.getElementById('ocr-raw-text');
    const itemsBox = document.getElementById('ocr-items-box');
    const itemsList = document.getElementById('ocr-items-list');
    const itemsCount = document.getElementById('ocr-items-count');

    currentOcrText = '';
    rawEl.textContent = 'Завантаження розпізнаного тексту...';
    numEl.textContent = '—';
    dateEl.textContent = '—';
    opEl.textContent = '—';
    if (requestedByEl) requestedByEl.textContent = '—';
    if (requestedViaEl) requestedViaEl.textContent = '—';
    docTypeBadge.innerHTML = '';
    itemsBox.classList.add('hidden');
    itemsList.innerHTML = '';

    try {
        const res = await fetch('/api/warehouse/documents/' + docId + '/ocr');
        const data = await res.json();
        if (data.error) {
            rawEl.textContent = 'Помилка: ' + data.error;
            return;
        }

        currentOcrText = data.raw_text || '';
        rawEl.textContent = currentOcrText || getOcrPlaceholder(data.status);
        numEl.textContent = data.doc_number || '—';
        dateEl.textContent = data.doc_date || '—';
        if (requestedByEl) requestedByEl.textContent = data.requested_by || '—';
        if (requestedViaEl) requestedViaEl.textContent = data.requested_via || '—';

        const dt = (data.doc_type || '').toUpperCase();
        if (dt === 'НАКЛАДНА') {
            docTypeBadge.innerHTML = '<span class="px-2 py-0.5 rounded-full text-[11px] font-medium badge-nakladna"><i class="fa-solid fa-arrow-down mr-1"></i>Накладна</span>';
            opEl.innerHTML = '<span class="text-emerald-400 font-semibold">НАКЛАДНА (Прихід)</span>';
        } else if (dt === 'ВИМОГА') {
            docTypeBadge.innerHTML = '<span class="px-2 py-0.5 rounded-full text-[11px] font-medium badge-vymoha"><i class="fa-solid fa-arrow-up mr-1"></i>Вимога</span>';
            opEl.innerHTML = '<span class="text-rose-400 font-semibold">ВИМОГА (Розхід / Видача)</span>';
        } else if (dt) {
            docTypeBadge.innerHTML = `<span class="px-2 py-0.5 rounded-full text-[11px] font-medium badge-import">${esc(dt)}</span>`;
            opEl.textContent = dt;
        } else {
            docTypeBadge.innerHTML = '';
            opEl.textContent = '—';
        }

        const items = data.impact || [];
        if (items.length > 0) {
            itemsBox.classList.remove('hidden');
            itemsCount.textContent = items.length;
            let listHtml = '';
            items.forEach((it, idx) => {
                const isInc = it.operation_type === 'income';
                const qi = fmtImpactQty(it.quantity, isInc);
                listHtml += `<div class="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/60 flex items-start justify-between gap-2 hover:border-slate-700/80 transition group">
                    <div class="min-w-0 flex-1">
                        <div class="flex items-center justify-between gap-1">
                            <span class="font-medium text-slate-200 min-w-0 break-words">${idx + 1}. ${esc(it.name)}</span>
                            <button onclick="event.stopPropagation(); openEditModal(${it.item_id}, 'name', '${esc(it.name)}', 'Найменування')" class="text-slate-500 hover:text-blue-400 p-0.5 rounded transition opacity-0 hover:opacity-100 group-hover:opacity-100 shrink-0" title="Редагувати найменування">
                                <i class="fa-solid fa-pencil text-[10px]"></i>
                            </button>
                        </div>
                        <div class="flex items-center justify-between gap-1 mt-0.5">
                            <span class="text-[10px] text-slate-500 font-mono min-w-0 break-words">${esc(it.sku || '(без SKU)')}</span>
                            <button onclick="event.stopPropagation(); openEditModal(${it.item_id}, 'sku', '${esc(it.sku)}', 'Номенклатурний номер (SKU)')" class="text-slate-500 hover:text-blue-400 p-0.5 rounded transition opacity-0 hover:opacity-100 group-hover:opacity-100 shrink-0" title="Редагувати SKU">
                                <i class="fa-solid fa-pencil text-[9px]"></i>
                            </button>
                        </div>
                    </div>
                    <div class="text-right shrink-0">
                        <div class="flex items-center justify-end gap-1 font-medium ${qi[1]}">
                            <span>${qi[0]}</span>
                            <button onclick="event.stopPropagation(); openEditModal(${it.item_id}, 'balance', '${it.quantity}', 'Залишок (кількість)')" class="text-slate-500 hover:text-blue-400 p-0.5 rounded transition opacity-0 hover:opacity-100 group-hover:opacity-100" title="Коригувати кількість/залишок">
                                <i class="fa-solid fa-pencil text-[10px]"></i>
                            </button>
                        </div>
                        <div class="flex items-center justify-end gap-1 text-[10px] text-slate-400 mt-0.5">
                            <span>${esc(it.unit || '')}</span>
                            <button onclick="event.stopPropagation(); openEditModal(${it.item_id}, 'unit', '${esc(it.unit)}', 'Одиниця виміру')" class="text-slate-500 hover:text-blue-400 p-0.5 rounded transition opacity-0 hover:opacity-100 group-hover:opacity-100" title="Редагувати одиницю виміру">
                                <i class="fa-solid fa-pencil text-[9px]"></i>
                            </button>
                        </div>
                    </div>
                </div>`;
            });
            itemsList.innerHTML = listHtml;
        }
    } catch (e) {
        rawEl.textContent = 'Помилка завантаження OCR: ' + e.message;
    }
}
