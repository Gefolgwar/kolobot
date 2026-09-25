
function filterItems() {
    const q = document.getElementById('search-items').value.toLowerCase().trim();
    let filtered = allItems;

    if (activeFilter === 'below-min') {
        filtered = filtered.filter(it => {
            const minBal = (it.min_balance !== null && it.min_balance !== undefined) ? Number(it.min_balance) : 0;
            return minBal > 0 && (it.balance || 0) < minBal;
        });
    } else if (activeFilter === 'negative') {
        filtered = filtered.filter(it => (it.balance || 0) < 0);
    } else if (activeFilter === 'no-docs') {
        filtered = filtered.filter(it => (it.doc_count || 0) === 0);
    } else if (activeFilter === 'dup-names') {
        const dupNames = getDuplicateNames();
        filtered = filtered.filter(it => dupNames.has((it.name || '').trim().toLowerCase()));
    } else if (activeFilter === 'zeros') {
        filtered = filtered.filter(it => (it.total_income || 0) === 0 && (it.total_expense || 0) === 0 && (it.balance || 0) === 0);
    }

    if (q) {
        filtered = filtered.filter(it =>
            (it.name || '').toLowerCase().includes(q) ||
            (it.sku || '').toLowerCase().includes(q) ||
            (it.supplier || '').toLowerCase().includes(q) ||
            (it.notes || '').toLowerCase().includes(q) ||
            (it.unit || '').toLowerCase().includes(q)
        );
    }
    renderItems(filtered);
}

function getDuplicateNames() {
    const nameSkus = {};
    allItems.forEach(it => {
        const name = (it.name || '').trim().toLowerCase();
        if (!name) return;
        if (!nameSkus[name]) nameSkus[name] = new Set();
        nameSkus[name].add((it.sku || '').trim());
    });
    const dupNames = new Set();
    Object.keys(nameSkus).forEach(name => {
        if (nameSkus[name].size > 1) dupNames.add(name);
    });
    return dupNames;
}

function setFilter(filter) {
    activeFilter = (activeFilter === filter) ? '' : filter;
    updateFilterUI();
    filterItems();
}

function updateFilterUI() {
    ['below-min', 'negative', 'no-docs', 'dup-names', 'zeros'].forEach(f => {
        const btn = document.getElementById('filter-' + f);
        if (!btn) return;
        if (f === activeFilter) {
            btn.classList.add('bg-blue-600/30', 'text-blue-300', 'border-blue-500/50');
            btn.classList.remove('text-slate-400', 'border-slate-700/60', 'bg-slate-900/50');
        } else {
            btn.classList.remove('bg-blue-600/30', 'text-blue-300', 'border-blue-500/50');
            btn.classList.add('text-slate-400', 'border-slate-700/60', 'bg-slate-900/50');
        }
    });
}

function updateFilterCounts() {
    const belowMinCount = allItems.filter(it => {
        const minBal = (it.min_balance !== null && it.min_balance !== undefined) ? Number(it.min_balance) : 0;
        return minBal > 0 && (it.balance || 0) < minBal;
    }).length;
    const belowMinEl = document.getElementById('filter-below-min-count');
    if (belowMinEl) belowMinEl.textContent = belowMinCount;

    const negCount = allItems.filter(it => (it.balance || 0) < 0).length;
    document.getElementById('filter-negative-count').textContent = negCount;

    const noDocCount = allItems.filter(it => (it.doc_count || 0) === 0).length;
    document.getElementById('filter-no-docs-count').textContent = noDocCount;

    const dupNames = getDuplicateNames();
    let dupCount = 0;
    allItems.forEach(it => {
        if (dupNames.has((it.name || '').trim().toLowerCase())) dupCount++;
    });
    document.getElementById('filter-dup-names-count').textContent = dupCount;

    const zeroCount = allItems.filter(it => (it.total_income || 0) === 0 && (it.total_expense || 0) === 0 && (it.balance || 0) === 0).length;
    document.getElementById('filter-zeros-count').textContent = zeroCount;
}
