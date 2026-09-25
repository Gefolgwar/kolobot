
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
