let allItems = [];
let allDocs = [];
let currentViewingDocId = null;
let activeFilter = '';

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

// ---- Warehouse Items ----

async function fetchItems() {
    try {
        const res = await fetch('/api/warehouse/items');
        allItems = await res.json();
        document.getElementById('items-count').innerText = allItems.length;
        updateFilterCounts();
        filterItems();
    } catch(e) {
        console.error(e);
    }
}

function renderItems(items) {
    const tbody = document.getElementById('items-tbody');
    document.getElementById('visible-items').innerText = items.length;
    if (items.length === 0) {
        tbody.innerHTML = '<tr><td colspan="10" class="py-12 text-center text-slate-500"><i class="fa-solid fa-boxes-stacked text-2xl mb-2 text-slate-600"></i><p>Склад порожній.</p></td></tr>';
        return;
    }
    let html = '';
    items.forEach(it => {
        const bal = it.balance || 0;
        const minBal = (it.min_balance !== null && it.min_balance !== undefined) ? Number(it.min_balance) : 0;
        const isBelowMin = minBal > 0 && bal < minBal;

        let rowClass = 'hover:bg-slate-800/40 transition cursor-pointer group';
        if (isBelowMin) {
            // клас-маркер row-low: у картковому режимі CSS картки перебиває рамку й тло,
            // тож підсвітку «нижче мінімуму» доводиться повертати окремим правилом
            rowClass = 'row-low bg-rose-950/40 hover:bg-rose-900/50 border-l-4 border-l-rose-500 transition cursor-pointer group shadow-[inset_0_0_20px_rgba(244,63,94,0.15)] text-rose-100';
        }

        const balClass = isBelowMin ? 'text-rose-400 font-bold' : (bal > 0 ? 'text-blue-400 font-bold' : (bal < 0 ? 'text-red-400 font-bold' : 'text-slate-500 font-bold'));
        const minBalClass = isBelowMin ? 'text-rose-300 font-bold' : 'text-slate-400';
        const minBalDisplay = minBal > 0 ? fmtNum(minBal) : '<span class="text-slate-600">—</span>';

        html += `
        <tr class="${rowClass}" onclick="toggleTransactions(${it.id})">
            <td class="py-4 px-3"><i id="chevron-${it.id}" class="fa-solid fa-chevron-right text-[10px] ${isBelowMin ? 'text-rose-400' : 'text-slate-500'} transition-transform"></i></td>
            <td class="py-4 px-3 font-mono text-xs text-slate-400" data-label="Ном. номер">
                <div class="flex items-center justify-between gap-1">
                    <span id="item-sku-${it.id}">${esc(it.sku)}</span>
                    <button onclick="event.stopPropagation(); openEditModal(${it.id}, 'sku', '${esc(it.sku)}', 'Номенклатурний номер (SKU)')" class="text-slate-500 hover:text-blue-400 p-1 rounded transition opacity-0 hover:opacity-100 group-hover:opacity-100" title="Редагувати номенклатурний номер">
                        <i class="fa-solid fa-pencil text-[10px]"></i>
                    </button>
                </div>
            </td>
            <td class="py-4 px-3 font-medium ${isBelowMin ? 'text-rose-100 font-semibold' : 'text-slate-200'}" data-label="Найменування">
                <div class="flex items-center justify-between gap-1">
                    <span id="item-name-${it.id}">${esc(it.name)} ${isBelowMin ? '<i class="fa-solid fa-triangle-exclamation text-rose-400 text-xs ml-1" title="Залишок менше мінімального!"></i>' : ''}</span>
                    <button onclick="event.stopPropagation(); openEditModal(${it.id}, 'name', '${esc(it.name)}', 'Найменування')" class="text-slate-500 hover:text-blue-400 p-1 rounded transition opacity-0 hover:opacity-100 group-hover:opacity-100" title="Редагувати найменування">
                        <i class="fa-solid fa-pencil text-[10px]"></i>
                    </button>
                </div>
            </td>
            <td class="py-4 px-3 text-emerald-400 font-medium" data-label="Прихід">${fmtNum(it.total_income)}</td>
            <td class="py-4 px-3 text-rose-400 font-medium" data-label="Розхід">${fmtNum(it.total_expense)}</td>
            <td class="py-4 px-3 ${balClass}" data-label="Залишок">
                <div class="flex items-center justify-between gap-1">
                    <span id="item-balance-${it.id}">${fmtNum(bal)}</span>
                    <button onclick="event.stopPropagation(); openEditModal(${it.id}, 'balance', '${bal}', 'Залишок (кількість)')" class="text-slate-500 hover:text-blue-400 p-1 rounded transition opacity-0 hover:opacity-100 group-hover:opacity-100" title="Редагувати залишок">
                        <i class="fa-solid fa-pencil text-[10px]"></i>
                    </button>
                </div>
            </td>
            <td class="py-4 px-3 ${minBalClass}" data-label="Мін. залишок">
                <div class="flex items-center justify-between gap-1">
                    <span id="item-min-balance-${it.id}">${minBalDisplay}</span>
                    <button onclick="event.stopPropagation(); openEditModal(${it.id}, 'min_balance', '${minBal > 0 ? minBal : ''}', 'Мінімальний залишок')" class="text-slate-500 hover:text-blue-400 p-1 rounded transition opacity-0 hover:opacity-100 group-hover:opacity-100" title="Встановити мінімальний залишок">
                        <i class="fa-solid fa-pencil text-[10px]"></i>
                    </button>
                </div>
            </td>
            <td class="py-4 px-3 text-slate-400" data-label="Од.виміру">
                <div class="flex items-center justify-between gap-1">
                    <span id="item-unit-${it.id}">${esc(it.unit)}</span>
                    <button onclick="event.stopPropagation(); openEditModal(${it.id}, 'unit', '${esc(it.unit)}', 'Одиниця виміру')" class="text-slate-500 hover:text-blue-400 p-1 rounded transition opacity-0 hover:opacity-100 group-hover:opacity-100" title="Редагувати одиницю виміру">
                        <i class="fa-solid fa-pencil text-[10px]"></i>
                    </button>
                </div>
            </td>
            <td class="py-4 px-3 text-slate-300" data-label="Постачальник">
                <div class="flex items-center justify-between gap-1">
                    <span id="item-supplier-${it.id}">${esc(it.supplier)}</span>
                    <button onclick="event.stopPropagation(); openEditModal(${it.id}, 'supplier', '${esc(it.supplier)}', 'Постачальник')" class="text-slate-500 hover:text-blue-400 p-1 rounded transition opacity-0 hover:opacity-100 group-hover:opacity-100" title="Редагувати постачальника">
                        <i class="fa-solid fa-pencil text-[10px]"></i>
                    </button>
                </div>
            </td>
            <td class="py-4 px-3 text-xs text-slate-400" data-label="Примітки">
                <div class="flex items-center justify-between gap-1">
                    <span id="item-notes-${it.id}" class="min-w-0 break-words">${esc(it.notes)}</span>
                    <button onclick="event.stopPropagation(); openEditModal(${it.id}, 'notes', '${esc(it.notes)}', 'Примітки')" class="text-slate-500 hover:text-blue-400 p-1 rounded transition opacity-0 hover:opacity-100 group-hover:opacity-100 shrink-0" title="Редагувати примітки">
                        <i class="fa-solid fa-pencil text-[10px]"></i>
                    </button>
                </div>
            </td>
        </tr>
        <tr id="tx-row-${it.id}" class="hidden">
            <td colspan="10" class="p-0">
                <div class="expand-row px-8 py-3 border-t border-slate-800/40">
                    <div id="tx-content-${it.id}" class="text-xs text-slate-400">Завантаження...</div>
                </div>
            </td>
        </tr>`;
    });
    tbody.innerHTML = html;
}

// ---- Item Edit Modal Logic ----

let currentEditItemId = null;
let currentEditField = null;

// ---- Ручне дозаповнення полів документа (#31) ----
// Пʼять полів розпізнавання, які користувач править у розгорнутій картці документа.
// Правка йде тим самим модальним вікном, що й позиції складу, але іншим endpointʼом.
const DOC_FIELD_LABELS = {
    doc_type: 'Тип документу',
    doc_number: '№ документа',
    doc_date: 'Дата документа',
    requested_by: 'Затребував',
    requested_via: 'Через кого'
};
let currentEditDocId = null;
let currentEditDocField = null;

function openDocFieldModal(docId, field) {
    const doc = allDocs.find(d => d.id === docId);
    if (!doc) return;
    currentEditItemId = null;
    currentEditField = null;
    currentEditDocId = docId;
    currentEditDocField = field;

    const label = DOC_FIELD_LABELS[field] || field;
    const currentVal = doc[field] || '';
    const isDocType = (field === 'doc_type');
    document.getElementById('edit-modal-title').textContent = 'Документ: ' + label;
    document.getElementById('edit-field-label').textContent = isDocType
        ? 'Тип документа:'
        : 'Нове значення (' + label + '):';
    document.getElementById('edit-current-value').textContent = currentVal !== '' ? currentVal : '(не встановлено)';

    const inputVal = document.getElementById('edit-new-value');
    const selectVal = document.getElementById('edit-doc-type');
    inputVal.classList.toggle('hidden', isDocType);
    selectVal.classList.toggle('hidden', !isDocType);
    if (isDocType) {
        // порожнє значення не має жодного з двох пунктів — користувач обирає тип явно
        selectVal.value = currentVal;
    } else {
        inputVal.type = 'text';
        inputVal.removeAttribute('step');
        inputVal.removeAttribute('min');
        inputVal.placeholder = 'Введіть нове значення...';
        inputVal.value = currentVal;
    }
    document.getElementById('edit-comment').value = '';
    const errEl = document.getElementById('edit-error');
    errEl.classList.add('hidden');
    errEl.textContent = '';
    document.getElementById('edit-modal').classList.remove('hidden');
    if (!isDocType) setTimeout(() => { inputVal.focus(); inputVal.select(); }, 50);
}

