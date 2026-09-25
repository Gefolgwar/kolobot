
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
