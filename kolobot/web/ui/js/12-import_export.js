
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