async function submitDocField() {
    const docId = currentEditDocId;
    const field = currentEditDocField;
    const saveBtn = document.getElementById('edit-save-btn');
    const errEl = document.getElementById('edit-error');
    const isDocType = (field === 'doc_type');
    const newVal = isDocType
        ? document.getElementById('edit-doc-type').value
        : document.getElementById('edit-new-value').value;
    const comment = document.getElementById('edit-comment').value;

    errEl.classList.add('hidden');
    if (isDocType && !newVal) {
        errEl.textContent = 'Оберіть тип документа зі списку';
        errEl.classList.remove('hidden');
        return;
    }
    const impactRow = document.getElementById('doc-impact-row-' + docId);
    const wasOpen = !!impactRow && !impactRow.classList.contains('hidden');

    saveBtn.disabled = true;
    saveBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> <span>Збереження...</span>';
    try {
        const res = await fetch('/api/warehouse/documents/' + docId + '/edit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ field: field, value: newVal, comment: comment })
        });
        const data = await res.json();
        if (!res.ok || data.error) {
            errEl.textContent = data.error || 'Помилка збереження';
            errEl.classList.remove('hidden');
            return;
        }

        closeEditModal();
        // Правка номера, дати чи типу дістає транзакції документа, а дозаповнення
        // останнього поля вводить документ в облік — тож оновлюємо обидві вкладки.
        // Перемальовування таблиці згортає картку, тому розгортаємо її назад.
        await refreshAll();
        if (wasOpen) await toggleDocImpact(docId);
    } catch(e) {
        errEl.textContent = 'Помилка: ' + e.message;
        errEl.classList.remove('hidden');
    } finally {
        saveBtn.disabled = false;
        saveBtn.innerHTML = '<i class="fa-solid fa-check"></i> <span>Зберегти</span>';
    }
}

function openEditModal(itemId, field, currentVal, fieldLabel) {
    currentEditDocId = null;
    currentEditDocField = null;
    document.getElementById('edit-doc-type').classList.add('hidden');
    document.getElementById('edit-new-value').classList.remove('hidden');
    currentEditItemId = itemId;
    currentEditField = field;
    const isQty = (field === 'balance' || field === 'quantity');
    const isMinBal = (field === 'min_balance');
    if (isQty) {
        document.getElementById('edit-modal-title').textContent = 'Коригування залишку';
        document.getElementById('edit-field-label').textContent = 'Новий залишок (цільова кількість):';
    } else if (isMinBal) {
        document.getElementById('edit-modal-title').textContent = 'Мінімальний залишок';
        document.getElementById('edit-field-label').textContent = 'Мінімальний залишок на складі:';
    } else {
        document.getElementById('edit-modal-title').textContent = 'Редагувати: ' + (fieldLabel || field);
        document.getElementById('edit-field-label').textContent = 'Нове значення (' + (fieldLabel || field) + '):';
    }
    document.getElementById('edit-current-value').textContent = (currentVal !== '' && currentVal !== null && currentVal !== undefined) ? currentVal : '(не встановлено)';
    const inputVal = document.getElementById('edit-new-value');
    if (isQty || isMinBal) {
        inputVal.type = 'number';
        inputVal.step = 'any';
        if (isMinBal) {
            inputVal.min = '0';
            inputVal.placeholder = 'Введіть мінімальний залишок (напр. 10)...';
        } else {
            inputVal.removeAttribute('min');
            inputVal.placeholder = 'Введіть новий залишок...';
        }
    } else {
        inputVal.type = 'text';
        inputVal.removeAttribute('step');
        inputVal.removeAttribute('min');
        inputVal.placeholder = 'Введіть нове значення...';
    }
    inputVal.value = (currentVal !== null && currentVal !== undefined) ? currentVal : '';
    document.getElementById('edit-comment').value = '';
    const errEl = document.getElementById('edit-error');
    errEl.classList.add('hidden');
    errEl.textContent = '';
    document.getElementById('edit-modal').classList.remove('hidden');
    setTimeout(() => { inputVal.focus(); inputVal.select(); }, 50);
}

function closeEditModal() {
    currentEditItemId = null;
    currentEditField = null;
    currentEditDocId = null;
    currentEditDocField = null;
    document.getElementById('edit-modal').classList.add('hidden');
}

async function submitEditField() {
    if (currentEditDocId) return submitDocField();
    if (!currentEditItemId || !currentEditField) return;
    const saveBtn = document.getElementById('edit-save-btn');
    const errEl = document.getElementById('edit-error');
    const newVal = document.getElementById('edit-new-value').value;
    const comment = document.getElementById('edit-comment').value;

    errEl.classList.add('hidden');
    saveBtn.disabled = true;
    saveBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> <span>Збереження...</span>';

    try {
        const res = await fetch('/api/warehouse/items/' + currentEditItemId + '/edit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                field: currentEditField,
                value: newVal,
                comment: comment
            })
        });
        const data = await res.json();
        if (!res.ok || data.error) {
            errEl.textContent = data.error || 'Помилка збереження';
            errEl.classList.remove('hidden');
            saveBtn.disabled = false;
            saveBtn.innerHTML = '<i class="fa-solid fa-check"></i> <span>Зберегти</span>';
            return;
        }

        // Update local item cache
        const itemIdx = allItems.findIndex(it => it.id === currentEditItemId);
        if (itemIdx !== -1) {
            if (data.item) {
                allItems[itemIdx] = { ...allItems[itemIdx], ...data.item };
            }
            if (data.target_quantity !== undefined) {
                allItems[itemIdx].balance = data.target_quantity;
            }
            if (data.operation_type === 'income' && data.delta) {
                allItems[itemIdx].total_income = (allItems[itemIdx].total_income || 0) + data.delta;
            } else if (data.operation_type === 'expense' && data.delta) {
                allItems[itemIdx].total_expense = (allItems[itemIdx].total_expense || 0) + Math.abs(data.delta);
            }
        }

        // Re-render filtered items immediately
        updateFilterCounts();
        filterItems();

        // If transaction row is currently expanded, reload transactions
        const txRow = document.getElementById('tx-row-' + currentEditItemId);
        if (txRow && !txRow.classList.contains('hidden')) {
            await reloadTransactions(currentEditItemId);
        }

        // If OCR preview modal is open, reload OCR items dynamically
        const imgModal = document.getElementById('img-modal');
        if (imgModal && !imgModal.classList.contains('hidden') && currentViewingDocId) {
            await loadDocumentOcr(currentViewingDocId);
        }

        // Reload any currently expanded document impact views
        const openImpactRows = document.querySelectorAll('[id^="doc-impact-row-"]:not(.hidden)');
        for (const row of openImpactRows) {
            const docId = parseInt(row.id.replace('doc-impact-row-', ''));
            if (docId) {
                await reloadDocImpact(docId);
            }
        }

        closeEditModal();
    } catch(e) {
        errEl.textContent = 'Помилка: ' + e.message;
        errEl.classList.remove('hidden');
    } finally {
        saveBtn.disabled = false;
        saveBtn.innerHTML = '<i class="fa-solid fa-check"></i> <span>Зберегти</span>';
    }
}

