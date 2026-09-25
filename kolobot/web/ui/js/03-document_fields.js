
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
