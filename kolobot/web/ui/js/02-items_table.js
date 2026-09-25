
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

let currentEditItemId = null;
let currentEditField = null;