async function reloadTransactions(itemId) {
    const content = document.getElementById('tx-content-' + itemId);
    if (!content) return;
    try {
        const res = await fetch('/api/warehouse/items/' + itemId + '/transactions');
        const txs = await res.json();
        const it = allItems.find(x => x.id === itemId);
        const curBal = it ? (it.balance || 0) : 0;
        const curUnit = it ? (it.unit || '') : '';
        const balColor = curBal > 0 ? 'text-blue-400' : (curBal < 0 ? 'text-red-400' : 'text-slate-400');

        let headerBar = `<div class="flex items-center justify-between pb-2 mb-2 border-b border-slate-800/60">
            <div class="text-xs text-slate-300 flex items-center gap-2">
                <span class="text-slate-400">Поточний залишок:</span>
                <span class="font-bold ${balColor}">${fmtNum(curBal)} ${esc(curUnit)}</span>
            </div>
        </div>`;

        if (txs.length === 0) {
            content.innerHTML = headerBar + '<p class="text-slate-500 py-2">Немає транзакцій.</p>';
            return;
        }
        let h = headerBar + '<table class="w-full card-table"><thead><tr class="text-slate-500 text-[11px] uppercase">' +
            '<th class="py-1 pr-3 text-left">Дата</th><th class="py-1 pr-3 text-left">Тип</th>' +
            '<th class="py-1 pr-3 text-left">Тип док.</th>' +
            '<th class="py-1 pr-3 text-right">Кількість</th><th class="py-1 pr-3 text-left">№ накл.</th>' +
            '<th class="py-1 pr-3 text-right">Залишок</th><th class="py-1 pr-3 text-left">Документ</th>' +
            '<th class="py-1 pr-3 text-left">Затребував</th>' +
            '<th class="py-1 pr-3 text-left">Через кого</th>' +
            '<th class="py-1 pr-3 text-left">Джерело</th>' +
            '</tr></thead><tbody>';
        txs.forEach(tx => {
            const isManual = tx.file_type === 'manual' || tx.doc_type === 'РУЧНЕ_КОРИГУВАННЯ';
            // Неврахований рядок (#30): прапорець рахує бекенд тим самим правилом обліку,
            // що й вкладка «Документи» (#29), — фронтенд його не повторює. Такий рядок
            // лишається в історії, але числа в «Залишку» не показує: інакше на екрані
            // стояли б два різні залишки позиції.
            const isUnaccounted = tx.accounted === false;
            const missingFields = tx.missing_fields || [];
            const unaccountedMark = isUnaccounted
                ? `<span class="text-amber-400 ml-1 align-middle" title="Документ не в обліку. Не розпізнано: ${esc(missingFields.join(', '))}"><i class="fa-solid fa-triangle-exclamation"></i></span>`
                : '';
            const isInc = tx.operation_type === 'income';
            let badge = isInc ? 'badge-income' : 'badge-expense';
            let label = isInc ? 'Прихід' : 'Розхід';
            if (isManual) {
                badge = 'badge-vymoha';
                label = 'Коригування';
            }
            const date = tx.doc_date || formatTs(tx.created_at);
            const docType = tx.doc_type || '';
            let docTypeBadge = '';
            if (docType === 'НАКЛАДНА') {
                docTypeBadge = '<span class="px-2 py-0.5 rounded-full text-[11px] font-medium badge-nakladna">Накл.</span>';
            } else if (docType === 'ВИМОГА') {
                docTypeBadge = '<span class="px-2 py-0.5 rounded-full text-[11px] font-medium badge-vymoha">Вимога</span>';
            } else if (docType === 'РУЧНЕ_КОРИГУВАННЯ' || isManual) {
                docTypeBadge = '<span class="px-2 py-0.5 rounded-full text-[11px] font-medium" style="background: rgba(245, 158, 11, 0.15); color: #fbbf24;">Коригування</span>';
            } else if (docType) {
                docTypeBadge = `<span class="text-slate-400 text-[11px]">${esc(docType)}</span>`;
            }
            const srcRow = tx.source_row || '';
            const requestedBy = tx.requested_by || '';
            const requestedVia = tx.requested_via || '';
            let qtyDisplay = '';
            if (tx.quantity === 0) {
                qtyDisplay = '<span class="text-slate-400 font-medium">0</span>';
            } else {
                const sign = isInc ? '+' : '-';
                const color = isInc ? 'text-emerald-400' : 'text-rose-400';
                qtyDisplay = `<span class="${color} font-medium">${sign}${fmtNum(tx.quantity)}</span>`;
            }
            let docDisplay = '';
            if (isManual) {
                docDisplay = `<span class="text-amber-400/90 text-xs font-medium" title="Ручне редагування"><i class="fa-solid fa-user-pen mr-1"></i>${esc(tx.filename)}</span>`;
            } else {
                const fileIcon = getFileIcon(tx.file_type);
                docDisplay = `<button onclick="event.stopPropagation(); viewDocument(${tx.document_id}, '${esc(tx.filename)}', '${tx.file_type}', '${esc(tx.source_row)}')"
                    class="text-slate-400 hover:text-blue-400 transition">
                    ${fileIcon} <span class="ml-1">${esc(tx.filename)}</span>
                </button>${unaccountedMark}${manualEditMark(tx.manual_edited)}`;
            }
            h += `<tr class="border-t border-slate-800/30${isUnaccounted ? ' opacity-60' : ''}">
                <td class="py-2 pr-3 text-slate-300" data-label="Дата">${esc(date)}</td>
                <td class="py-2 pr-3" data-label="Тип"><span class="px-2 py-0.5 rounded-full text-[11px] font-medium ${badge}" ${isManual ? 'style="background: rgba(245, 158, 11, 0.15); color: #fbbf24;"' : ''}>${label}</span></td>
                <td class="py-2 pr-3" data-label="Тип док.">${docTypeBadge}</td>
                <td class="py-2 pr-3 text-right font-medium" data-label="Кількість">${qtyDisplay}</td>
                <td class="py-2 pr-3 text-slate-300 font-mono" data-label="№ накл.">${esc(tx.doc_number)}</td>
                <td class="py-2 pr-3 text-right text-blue-400 font-medium" data-label="Залишок">${isUnaccounted ? '<span class="text-slate-500" title="Документ не в обліку — кількість не входить у залишок">—</span>' : fmtNum(tx.running_balance)}</td>
                <td class="py-2 pr-3 break-words" data-label="Документ">${docDisplay}</td>
                <td class="py-2 pr-3 text-slate-300 break-words" data-label="Затребував">${fmtRequestedBy(requestedBy)}</td>
                <td class="py-2 pr-3 text-slate-300 break-words" data-label="Через кого">${fmtRequestedBy(requestedVia)}</td>
                <td class="py-2 pr-3 text-slate-500 text-[11px] break-words" data-label="Джерело">${esc(srcRow)}</td>
            </tr>`;
        });
        h += '</tbody></table>';
        content.innerHTML = h;
    } catch(e) {
        content.innerHTML = '<p class="text-red-400">Помилка завантаження транзакцій.</p>';
    }
}

async function toggleTransactions(itemId) {
    const row = document.getElementById('tx-row-' + itemId);
    const chevron = document.getElementById('chevron-' + itemId);
    if (!row.classList.contains('hidden')) {
        row.classList.add('hidden');
        chevron.style.transform = '';
        return;
    }
    row.classList.remove('hidden');
    chevron.style.transform = 'rotate(90deg)';

    const content = document.getElementById('tx-content-' + itemId);
    content.innerHTML = '<div class="py-2 text-slate-500"><i class="fa-solid fa-spinner fa-spin mr-1.5"></i>Завантаження...</div>';
    await reloadTransactions(itemId);
}

function filterItems() {
    const q = document.getElementById('search-items').value.toLowerCase().trim();
    let filtered = allItems;

    if (activeFilter === 'below-min') {
        filtered = filtered.filter(it => {
            const minBal = (it.min_balance !== null && it.min_balance !== undefined) ? Number(it.min_balance) : 0;
            return minBal > 0 && (it.balance || 0) < minBal;
        });
    } else if (activeFilter === 'negative') {
        filtered = filtered.filter(it => (it.balance || 0) < 0);
    } else if (activeFilter === 'no-docs') {
        filtered = filtered.filter(it => (it.doc_count || 0) === 0);
    } else if (activeFilter === 'dup-names') {
        const dupNames = getDuplicateNames();
        filtered = filtered.filter(it => dupNames.has((it.name || '').trim().toLowerCase()));
    } else if (activeFilter === 'zeros') {
        filtered = filtered.filter(it => (it.total_income || 0) === 0 && (it.total_expense || 0) === 0 && (it.balance || 0) === 0);
    }

    if (q) {
        filtered = filtered.filter(it =>
            (it.name || '').toLowerCase().includes(q) ||
            (it.sku || '').toLowerCase().includes(q) ||
            (it.supplier || '').toLowerCase().includes(q) ||
            (it.notes || '').toLowerCase().includes(q) ||
            (it.unit || '').toLowerCase().includes(q)
        );
    }
    renderItems(filtered);
}

function getDuplicateNames() {
    const nameSkus = {};
    allItems.forEach(it => {
        const name = (it.name || '').trim().toLowerCase();
        if (!name) return;
        if (!nameSkus[name]) nameSkus[name] = new Set();
        nameSkus[name].add((it.sku || '').trim());
    });
    const dupNames = new Set();
    Object.keys(nameSkus).forEach(name => {
        if (nameSkus[name].size > 1) dupNames.add(name);
    });
    return dupNames;
}

function setFilter(filter) {
    activeFilter = (activeFilter === filter) ? '' : filter;
    updateFilterUI();
    filterItems();
}

function updateFilterUI() {
    ['below-min', 'negative', 'no-docs', 'dup-names', 'zeros'].forEach(f => {
        const btn = document.getElementById('filter-' + f);
        if (!btn) return;
        if (f === activeFilter) {
            btn.classList.add('bg-blue-600/30', 'text-blue-300', 'border-blue-500/50');
            btn.classList.remove('text-slate-400', 'border-slate-700/60', 'bg-slate-900/50');
        } else {
            btn.classList.remove('bg-blue-600/30', 'text-blue-300', 'border-blue-500/50');
            btn.classList.add('text-slate-400', 'border-slate-700/60', 'bg-slate-900/50');
        }
    });
}

