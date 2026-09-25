
let pendingDeleteId = null;
function openDeleteModal(docId, filename) {
    pendingDeleteId = docId;
    document.getElementById('delete-doc-name').innerText = filename;
    document.getElementById('confirm-delete-btn').onclick = () => executeDelete(docId);
    document.getElementById('delete-modal').classList.remove('hidden');
}
function closeDeleteModal() {
    pendingDeleteId = null;
    document.getElementById('delete-modal').classList.add('hidden');
}
async function executeDelete(docId) {
    try {
        const res = await fetch('/api/warehouse/documents/' + docId, { method: 'DELETE' });
        if (!res.ok) throw new Error('Помилка видалення');
        closeDeleteModal();
        await refreshAll();
    } catch(e) { alert('Не вдалося видалити: ' + e.message); }
}

function esc(s) {
    return String(s || '').replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]));
}
function fmtImpactQty(qty, isInc) {
    if (qty === 0) return ['0', 'text-slate-400'];
    return [(isInc ? '+' : '-') + fmtNum(qty), isInc ? 'text-emerald-400' : 'text-rose-400'];
}
function fmtNum(v) {
    if (v === null || v === undefined || v === '') return '';
    const n = Number(v);
    if (isNaN(n)) return String(v);
    return n % 1 === 0 ? n.toString() : n.toFixed(2);
}
function formatTs(ts) {
    if (!ts) return '';
    const d = new Date(ts * 1000);
    return d.toLocaleDateString('uk-UA') + ' ' + d.toLocaleTimeString('uk-UA', {hour:'2-digit', minute:'2-digit'});
}
function getFileIcon(ft) {
    if (ft === 'excel') return '<i class="fa-solid fa-file-excel text-green-500"></i>';
    if (ft === 'pdf') return '<i class="fa-solid fa-file-pdf text-red-400"></i>';
    return '<i class="fa-solid fa-image text-emerald-400"></i>';
}
function fmtRequestedBy(v) {
    return v ? esc(v) : '<span class="text-slate-600">—</span>';
}
// Позначка ручного редагування: документ, у який втручався користувач.
function manualEditMark(isEdited) {
    if (!isEdited) return '';
    return ' <span class="text-amber-400" title="Правка вручну"><i class="fa-solid fa-pen"></i></span>';
}
// Мітка «не в обліку»: перелік не розпізнаних полів дає бекенд, клітинка лише показує його.
// Нею користуються і рядок таблиці, і підказка до позначок — щоб вони не розійшлися.
function docUnaccountedMark(missingFields) {
    if (!missingFields.length) return '';
    return ` <span class="text-amber-400 ml-1 align-middle" title="Документ не в обліку. Не розпізнано: ${esc(missingFields.join(', '))}"><i class="fa-solid fa-triangle-exclamation"></i></span>`;
}
// Клон-підказка до підсвіченої клітинки «№ документа» (клас .doc-dup): скільки ще документів
// мають такий самий номер. Нею користуються і рядок таблиці, і підказка до позначок.
function docNumberTwinMark(twinCount) {
    if (!twinCount) return '';
    return `<span class="text-purple-300 ml-1" title="Такий самий номер ще в ${twinCount} документах"><i class="fa-solid fa-clone"></i></span>`;
}
