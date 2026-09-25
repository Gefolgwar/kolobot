
document.addEventListener('DOMContentLoaded', function() {
    refreshAll();
    fetchLogs();
    connectLogStream();
    renderDocLegend();
    const imgContainer = document.getElementById('img-modal-container');
    if (imgContainer) {
        imgContainer.addEventListener('wheel', function(e) {
            if (!e.ctrlKey) return;
            e.preventDefault();
            if (e.deltaY < 0) {
                zoomImgIn();
            } else {
                zoomImgOut();
            }
        }, {passive: false});
    }

    document.addEventListener('keydown', function(e) {
        const editModal = document.getElementById('edit-modal');
        if (editModal && !editModal.classList.contains('hidden')) {
            if (e.key === 'Escape') {
                closeEditModal();
            } else if (e.key === 'Enter' && (e.target.id === 'edit-new-value' || e.target.id === 'edit-comment')) {
                e.preventDefault();
                submitEditField();
            }
        }
    });
});