function updateFilterCounts() {
    const belowMinCount = allItems.filter(it => {
        const minBal = (it.min_balance !== null && it.min_balance !== undefined) ? Number(it.min_balance) : 0;
        return minBal > 0 && (it.balance || 0) < minBal;
    }).length;
    const belowMinEl = document.getElementById('filter-below-min-count');
    if (belowMinEl) belowMinEl.textContent = belowMinCount;

    const negCount = allItems.filter(it => (it.balance || 0) < 0).length;
    document.getElementById('filter-negative-count').textContent = negCount;

    const noDocCount = allItems.filter(it => (it.doc_count || 0) === 0).length;
    document.getElementById('filter-no-docs-count').textContent = noDocCount;

    const dupNames = getDuplicateNames();
    let dupCount = 0;
    allItems.forEach(it => {
        if (dupNames.has((it.name || '').trim().toLowerCase())) dupCount++;
    });
    document.getElementById('filter-dup-names-count').textContent = dupCount;

    const zeroCount = allItems.filter(it => (it.total_income || 0) === 0 && (it.total_expense || 0) === 0 && (it.balance || 0) === 0).length;
    document.getElementById('filter-zeros-count').textContent = zeroCount;
}

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

// ---- Сортування таблиці документів (#25) ----
// Порядок рядків у SQL лишається незмінним: сортування переставляє лише той
// список, який сторінка вже завантажила, і тримає свій стан у памʼяті сторінки.
// Тут живуть і спільні помічники порівняння: нормалізацію номера документа
// використовує й підсвічування дублів (#26), другої такої функції немає.

// Стан сортування живе поряд зі станом фільтра й застосовується при кожному
// рендері, тож переживає автооновлення і скидається лише перезавантаженням сторінки.
let docSort = { key: null, dir: null };
// Останній список, який показала таблиця (з урахуванням пошуку й фільтрів).
let lastRenderedDocs = [];

function comparePlainText(a, b) {
    return String(a == null ? '' : a).localeCompare(String(b == null ? '' : b), 'uk');
}

// Числове подання значення колонки: 10 → 10, «№ 0002143» → 2143, «—» → NaN.
function numericValue(v) {
    if (v === null || v === undefined) return NaN;
    if (typeof v === 'number') return v;
    const m = String(v).replace(/\s/g, '').match(/-?\d+(?:[.,]\d+)?/);
    return m ? Number(m[0].replace(',', '.')) : NaN;
}

// Порівняння номерів і кількостей як чисел: «10» іде після «9», а не перед ним.
// Якщо число не читається з обох боків — порівнюємо як текст.
function compareNumericValues(a, b) {
    const na = numericValue(a);
    const nb = numericValue(b);
    if (!isNaN(na) && !isNaN(nb)) return na < nb ? -1 : (na > nb ? 1 : 0);
    return comparePlainText(a, b);
}

// Ключ порівняння номера документа — один на сортування й на пошук дублів (#26).
// «№ 1234», «N1234» і «1234» з різними пробілами та регістром — той самий номер.
// Провідні нулі не прибираються: «0002143» і «2143» — різні номери.
function normalizeDocNumber(v) {
    return String(v == null ? '' : v).replace(/[\s№n]/gi, '').toLowerCase();
}

// Номер документа сортується за тим самим ключем: «10» після «9».
function compareDocNumbers(a, b) {
    return compareNumericValues(normalizeDocNumber(a), normalizeDocNumber(b));
}

// Життєвий цикл документа — саме цей порядок, а не алфавіт.
const DOC_STATUS_ORDER = ['queued', 'processing_ocr', 'processing_emb', 'completed', 'error'];

function compareDocStatus(a, b) {
    const ia = DOC_STATUS_ORDER.indexOf(a);
    const ib = DOC_STATUS_ORDER.indexOf(b);
    if (ia === ib) return comparePlainText(a, b);
    return (ia === -1 ? DOC_STATUS_ORDER.length : ia) - (ib === -1 ? DOC_STATUS_ORDER.length : ib);
}

// Девʼять колонок, які сортуються, і спосіб порівняння кожної.
// Превʼю, розгортання й дії лишаються не сортованими.
const DOC_SORT_COLUMNS = {
    filename:          { get: d => d.filename,              compare: comparePlainText },
    file_type:         { get: d => d.file_type,             compare: comparePlainText },
    doc_type:          { get: d => d.doc_type,              compare: comparePlainText },
    status:            { get: d => d.status || 'completed', compare: compareDocStatus },
    uploaded_at:       { get: d => d.uploaded_at,           compare: compareNumericValues },
    doc_number:        { get: d => d.doc_number,            compare: compareDocNumbers },
    requested_by:      { get: d => d.requested_by,          compare: comparePlainText },
    requested_via:     { get: d => d.requested_via,         compare: comparePlainText },
    transaction_count: { get: d => d.transaction_count,     compare: compareNumericValues },
};

// Сортує переданий список — тобто результат пошуку й фільтрів, а не весь allDocs.
// Порожнє значення колонки завжди опиняється в кінці, хоч за зростанням, хоч за спаданням.
function applyDocSort(docs) {
    const col = docSort.key ? DOC_SORT_COLUMNS[docSort.key] : null;
    if (!col) return docs;
    const dir = docSort.dir === 'desc' ? -1 : 1;
    const filled = [];
    const empty = [];
    docs.forEach(d => {
        const v = col.get(d);
        (v === null || v === undefined || String(v).trim() === '' ? empty : filled).push(d);
    });
    filled.sort((a, b) => col.compare(col.get(a), col.get(b)) * dir);
    return filled.concat(empty);
}

// Клік по заголовку: зростання → спадання → типовий порядок. Сортується одна колонка за раз.
function toggleDocSort(key) {
    if (docSort.key !== key) {
        docSort = { key: key, dir: 'asc' };
    } else if (docSort.dir === 'asc') {
        docSort = { key: key, dir: 'desc' };
    } else {
        docSort = { key: null, dir: null };
    }
    renderDocs(lastRenderedDocs);
    renderDocSortIndicators();
}

// Показує, яка колонка активна і в якому напрямку: стрілка вгору/вниз у її заголовку.
function renderDocSortIndicators() {
    Object.keys(DOC_SORT_COLUMNS).forEach(key => {
        const icon = document.getElementById('doc-sort-icon-' + key);
        const th = document.getElementById('doc-sort-' + key);
        if (!icon) return;
        const active = docSort.key === key;
        icon.className = active && docSort.dir === 'desc'
            ? 'fa-solid fa-sort-down text-sky-400'
            : (active ? 'fa-solid fa-sort-up text-sky-400' : 'fa-solid fa-sort text-slate-600');
        if (th) th.style.color = active ? '#38bdf8' : '';
    });
}
// ---- Кінець сортування таблиці документів (#25) ----

// ---- Підсвічування дублів «№ документа» (#26) ----
// Дублі рахуються по всьому завантаженому списку, а не по відфільтрованому,
// і не залежать від сортування: ключ той самий, що й у сортуванні.
function docNumberTwinCounts() {
    const counts = {};
    allDocs.forEach(d => {
        const key = normalizeDocNumber(d.doc_number);
        if (!key) return;  // порожній номер дублем не вважається
        counts[key] = (counts[key] || 0) + 1;
    });
    return counts;
}
// ---- Кінець підсвічування дублів (#26) ----

// ---- Мітка «Не в обліку» та її фільтр (#29) ----
// Перелік не розпізнаних полів приходить із бекенду (missing_fields) — його рахує
// та сама missing_doc_fields(), що й SQL-правило обліку. Фронтенд його не повторює,
// тож excel і ручний системний документ мітки не отримують.
// Стан фільтра живе поряд зі станом сортування і застосовується при кожному рендері,
// тож переживає автооновлення. Порядок як у батьківській задачі: спершу фільтр, потім сортування.
let docFilter = '';

function isDocUnaccounted(doc) {
    return (doc.missing_fields || []).length > 0;
}

function setDocFilter(filter) {
    docFilter = (docFilter === filter) ? '' : filter;
    updateDocFilterUI();
    filterDocs();
}

function updateDocFilterUI() {
    const btn = document.getElementById('filter-not-accounted');
    if (!btn) return;
    if (docFilter === 'not-accounted') {
        btn.classList.add('bg-blue-600/30', 'text-blue-300', 'border-blue-500/50');
        btn.classList.remove('text-slate-400', 'border-slate-700/60', 'bg-slate-900/50');
    } else {
        btn.classList.remove('bg-blue-600/30', 'text-blue-300', 'border-blue-500/50');
        btn.classList.add('text-slate-400', 'border-slate-700/60', 'bg-slate-900/50');
    }
}

function updateDocFilterCounts() {
    const el = document.getElementById('filter-not-accounted-count');
    if (!el) return;
    el.textContent = allDocs.filter(isDocUnaccounted).length;
}

// Фільтр іде по всьому завантаженому списку, а сортування — вже по його результату.
function filterDocs() {
    updateDocFilterCounts();
    renderDocs(docFilter === 'not-accounted' ? allDocs.filter(isDocUnaccounted) : allDocs);
}
// ---- Кінець фільтра «Не в обліку» (#29) ----

