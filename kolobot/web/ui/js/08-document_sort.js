
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
