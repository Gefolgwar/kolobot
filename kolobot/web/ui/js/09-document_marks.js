
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