// ---- Підказка до позначок таблиці ----
// Позначки в підказці — ті самі, що й у рядках: розмітку будують ті самі функції, лише
// з прикладовими даними. Тому підказка не може розійтися з таблицею, а «Приклад» цитує
// ту саму підказку, яку користувач побачить при наведенні на позначку.
function renderDocLegend() {
    const body = document.getElementById('doc-legend-body');
    if (!body) return;
    const tooltip = mark => mark.split('title="')[1].split('"')[0];
    const row = (mark, label, text, example) => `
        <div class="flex gap-3 py-2">
            <div class="w-16 shrink-0 text-center leading-5">${mark}</div>
            <div class="leading-5">
                <span class="text-slate-200 font-semibold">${label}</span><span class="text-slate-400"> — ${text}</span>
                <div class="text-slate-500 mt-0.5">Приклад: ${example}</div>
            </div>
        </div>`;
    const unaccounted = docUnaccountedMark(['Дата документа']);
    const edited = manualEditMark(true);
    const twin = docNumberTwinMark(2);
    body.innerHTML =
        row(unaccounted, 'Не в обліку', 'не розпізнано обовʼязкові поля, тож документ не входить у залишки',
            'документ без дати — «' + tooltip(unaccounted) + '»') +
        row(edited, 'Ручне редагування', 'поля документа заповнив або виправив користувач, а не розпізнавання',
            'ви вписали номер вручну — «' + tooltip(edited) + '»') +
        row('<span class="doc-dup px-1.5 py-0.5 rounded font-mono">№ 7</span>' + twin, 'Дубль номера',
            'такий самий номер уже є в інших документах',
            'клітинка «№ документа» — «' + tooltip(twin) + '»');
}
// ---- Кінець підказки до позначок таблиці ----

function renderDocs(docs) {
    lastRenderedDocs = docs;
    const sorted = applyDocSort(docs);
    const twinCounts = docNumberTwinCounts();
    const tbody = document.getElementById('docs-tbody');
    if (sorted.length === 0) {
        tbody.innerHTML = '<tr><td colspan="12" class="py-12 text-center text-slate-500"><p>Документів немає.</p></td></tr>';
        return;
    }
    let html = '';
    sorted.forEach(doc => {
        const icon = getFileIcon(doc.file_type);
        const typeLabel = doc.file_type === 'excel' ? 'Excel' : (doc.file_type === 'photo' ? 'Фото' : 'PDF');
        const date = formatTs(doc.uploaded_at);
        const docType = doc.doc_type || '';
        const requestedBy = doc.requested_by || '';
        const requestedVia = doc.requested_via || '';
        // Дубль номера: підсвічується сама клітинка, а не рядок
        const docNumberKey = normalizeDocNumber(doc.doc_number);
        const twinCount = docNumberKey ? (twinCounts[docNumberKey] || 1) - 1 : 0;
        const docNumberCls = twinCount ? 'doc-dup' : 'text-slate-300';
        // Мітка «не в обліку»: перелік не розпізнаних полів дає бекенд, клітинка лише показує його
        const missingFields = doc.missing_fields || [];
        let docTypeBadge = '';
        if (docType === 'НАКЛАДНА') {
            docTypeBadge = '<span class="px-2 py-0.5 rounded-full text-[11px] font-medium badge-nakladna"><i class="fa-solid fa-arrow-down mr-1"></i>Накладна</span>';
        } else if (docType === 'ВИМОГА') {
            docTypeBadge = '<span class="px-2 py-0.5 rounded-full text-[11px] font-medium badge-vymoha"><i class="fa-solid fa-arrow-up mr-1"></i>Вимога</span>';
        } else if (docType) {
            docTypeBadge = `<span class="px-2 py-0.5 rounded-full text-[11px] font-medium badge-import">${esc(docType)}</span>`;
        } else {
            docTypeBadge = '<span class="text-slate-600 text-xs">—</span>';
        }
        let previewBtn = '';
        if (doc.file_type === 'excel') {
            previewBtn = `<button onclick="event.stopPropagation(); viewDocument(${doc.id}, '${esc(doc.filename)}', '${doc.file_type}')" class="w-10 h-10 flex items-center justify-center rounded-lg bg-green-500/10 text-green-500 hover:bg-green-500/20 border border-green-500/20 transition" title="Перегляд Excel">
                <i class="fa-solid fa-file-excel text-xl"></i>
            </button>`;
        } else if (doc.file_type === 'pdf') {
            previewBtn = `<button onclick="event.stopPropagation(); viewDocument(${doc.id}, '${esc(doc.filename)}', '${doc.file_type}')" class="w-10 h-10 flex items-center justify-center rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20 border border-red-500/20 transition" title="Перегляд PDF">
                <i class="fa-solid fa-file-pdf text-xl"></i>
            </button>`;
        } else {
            previewBtn = `<button onclick="event.stopPropagation(); viewDocument(${doc.id}, '${esc(doc.filename)}', '${doc.file_type}')" class="group relative block w-10 h-10 rounded-lg overflow-hidden border border-slate-700 bg-slate-900 hover:border-blue-500 transition shadow" title="Переглянути фото та текст OCR">
                <img src="/api/warehouse/documents/${doc.id}/view" alt="Превʼю" class="w-full h-full object-cover group-hover:scale-110 transition duration-200" onerror="this.outerHTML='<div class=\\'w-full h-full flex items-center justify-center text-emerald-400\\'><i class=\\'fa-solid fa-image text-lg\\'></i></div>'">
            </button>`;
        }

        let retryBtn = '';
        if (doc.status === 'error') {
            retryBtn = `<button onclick="event.stopPropagation(); retryDocument(${doc.id})" class="p-2 text-amber-400 hover:text-amber-300 hover:bg-amber-500/10 rounded-lg transition mr-1" title="Повторити">
                <i class="fa-solid fa-rotate-right"></i>
            </button>`;
        }

        html += `
        <tr class="hover:bg-slate-800/40 transition cursor-pointer" onclick="toggleDocImpact(${doc.id})">
            <td class="py-4 px-3 whitespace-nowrap"><i id="doc-chevron-${doc.id}" class="fa-solid fa-chevron-right text-[10px] text-slate-500 transition-transform"></i>${docUnaccountedMark(missingFields)}${manualEditMark(doc.manual_edited)}</td>
            <td class="py-4 px-3" data-label="Превʼю">${previewBtn}</td>
            <td class="py-4 px-3 font-medium text-slate-200 break-words" data-label="Файл">${esc(doc.filename)}</td>
            <td class="py-4 px-3" data-label="Тип"><span class="px-2 py-0.5 rounded-full text-[11px] font-medium badge-import">${typeLabel}</span></td>
            <td class="py-4 px-3" data-label="Тип документу">${docTypeBadge}</td>
            <td class="py-4 px-3" data-label="Статус">${docStatusBadge(doc)}</td>
            <td class="py-4 px-3 text-slate-300" data-label="Дата завантаження">${date}</td>
            <td class="py-4 px-3 font-mono ${docNumberCls}" data-label="№ документа">${esc(doc.doc_number)}${docNumberTwinMark(twinCount)}</td>
            <td class="py-4 px-3 text-slate-300" data-label="Затребував">
                <span class="block break-words">${fmtRequestedBy(requestedBy)}</span>
            </td>
            <td class="py-4 px-3 text-slate-300" data-label="Через кого">
                <span class="block break-words">${fmtRequestedBy(requestedVia)}</span>
            </td>
            <td class="py-4 px-3 text-blue-400 font-medium" data-label="Позицій">${doc.transaction_count}</td>
            <td class="py-4 px-3 text-right" data-label="Дії">
                ${retryBtn}<button onclick="event.stopPropagation(); openDeleteModal(${doc.id}, '${esc(doc.filename)}')" class="p-2 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition" title="Видалити">
                    <i class="fa-solid fa-trash"></i>
                </button>
            </td>
        </tr>
        <tr id="doc-impact-row-${doc.id}" class="hidden">
            <td colspan="12" class="p-0">
                <div class="expand-row px-8 py-4 border-t border-slate-800/40">
                    <div id="doc-impact-content-${doc.id}" class="text-xs text-slate-400">Завантаження...</div>
                </div>
            </td>
        </tr>`;
    });
    tbody.innerHTML = html;
}

