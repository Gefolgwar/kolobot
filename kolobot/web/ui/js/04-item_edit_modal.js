
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
