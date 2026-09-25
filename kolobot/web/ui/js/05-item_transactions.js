
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