async function reloadDocImpact(docId) {
    const content = document.getElementById('doc-impact-content-' + docId);
    if (!content) return;

    try {
        const res = await fetch('/api/warehouse/documents/' + docId + '/ocr');
        const data = await res.json();
        if (data.error) {
            content.innerHTML = '<p class="text-red-400 py-2">Помилка: ' + esc(data.error) + '</p>';
            return;
        }

        const isPhoto = data.file_type === 'photo' || (data.filename && data.filename.match(/\.(jpg|jpeg|png|webp)$/i));
        const rawText = data.raw_text || '';
        const impacts = data.impact || [];

        let h = '<div class="space-y-4">';

        // Попередження про неповне розпізнавання (#29): той самий перелік, що й у мітці рядка.
        const missingFields = data.missing_fields || [];
        if (missingFields.length) {
            h += '<div class="rounded-xl border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-200 flex items-start gap-2">';
            h += '<i class="fa-solid fa-triangle-exclamation text-amber-400 mt-0.5"></i>';
            h += '<span>Документ не в обліку. Не розпізнано: ' + esc(missingFields.join(', ')) + '</span>';
            h += '</div>';
        }

        if (isPhoto) {
            h += '<div class="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">';

            // Left: Image Preview Card
            h += '<div class="lg:col-span-4 glass rounded-xl p-3 border border-slate-800 flex flex-col items-center space-y-3 bg-slate-900/60">';
            h += '<div class="relative w-full max-h-[320px] overflow-hidden rounded-lg bg-slate-950 flex items-center justify-center border border-slate-800/80 cursor-pointer group" onclick="viewDocument(' + docId + ', \'' + esc(data.filename) + '\', \'' + data.file_type + '\')">';
            h += '<img src="/api/warehouse/documents/' + docId + '/view" alt="' + esc(data.filename) + '" class="max-h-[300px] w-auto object-contain rounded select-none group-hover:scale-105 transition duration-300" />';
            h += '<div class="absolute inset-0 bg-slate-950/40 opacity-0 group-hover:opacity-100 flex items-center justify-center transition duration-200"><span class="px-3 py-1.5 bg-blue-600/90 text-white rounded-lg text-xs font-medium shadow-lg"><i class="fa-solid fa-expand mr-1.5"></i>Відкрити в повному розмірі</span></div>';
            h += '</div>';
            h += '<div class="w-full flex items-center justify-between text-xs text-slate-400 px-1">';
            h += '<span class="font-medium text-slate-300 min-w-0 break-words"><i class="fa-solid fa-image text-emerald-400 mr-1.5"></i>' + esc(data.filename) + '</span>';
            h += '<button onclick="viewDocument(' + docId + ', \'' + esc(data.filename) + '\', \'' + data.file_type + '\')" class="text-blue-400 hover:text-blue-300 font-medium transition"><i class="fa-solid fa-magnifying-glass-plus mr-1"></i>Збільшити</button>';
            h += '</div>';
            h += '</div>';

            // Right: OCR Text and Metadata Card
            h += '<div class="lg:col-span-8 space-y-3">';

            // Meta bar — усі пʼять полів розпізнавання рендеряться завжди: значення або прочерк.
            // Олівець має кожне поле — і заповнене, і порожнє: саме ним поле дозаповнюють.
            const docFieldPencil = (field, label) => '<button onclick="event.stopPropagation(); openDocFieldModal(' + docId + ', \'' + field + '\')" class="text-slate-500 hover:text-blue-400 p-0.5 rounded transition" title="Редагувати: ' + label + '"><i class="fa-solid fa-pencil text-[10px]"></i></button>';
            const metaField = (label, valueHtml, field) => '<span class="text-xs text-slate-300 inline-flex items-center gap-1"><span class="text-slate-500">' + label + ':</span> ' + valueHtml + docFieldPencil(field, label) + '</span>';
            const metaDash = '<span class="text-slate-600">—</span>';
            h += '<div class="glass rounded-xl p-3 border border-slate-800 flex flex-wrap items-center justify-between gap-2 bg-slate-900/60">';
            h += '<div class="flex items-center gap-3">';
            const dt = (data.doc_type || '').toUpperCase();
            if (dt) {
                const badge = dt === 'НАКЛАДНА' ? 'badge-nakladna' : (dt === 'ВИМОГА' ? 'badge-vymoha' : 'badge-import');
                h += metaField('Тип', '<span class="px-2.5 py-0.5 rounded-full text-xs font-semibold ' + badge + '">' + esc(dt) + '</span>', 'doc_type');
            } else {
                h += metaField('Тип', metaDash, 'doc_type');
            }
            h += metaField('№', data.doc_number ? '<span class="font-mono font-bold text-slate-200">' + esc(data.doc_number) + '</span>' : metaDash, 'doc_number');
            h += metaField('Дата', data.doc_date ? esc(data.doc_date) : metaDash, 'doc_date');
            h += metaField('Затребував', data.requested_by ? '<span class="text-amber-200">' + esc(data.requested_by) + '</span>' : metaDash, 'requested_by');
            h += metaField('Через кого', data.requested_via ? '<span class="text-amber-200">' + esc(data.requested_via) + '</span>' : metaDash, 'requested_via');
            h += '</div>';
            if (rawText) {
                h += '<button onclick="copyTextDirect(\'ocr-acc-text-' + docId + '\', this)" class="px-2.5 py-1 text-xs text-slate-400 hover:text-slate-200 bg-slate-800 hover:bg-slate-700 rounded-lg transition flex items-center gap-1"><i class="fa-solid fa-copy"></i><span>Копіювати текст</span></button>';
            }
            h += '</div>';

            // OCR Text Box
            h += '<div class="glass rounded-xl p-3 border border-slate-800 bg-slate-900/60">';
            h += '<div class="text-xs font-semibold text-slate-400 mb-1.5 flex items-center gap-1.5"><i class="fa-solid fa-align-left text-blue-400"></i><span>Розпізнаний OCR текст з файлу:</span></div>';
            h += '<pre id="ocr-acc-text-' + docId + '" class="bg-slate-950/80 p-3 rounded-lg border border-slate-800/80 text-slate-300 font-mono text-[11px] whitespace-pre-wrap break-words leading-relaxed max-h-[160px] overflow-y-auto select-text">' + (rawText ? esc(rawText) : esc(getOcrPlaceholder(data.status))) + '</pre>';
            h += '</div>';

            // Items Impact Table
            if (impacts.length > 0) {
                h += '<div class="glass rounded-xl p-3 border border-slate-800 bg-slate-900/60">';
                h += '<div class="text-xs font-semibold text-slate-400 mb-2 flex items-center justify-between"><span>Позиції в документі (' + impacts.length + ')</span></div>';
                h += '<div class="overflow-x-auto"><table class="w-full text-xs card-table"><thead><tr class="text-slate-500 text-[11px] uppercase"><th class="py-1 pr-3 text-left">Ном. номер</th><th class="py-1 pr-3 text-left">Найменування</th><th class="py-1 pr-3 text-left">Тип</th><th class="py-1 pr-3 text-right">Кількість</th><th class="py-1 pr-3 text-left">Од.</th><th class="py-1 pr-3 text-left">Джерело</th></tr></thead><tbody>';
                impacts.forEach(imp => {
                    const isInc = imp.operation_type === 'income';
                    const badge = isInc ? 'badge-income' : 'badge-expense';
                    const label = isInc ? 'Прихід' : 'Розхід';
                    const qi = fmtImpactQty(imp.quantity, isInc);
                    h += `<tr class="border-t border-slate-800/30 hover:bg-slate-800/30 transition group">
                        <td class="py-1.5 pr-3 font-mono text-slate-400" data-label="Ном. номер">
                            <div class="flex items-center justify-between gap-1">
                                <span>${esc(imp.sku)}</span>
                                <button onclick="event.stopPropagation(); openEditModal(${imp.item_id}, 'sku', '${esc(imp.sku)}', 'Номенклатурний номер (SKU)')" class="text-slate-500 hover:text-blue-400 p-0.5 rounded transition opacity-0 hover:opacity-100 group-hover:opacity-100" title="Редагувати номенклатурний номер">
                                    <i class="fa-solid fa-pencil text-[10px]"></i>
                                </button>
                            </div>
                        </td>
                        <td class="py-1.5 pr-3 text-slate-200" data-label="Найменування">
                            <div class="flex items-center justify-between gap-1">
                                <span class="min-w-0 break-words">${esc(imp.name)}</span>
                                <button onclick="event.stopPropagation(); openEditModal(${imp.item_id}, 'name', '${esc(imp.name)}', 'Найменування')" class="text-slate-500 hover:text-blue-400 p-0.5 rounded transition opacity-0 hover:opacity-100 group-hover:opacity-100 shrink-0" title="Редагувати найменування">
                                    <i class="fa-solid fa-pencil text-[10px]"></i>
                                </button>
                            </div>
                        </td>
                        <td class="py-1.5 pr-3" data-label="Тип"><span class="px-2 py-0.5 rounded-full text-[10px] font-medium ${badge}">${label}</span></td>
                        <td class="py-1.5 pr-3 text-right font-medium ${qi[1]}" data-label="Кількість">
                            <div class="flex items-center justify-end gap-1">
                                <span>${qi[0]}</span>
                                <button onclick="event.stopPropagation(); openEditModal(${imp.item_id}, 'balance', '${imp.quantity}', 'Залишок (кількість)')" class="text-slate-500 hover:text-blue-400 p-0.5 rounded transition opacity-0 hover:opacity-100 group-hover:opacity-100" title="Коригувати кількість/залишок">
                                    <i class="fa-solid fa-pencil text-[10px]"></i>
                                </button>
                            </div>
                        </td>
                        <td class="py-1.5 pr-3 text-slate-400" data-label="Од.">
                            <div class="flex items-center justify-between gap-1">
                                <span>${esc(imp.unit)}</span>
                                <button onclick="event.stopPropagation(); openEditModal(${imp.item_id}, 'unit', '${esc(imp.unit)}', 'Одиниця виміру')" class="text-slate-500 hover:text-blue-400 p-0.5 rounded transition opacity-0 hover:opacity-100 group-hover:opacity-100" title="Редагувати одиницю виміру">
                                    <i class="fa-solid fa-pencil text-[10px]"></i>
                                </button>
                            </div>
                        </td>
                        <td class="py-1.5 pr-3 text-slate-500 text-[11px] break-words" data-label="Джерело">${esc(imp.source_row || '')}</td>
                    </tr>`;
                });
                h += '</tbody></table></div></div>';
            }

            h += '</div></div>'; // end grid
        } else {
            // Excel / other non-photo documents
            if (impacts.length === 0) {
                h += '<p class="text-slate-500 py-2">Документ не вплинув на жодну позицію.</p>';
            } else {
                h += '<table class="w-full text-xs card-table"><thead><tr class="text-slate-500 text-[11px] uppercase">' +
                    '<th class="py-1 pr-3 text-left">Ном. номер</th><th class="py-1 pr-3 text-left">Найменування</th>' +
                    '<th class="py-1 pr-3 text-left">Тип</th><th class="py-1 pr-3 text-right">Кількість</th>' +
                    '<th class="py-1 pr-3 text-left">Од.</th><th class="py-1 pr-3 text-left">Джерело</th>' +
                    '</tr></thead><tbody>';
                impacts.forEach(imp => {
                    const isInc = imp.operation_type === 'income';
                    const badge = isInc ? 'badge-income' : 'badge-expense';
                    const label = isInc ? 'Прихід' : 'Розхід';
                    const qi = fmtImpactQty(imp.quantity, isInc);
                    const srcRow = imp.source_row || '';
                    h += `<tr class="border-t border-slate-800/30 hover:bg-slate-800/30 transition group">
                        <td class="py-2 pr-3 font-mono text-slate-400" data-label="Ном. номер">
                            <div class="flex items-center justify-between gap-1">
                                <span>${esc(imp.sku)}</span>
                                <button onclick="event.stopPropagation(); openEditModal(${imp.item_id}, 'sku', '${esc(imp.sku)}', 'Номенклатурний номер (SKU)')" class="text-slate-500 hover:text-blue-400 p-0.5 rounded transition opacity-0 hover:opacity-100 group-hover:opacity-100" title="Редагувати номенклатурний номер">
                                    <i class="fa-solid fa-pencil text-[10px]"></i>
                                </button>
                            </div>
                        </td>
                        <td class="py-2 pr-3 text-slate-200" data-label="Найменування">
                            <div class="flex items-center justify-between gap-1">
                                <span class="min-w-0 break-words">${esc(imp.name)}</span>
                                <button onclick="event.stopPropagation(); openEditModal(${imp.item_id}, 'name', '${esc(imp.name)}', 'Найменування')" class="text-slate-500 hover:text-blue-400 p-0.5 rounded transition opacity-0 hover:opacity-100 group-hover:opacity-100 shrink-0" title="Редагувати найменування">
                                    <i class="fa-solid fa-pencil text-[10px]"></i>
                                </button>
                            </div>
                        </td>
                        <td class="py-2 pr-3" data-label="Тип"><span class="px-2 py-0.5 rounded-full text-[11px] font-medium ${badge}">${label}</span></td>
                        <td class="py-2 pr-3 text-right font-medium ${qi[1]}" data-label="Кількість">
                            <div class="flex items-center justify-end gap-1">
                                <span>${qi[0]}</span>
                                <button onclick="event.stopPropagation(); openEditModal(${imp.item_id}, 'balance', '${imp.quantity}', 'Залишок (кількість)')" class="text-slate-500 hover:text-blue-400 p-0.5 rounded transition opacity-0 hover:opacity-100 group-hover:opacity-100" title="Коригувати кількість/залишок">
                                    <i class="fa-solid fa-pencil text-[10px]"></i>
                                </button>
                            </div>
                        </td>
                        <td class="py-2 pr-3 text-slate-400" data-label="Од.">
                            <div class="flex items-center justify-between gap-1">
                                <span>${esc(imp.unit)}</span>
                                <button onclick="event.stopPropagation(); openEditModal(${imp.item_id}, 'unit', '${esc(imp.unit)}', 'Одиниця виміру')" class="text-slate-500 hover:text-blue-400 p-0.5 rounded transition opacity-0 hover:opacity-100 group-hover:opacity-100" title="Редагувати одиницю виміру">
                                    <i class="fa-solid fa-pencil text-[10px]"></i>
                                </button>
                            </div>
                        </td>
                        <td class="py-2 pr-3 text-slate-500 text-[11px] break-words" data-label="Джерело">${esc(srcRow)}</td>
                    </tr>`;
                });
                h += '</tbody></table>';
            }
        }

        h += '</div>';
        content.innerHTML = h;
    } catch(e) {
        content.innerHTML = '<p class="text-red-400 py-2">Помилка завантаження: ' + esc(e.message) + '</p>';
    }
}

