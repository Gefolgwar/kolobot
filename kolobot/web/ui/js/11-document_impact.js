
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