async function toggleDocImpact(docId) {
    const row = document.getElementById('doc-impact-row-' + docId);
    const chevron = document.getElementById('doc-chevron-' + docId);
    if (!row.classList.contains('hidden')) {
        row.classList.add('hidden');
        chevron.style.transform = '';
        return;
    }
    row.classList.remove('hidden');
    chevron.style.transform = 'rotate(90deg)';

    const content = document.getElementById('doc-impact-content-' + docId);
    content.innerHTML = '<div class="py-4 text-center text-slate-500"><i class="fa-solid fa-spinner fa-spin mr-2"></i>Завантаження даних...</div>';
    await reloadDocImpact(docId);
}

// ---- Import / Export ----

async function importExcel(input) {
    const file = input.files[0];
    if (!file) return;

    const progress = document.getElementById('import-progress');
    const statusEl = document.getElementById('import-status');
    const barEl = document.getElementById('import-bar');
    const detailEl = document.getElementById('import-detail');

    progress.classList.remove('hidden');
    statusEl.textContent = 'Завантаження файлу: ' + file.name + '...';
    barEl.style.width = '10%';
    detailEl.textContent = 'Розмір: ' + (file.size / 1024).toFixed(1) + ' КБ';
    console.log('[Імпорт] Початок завантаження:', file.name, '(' + file.size + ' байт)');

    const formData = new FormData();
    formData.append('file', file);
    try {
        barEl.style.width = '30%';
        statusEl.textContent = 'Відправка на сервер...';
        console.log('[Імпорт] Відправка на сервер...');

        const res = await fetch('/api/warehouse/import', { method: 'POST', body: formData });

        barEl.style.width = '70%';
        statusEl.textContent = 'Обробка даних...';
        console.log('[Імпорт] Обробка відповіді...');

        const result = await res.json();

        barEl.style.width = '100%';

        if (result.error) {
            statusEl.textContent = 'Помилка: ' + result.error;
            console.error('[Імпорт] Помилка:', result.error);
            detailEl.textContent = '';
            setTimeout(() => { progress.classList.add('hidden'); }, 2000);
            input.value = '';
            return;
        }

        const docTypeInfo = result.doc_type ? ' (' + result.doc_type + ')' : '';
        statusEl.textContent = 'Імпорт завершено!' + docTypeInfo;
        detailEl.textContent = `${result.items_created} нових, ${result.items_updated} оновлено, ${result.transactions_created} транзакцій`;
        console.log('[Імпорт] Завершено:', result);
        console.log('[Імпорт] Тип документу:', result.doc_type || 'не визначено');
        console.log('[Імпорт] Нових позицій:', result.items_created);
        console.log('[Імпорт] Оновлено:', result.items_updated);
        console.log('[Імпорт] Транзакцій:', result.transactions_created);

        setTimeout(async () => {
            progress.classList.add('hidden');
            await refreshAll();
        }, 1500);
    } catch(e) {
        statusEl.textContent = 'Помилка імпорту';
        detailEl.textContent = e.message;
        console.error('[Імпорт] Помилка:', e);
        setTimeout(() => { progress.classList.add('hidden'); }, 2000);
    }
    input.value = '';
}

function exportExcel() {
    window.location.href = '/api/warehouse/export';
}

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

function toggleOcrPanel() {
    const panel = document.getElementById('ocr-panel');
    const btn = document.getElementById('toggle-ocr-btn');
    if (!panel) return;
    if (panel.classList.contains('hidden')) {
        panel.classList.remove('hidden');
        btn.classList.add('bg-blue-600/20', 'text-blue-400', 'border-blue-500/30');
        btn.classList.remove('text-slate-400', 'bg-slate-800');
    } else {
        panel.classList.add('hidden');
        btn.classList.remove('bg-blue-600/20', 'text-blue-400', 'border-blue-500/30');
        btn.classList.add('text-slate-400', 'bg-slate-800');
    }
}

function copyOcrText() {
    if (!currentOcrText) return;
    navigator.clipboard.writeText(currentOcrText).then(() => {
        const label = document.getElementById('copy-text-label');
        if (label) {
            label.textContent = 'Скопійовано!';
            setTimeout(() => { label.textContent = 'Копіювати'; }, 2000);
        }
    }).catch(err => {
        console.error('Copy failed:', err);
    });
}

function copyTextDirect(elementId, btn) {
    const el = document.getElementById(elementId);
    if (!el) return;
    const text = el.innerText || el.textContent || '';
    if (!text) return;
    navigator.clipboard.writeText(text).then(() => {
        const origHtml = btn.innerHTML;
        btn.innerHTML = '<i class="fa-solid fa-check text-emerald-400"></i><span class="text-emerald-400">Скопійовано!</span>';
        setTimeout(() => { btn.innerHTML = origHtml; }, 2000);
    }).catch(err => {
        console.error('Copy failed:', err);
    });
}

function closeImgModal() {
    document.getElementById('img-modal').classList.add('hidden');
    const img = document.getElementById('img-modal-src');
    if (img) {
        img.src = '';
    }
    imgZoom = 1.0;
    currentOcrText = '';
}

function applyImgZoom() {
    const img = document.getElementById('img-modal-src');
    if (!img) return;
    const nw = img.naturalWidth;
    const nh = img.naturalHeight;
    if (nw > 0) {
        img.style.maxWidth = 'none';
        img.style.maxHeight = 'none';
        img.style.width = Math.round(nw * imgZoom) + 'px';
        img.style.height = Math.round(nh * imgZoom) + 'px';
        img.style.flexShrink = '0';
    } else {
        img.style.maxWidth = 'none';
        img.style.maxHeight = 'none';
        img.style.width = (imgZoom * 100) + '%';
        img.style.height = 'auto';
        img.style.flexShrink = '0';
    }
}

function setImgZoom(level) {
    imgZoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, Math.round(level * 100) / 100));
    applyImgZoom();
    updateZoomUI();
}

function zoomImgIn() {
    const nextZoom = Math.min(MAX_ZOOM, Math.round((imgZoom + ZOOM_STEP) * 100) / 100);
    setImgZoom(nextZoom);
}

function zoomImgOut() {
    const nextZoom = Math.max(MIN_ZOOM, Math.round((imgZoom - ZOOM_STEP) * 100) / 100);
    setImgZoom(nextZoom);
}

function resetImgZoom() {
    setImgZoom(1.0);
    const container = document.getElementById('img-modal-container');
    if (container) {
        container.scrollLeft = 0;
        container.scrollTop = 0;
    }
}

function updateZoomUI() {
    const label = document.getElementById('img-zoom-label');
    if (label) {
        label.textContent = Math.round(imgZoom * 100) + '%';
    }
    const btnIn = document.getElementById('img-zoom-in-btn');
    if (btnIn) {
        btnIn.disabled = imgZoom >= MAX_ZOOM;
    }
    const btnOut = document.getElementById('img-zoom-out-btn');
    if (btnOut) {
        btnOut.disabled = imgZoom <= MIN_ZOOM;
    }
}

async function openExcelPreview(docId, filename, highlightRows) {
    highlightRows = highlightRows || [];
    const modal = document.getElementById('excel-modal');
    const content = document.getElementById('excel-modal-content');
    const titleEl = document.getElementById('excel-modal-title');
    const downloadBtn = document.getElementById('excel-download-btn');

    titleEl.innerHTML = '<i class="fa-solid fa-file-excel text-green-500"></i> ' + esc(filename);
    downloadBtn.onclick = () => { window.location.href = '/api/warehouse/documents/' + docId + '/download'; };
    content.innerHTML = '<p class="text-slate-500 py-4 text-center"><i class="fa-solid fa-spinner fa-spin mr-2"></i>Завантаження...</p>';
    modal.classList.remove('hidden');

    try {
        let previewUrl = '/api/warehouse/documents/' + docId + '/preview';
        if (highlightRows.length > 0) {
            previewUrl += '?highlight=' + highlightRows.join(',');
        }
        const res = await fetch(previewUrl);
        const data = await res.json();
        if (data.error) {
            content.innerHTML = '<p class="text-red-400 py-4 text-center">' + esc(data.error) + '</p>';
            return;
        }
        let h = '<div class="overflow-x-auto"><table class="w-full border-collapse text-xs">';
        h += '<thead><tr class="bg-slate-800/60">';
        h += '<th class="py-2 px-3 text-center text-slate-400 font-semibold border border-slate-700/50 w-12">#</th>';
        data.headers.forEach(hdr => {
            h += `<th class="py-2 px-3 text-left text-slate-400 font-semibold border border-slate-700/50">${esc(hdr)}</th>`;
        });
        h += '</tr></thead><tbody>';
        data.rows.forEach((row, idx) => {
            const rowNum = data.row_numbers ? data.row_numbers[idx] : (idx + 2);
            const isHl = highlightRows.includes(rowNum);
            const bg = isHl ? 'bg-amber-500/20' : (idx % 2 === 0 ? '' : 'bg-slate-800/20');
            h += `<tr class="${bg}" ${isHl ? 'id="hl-row-' + rowNum + '"' : ''}>`;
            h += `<td class="py-1.5 px-3 ${isHl ? 'text-amber-300' : 'text-slate-500'} border border-slate-800/40 text-center font-mono">${rowNum}</td>`;
            row.forEach(cell => {
                h += `<td class="py-1.5 px-3 ${isHl ? 'text-amber-200' : 'text-slate-300'} border border-slate-800/40">${esc(cell)}</td>`;
            });
            h += '</tr>';
        });
        h += '</tbody></table></div>';
        if (data.truncated) {
            h += '<p class="text-xs text-slate-500 mt-2 text-center">Показано перші ' + data.total_rows + ' рядків</p>';
        }
        content.innerHTML = h;
        if (highlightRows.length > 0) {
            setTimeout(() => {
                const el = document.getElementById('hl-row-' + highlightRows[0]);
                if (el) el.scrollIntoView({behavior: 'smooth', block: 'center'});
            }, 100);
        }
    } catch(e) {
        content.innerHTML = '<p class="text-red-400 py-4 text-center">Помилка завантаження: ' + esc(e.message) + '</p>';
    }
}
function closeExcelModal() { document.getElementById('excel-modal').classList.add('hidden'); }

// ---- Delete ----

let pendingDeleteId = null;
function openDeleteModal(docId, filename) {
    pendingDeleteId = docId;
    document.getElementById('delete-doc-name').innerText = filename;
    document.getElementById('confirm-delete-btn').onclick = () => executeDelete(docId);
    document.getElementById('delete-modal').classList.remove('hidden');
}
function closeDeleteModal() {
    pendingDeleteId = null;
    document.getElementById('delete-modal').classList.add('hidden');
}
async function executeDelete(docId) {
    try {
        const res = await fetch('/api/warehouse/documents/' + docId, { method: 'DELETE' });
        if (!res.ok) throw new Error('Помилка видалення');
        closeDeleteModal();
        await refreshAll();
    } catch(e) { alert('Не вдалося видалити: ' + e.message); }
}

// ---- Helpers ----

function esc(s) {
    return String(s || '').replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]));
}
function fmtImpactQty(qty, isInc) {
    if (qty === 0) return ['0', 'text-slate-400'];
    return [(isInc ? '+' : '-') + fmtNum(qty), isInc ? 'text-emerald-400' : 'text-rose-400'];
}
function fmtNum(v) {
    if (v === null || v === undefined || v === '') return '';
    const n = Number(v);
    if (isNaN(n)) return String(v);
    return n % 1 === 0 ? n.toString() : n.toFixed(2);
}
function formatTs(ts) {
    if (!ts) return '';
    const d = new Date(ts * 1000);
    return d.toLocaleDateString('uk-UA') + ' ' + d.toLocaleTimeString('uk-UA', {hour:'2-digit', minute:'2-digit'});
}
function getFileIcon(ft) {
    if (ft === 'excel') return '<i class="fa-solid fa-file-excel text-green-500"></i>';
    if (ft === 'pdf') return '<i class="fa-solid fa-file-pdf text-red-400"></i>';
    return '<i class="fa-solid fa-image text-emerald-400"></i>';
}
function fmtRequestedBy(v) {
    return v ? esc(v) : '<span class="text-slate-600">—</span>';
}
// Позначка ручного редагування: документ, у який втручався користувач.
function manualEditMark(isEdited) {
    if (!isEdited) return '';
    return ' <span class="text-amber-400" title="Правка вручну"><i class="fa-solid fa-pen"></i></span>';
}
// Мітка «не в обліку»: перелік не розпізнаних полів дає бекенд, клітинка лише показує його.
// Нею користуються і рядок таблиці, і підказка до позначок — щоб вони не розійшлися.
function docUnaccountedMark(missingFields) {
    if (!missingFields.length) return '';
    return ` <span class="text-amber-400 ml-1 align-middle" title="Документ не в обліку. Не розпізнано: ${esc(missingFields.join(', '))}"><i class="fa-solid fa-triangle-exclamation"></i></span>`;
}
// Клон-підказка до підсвіченої клітинки «№ документа» (клас .doc-dup): скільки ще документів
// мають такий самий номер. Нею користуються і рядок таблиці, і підказка до позначок.
function docNumberTwinMark(twinCount) {
    if (!twinCount) return '';
    return `<span class="text-purple-300 ml-1" title="Такий самий номер ще в ${twinCount} документах"><i class="fa-solid fa-clone"></i></span>`;
}

// ---- Log Console Logic ----

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

document.addEventListener('DOMContentLoaded', function() {
    refreshAll();
    fetchLogs();
    connectLogStream();
    renderDocLegend();
    const imgContainer = document.getElementById('img-modal-container');
    if (imgContainer) {
        imgContainer.addEventListener('wheel', function(e) {
            if (!e.ctrlKey) return;
            e.preventDefault();
            if (e.deltaY < 0) {
                zoomImgIn();
            } else {
                zoomImgOut();
            }
        }, {passive: false});
    }

    document.addEventListener('keydown', function(e) {
        const editModal = document.getElementById('edit-modal');
        if (editModal && !editModal.classList.contains('hidden')) {
            if (e.key === 'Escape') {
                closeEditModal();
            } else if (e.key === 'Enter' && (e.target.id === 'edit-new-value' || e.target.id === 'edit-comment')) {
                e.preventDefault();
                submitEditField();
            }
        }
    });
});
