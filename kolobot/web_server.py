"""Embedded aiohttp web server: warehouse inventory UI with two tabs + REST API."""

from __future__ import annotations

import datetime
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

from aiohttp import web

from kolobot.file_store import FileStore
from kolobot.vector_store import VectorStore
from kolobot.warehouse_db import WarehouseDB

logger = logging.getLogger(__name__)

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="uk" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>kolobot — Складський облік</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body { background-color: #0f172a; color: #f8fafc; }
        .glass { background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.08); }
        .tab-active { border-bottom: 2px solid #3b82f6; color: #93c5fd; }
        .tab-inactive { color: #64748b; }
        .tab-inactive:hover { color: #94a3b8; }
        .expand-row { background: rgba(15, 23, 42, 0.6); }
        .badge-income { background: rgba(16,185,129,0.15); color: #34d399; }
        .badge-expense { background: rgba(244,63,94,0.15); color: #fb7185; }
        .badge-import { background: rgba(59,130,246,0.15); color: #60a5fa; }
        .badge-nakladna { background: rgba(16,185,129,0.15); color: #34d399; }
        .badge-vymoha { background: rgba(244,63,94,0.15); color: #fb7185; }
        .progress-bar { transition: width 0.3s ease; }
    </style>
</head>
<body class="min-h-screen font-sans pb-12">
    <!-- Header -->
    <header class="glass sticky top-0 z-30 border-b border-slate-800 px-6 py-4 mb-0">
        <div class="max-w-7xl mx-auto flex items-center justify-between">
            <div class="flex items-center space-x-3">
                <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center text-white font-bold text-xl shadow-lg shadow-blue-500/20">
                    <i class="fa-solid fa-warehouse"></i>
                </div>
                <div>
                    <h1 class="text-xl font-bold text-slate-100">kolobot</h1>
                    <p class="text-xs text-slate-400">Складський облік</p>
                </div>
            </div>
            <div class="flex items-center space-x-2">
                <label class="px-3 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-xl cursor-pointer transition shadow-lg shadow-blue-600/20">
                    <i class="fa-solid fa-file-import mr-1"></i> Імпорт Excel
                    <input type="file" accept=".xlsx,.xls" onchange="importExcel(this)" class="hidden">
                </label>
                <button onclick="exportExcel()" class="px-3 py-2 bg-slate-700 hover:bg-slate-600 text-slate-200 text-sm font-medium rounded-xl transition">
                    <i class="fa-solid fa-file-export mr-1"></i> Експорт
                </button>
                <button onclick="refreshAll()" class="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition" title="Оновити">
                    <i class="fa-solid fa-rotate"></i>
                </button>
            </div>
        </div>
    </header>

    <!-- Tabs -->
    <div class="max-w-7xl mx-auto px-6">
        <div class="flex space-x-6 border-b border-slate-800 mb-6 pt-4">
            <button id="tab-warehouse" onclick="switchTab('warehouse')" class="pb-3 px-1 text-sm font-semibold tab-active transition">
                <i class="fa-solid fa-boxes-stacked mr-1"></i> Склад
                <span id="items-count" class="ml-1 px-2 py-0.5 bg-slate-800 text-blue-400 rounded-full text-xs">0</span>
            </button>
            <button id="tab-documents" onclick="switchTab('documents')" class="pb-3 px-1 text-sm font-semibold tab-inactive transition">
                <i class="fa-solid fa-file-lines mr-1"></i> Документи
                <span id="docs-count" class="ml-1 px-2 py-0.5 bg-slate-800 text-slate-400 rounded-full text-xs">0</span>
            </button>
        </div>
    </div>

    <!-- Warehouse Tab -->
    <main id="panel-warehouse" class="max-w-7xl mx-auto px-6">
        <div class="glass rounded-2xl p-4 mb-6 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div class="relative w-full sm:w-96">
                <i class="fa-solid fa-magnifying-glass absolute left-3.5 top-3.5 text-slate-500"></i>
                <input type="text" id="search-items" onkeyup="filterItems()" placeholder="Пошук за назвою або номенклатурним номером..."
                    class="w-full bg-slate-900/80 text-sm text-slate-200 pl-10 pr-4 py-2.5 rounded-xl border border-slate-700/60 focus:outline-none focus:border-blue-500 transition">
            </div>
            <div class="text-xs text-slate-400">
                Показано: <span id="visible-items" class="font-bold text-slate-200">0</span>
            </div>
        </div>

        <div class="glass rounded-2xl border border-slate-800 overflow-hidden shadow-2xl">
            <div class="overflow-x-auto">
                <table class="w-full text-left border-collapse">
                    <thead>
                        <tr class="bg-slate-900/90 text-slate-400 text-xs font-semibold uppercase tracking-wider border-b border-slate-800">
                            <th class="py-4 px-3 w-8"></th>
                            <th class="py-4 px-3">Ном. номер</th>
                            <th class="py-4 px-3">Найменування</th>
                            <th class="py-4 px-3">Прихід</th>
                            <th class="py-4 px-3">Розхід</th>
                            <th class="py-4 px-3">Залишок</th>
                            <th class="py-4 px-3">Од.виміру</th>
                            <th class="py-4 px-3">Постачальник</th>
                            <th class="py-4 px-3">Примітки</th>
                        </tr>
                    </thead>
                    <tbody id="items-tbody" class="divide-y divide-slate-800/60 text-sm">
                        <tr><td colspan="9" class="py-12 text-center text-slate-500">
                            <i class="fa-solid fa-boxes-stacked text-2xl mb-2 text-slate-600"></i>
                            <p>Склад порожній. Завантажте Excel файл для початку роботи.</p>
                        </td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    </main>

    <!-- Documents Tab -->
    <main id="panel-documents" class="max-w-7xl mx-auto px-6 hidden">
        <div class="glass rounded-2xl border border-slate-800 overflow-hidden shadow-2xl">
            <div class="overflow-x-auto">
                <table class="w-full text-left border-collapse">
                    <thead>
                        <tr class="bg-slate-900/90 text-slate-400 text-xs font-semibold uppercase tracking-wider border-b border-slate-800">
                            <th class="py-4 px-3 w-8"></th>
                            <th class="py-4 px-3">Превʼю</th>
                            <th class="py-4 px-3">Файл</th>
                            <th class="py-4 px-3">Тип</th>
                            <th class="py-4 px-3">Тип документу</th>
                            <th class="py-4 px-3">Дата завантаження</th>
                            <th class="py-4 px-3">№ документа</th>
                            <th class="py-4 px-3">Позицій</th>
                            <th class="py-4 px-3 text-right">Дії</th>
                        </tr>
                    </thead>
                    <tbody id="docs-tbody" class="divide-y divide-slate-800/60 text-sm">
                        <tr><td colspan="9" class="py-12 text-center text-slate-500">
                            <p>Документів немає.</p>
                        </td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    </main>

    <!-- Delete Confirmation Modal -->
    <div id="delete-modal" class="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm hidden flex items-center justify-center p-4">
        <div class="glass w-full max-w-md rounded-2xl p-6 border border-red-500/30 shadow-2xl text-center space-y-4">
            <div class="w-12 h-12 rounded-full bg-red-500/10 text-red-400 flex items-center justify-center mx-auto text-xl border border-red-500/20">
                <i class="fa-solid fa-triangle-exclamation"></i>
            </div>
            <div>
                <h3 class="text-lg font-bold text-slate-100">Видалити документ?</h3>
                <p id="delete-doc-name" class="text-sm text-red-300 mt-1 break-all"></p>
                <p class="text-xs text-slate-500 mt-2">Усі транзакції цього документа будуть відкатані. Цю дію неможливо скасувати.</p>
            </div>
            <div class="flex items-center justify-center space-x-3 pt-2">
                <button onclick="closeDeleteModal()" class="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium rounded-xl transition">
                    Скасувати
                </button>
                <button id="confirm-delete-btn" class="px-4 py-2 bg-red-600 hover:bg-red-500 text-white text-sm font-medium rounded-xl transition shadow-lg shadow-red-600/30">
                    Так, видалити
                </button>
            </div>
        </div>
    </div>

    <!-- Image Viewer Modal -->
    <div id="img-modal" class="fixed inset-0 z-50 bg-slate-950/90 backdrop-blur-md hidden flex items-center justify-center p-4">
        <div class="glass w-full max-w-4xl max-h-[90vh] rounded-2xl flex flex-col border border-slate-700 shadow-2xl overflow-hidden">
            <div class="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
                <h3 id="img-modal-title" class="font-semibold text-lg text-slate-100 flex items-center gap-2">
                    <i class="fa-solid fa-image text-emerald-400"></i>
                    <span>Перегляд</span>
                </h3>
                <div class="flex items-center gap-2">
                    <div class="flex items-center bg-slate-800 rounded-lg border border-slate-700">
                        <button onclick="zoomImgOut()" class="px-2.5 py-1.5 text-slate-400 hover:text-white transition" title="Зменшити (Ctrl+Scroll)">
                            <i class="fa-solid fa-minus text-xs"></i>
                        </button>
                        <span id="img-zoom-label" class="px-2 py-1 text-xs text-slate-300 min-w-[52px] text-center select-none">Вписати</span>
                        <button onclick="zoomImgIn()" class="px-2.5 py-1.5 text-slate-400 hover:text-white transition" title="Збільшити (Ctrl+Scroll)">
                            <i class="fa-solid fa-plus text-xs"></i>
                        </button>
                    </div>
                    <button onclick="resetImgZoom()" class="px-2.5 py-1.5 text-slate-400 hover:text-white bg-slate-800 rounded-lg border border-slate-700 transition text-xs" title="Вписати у вікно">
                        <i class="fa-solid fa-expand"></i>
                    </button>
                    <button onclick="closeImgModal()" class="text-slate-400 hover:text-white p-1 rounded-lg">
                        <i class="fa-solid fa-xmark text-lg"></i>
                    </button>
                </div>
            </div>
            <div id="img-modal-container" class="p-4 flex-1 overflow-auto flex items-center justify-center bg-slate-950/50">
                <img id="img-modal-src" src="" alt="Документ" class="max-h-[70vh] max-w-full object-contain rounded-xl shadow-2xl" draggable="false">
            </div>
        </div>
    </div>

    <!-- Excel Preview Modal -->
    <div id="excel-modal" class="fixed inset-0 z-50 bg-slate-950/90 backdrop-blur-md hidden flex items-center justify-center p-4">
        <div class="glass w-full max-w-5xl max-h-[90vh] rounded-2xl flex flex-col border border-slate-700 shadow-2xl overflow-hidden">
            <div class="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
                <h3 id="excel-modal-title" class="font-semibold text-lg text-slate-100 flex items-center gap-2">
                    <i class="fa-solid fa-file-excel text-green-500"></i>
                    <span>Перегляд Excel</span>
                </h3>
                <div class="flex items-center gap-2">
                    <button id="excel-download-btn" onclick="" class="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-slate-200 text-sm font-medium rounded-lg transition">
                        <i class="fa-solid fa-download mr-1"></i> Завантажити
                    </button>
                    <button onclick="closeExcelModal()" class="text-slate-400 hover:text-white p-1 rounded-lg">
                        <i class="fa-solid fa-xmark text-lg"></i>
                    </button>
                </div>
            </div>
            <div class="p-4 flex-1 overflow-auto bg-slate-950/50">
                <div id="excel-modal-content" class="text-sm text-slate-300"></div>
            </div>
        </div>
    </div>

    <!-- Import Progress Overlay -->
    <div id="import-progress" class="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm hidden flex items-center justify-center p-4">
        <div class="glass w-full max-w-md rounded-2xl p-6 border border-blue-500/30 shadow-2xl text-center space-y-4">
            <div class="w-12 h-12 rounded-full bg-blue-500/10 text-blue-400 flex items-center justify-center mx-auto text-xl border border-blue-500/20">
                <i class="fa-solid fa-spinner fa-spin"></i>
            </div>
            <div>
                <h3 class="text-lg font-bold text-slate-100">Імпорт Excel</h3>
                <p id="import-status" class="text-sm text-blue-300 mt-1">Завантаження файлу...</p>
            </div>
            <div class="w-full bg-slate-800 rounded-full h-2">
                <div id="import-bar" class="bg-blue-500 h-2 rounded-full progress-bar" style="width: 0%"></div>
            </div>
            <p id="import-detail" class="text-xs text-slate-500"></p>
        </div>
    </div>

<script>
let allItems = [];
let allDocs = [];

function switchTab(tab) {
    const wh = document.getElementById('panel-warehouse');
    const dc = document.getElementById('panel-documents');
    const tw = document.getElementById('tab-warehouse');
    const td = document.getElementById('tab-documents');
    if (tab === 'warehouse') {
        wh.classList.remove('hidden'); dc.classList.add('hidden');
        tw.className = tw.className.replace('tab-inactive', 'tab-active');
        td.className = td.className.replace('tab-active', 'tab-inactive');
    } else {
        dc.classList.remove('hidden'); wh.classList.add('hidden');
        td.className = td.className.replace('tab-inactive', 'tab-active');
        tw.className = tw.className.replace('tab-active', 'tab-inactive');
    }
}

async function refreshAll() {
    await Promise.all([fetchItems(), fetchDocs()]);
}

// ---- Warehouse Items ----

async function fetchItems() {
    try {
        const res = await fetch('/api/warehouse/items');
        allItems = await res.json();
        document.getElementById('items-count').innerText = allItems.length;
        renderItems(allItems);
    } catch(e) {
        console.error(e);
    }
}

function renderItems(items) {
    const tbody = document.getElementById('items-tbody');
    document.getElementById('visible-items').innerText = items.length;
    if (items.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="py-12 text-center text-slate-500"><i class="fa-solid fa-boxes-stacked text-2xl mb-2 text-slate-600"></i><p>Склад порожній.</p></td></tr>';
        return;
    }
    let html = '';
    items.forEach(it => {
        const bal = it.balance || 0;
        const balClass = bal > 0 ? 'text-blue-400' : (bal < 0 ? 'text-red-400' : 'text-slate-500');
        html += `
        <tr class="hover:bg-slate-800/40 transition cursor-pointer" onclick="toggleTransactions(${it.id})">
            <td class="py-4 px-3"><i id="chevron-${it.id}" class="fa-solid fa-chevron-right text-[10px] text-slate-500 transition-transform"></i></td>
            <td class="py-4 px-3 font-mono text-xs text-slate-400">${esc(it.sku)}</td>
            <td class="py-4 px-3 font-medium text-slate-200">${esc(it.name)}</td>
            <td class="py-4 px-3 text-emerald-400 font-medium">${fmtNum(it.total_income)}</td>
            <td class="py-4 px-3 text-rose-400 font-medium">${fmtNum(it.total_expense)}</td>
            <td class="py-4 px-3 ${balClass} font-bold">${fmtNum(bal)}</td>
            <td class="py-4 px-3 text-slate-400">${esc(it.unit)}</td>
            <td class="py-4 px-3 text-slate-300">${esc(it.supplier)}</td>
            <td class="py-4 px-3 text-xs text-slate-400 max-w-[150px] truncate" title="${esc(it.notes)}">${esc(it.notes)}</td>
        </tr>
        <tr id="tx-row-${it.id}" class="hidden">
            <td colspan="9" class="p-0">
                <div class="expand-row px-8 py-3 border-t border-slate-800/40">
                    <div id="tx-content-${it.id}" class="text-xs text-slate-400">Завантаження...</div>
                </div>
            </td>
        </tr>`;
    });
    tbody.innerHTML = html;
}

async function toggleTransactions(itemId) {
    const row = document.getElementById('tx-row-' + itemId);
    const chevron = document.getElementById('chevron-' + itemId);
    if (!row.classList.contains('hidden')) {
        row.classList.add('hidden');
        chevron.style.transform = '';
        return;
    }
    row.classList.remove('hidden');
    chevron.style.transform = 'rotate(90deg)';

    const content = document.getElementById('tx-content-' + itemId);
    try {
        const res = await fetch('/api/warehouse/items/' + itemId + '/transactions');
        const txs = await res.json();
        if (txs.length === 0) {
            content.innerHTML = '<p class="text-slate-500 py-2">Немає транзакцій.</p>';
            return;
        }
        let h = '<table class="w-full"><thead><tr class="text-slate-500 text-[11px] uppercase">' +
            '<th class="py-1 pr-3 text-left">Дата</th><th class="py-1 pr-3 text-left">Тип</th>' +
            '<th class="py-1 pr-3 text-left">Тип док.</th>' +
            '<th class="py-1 pr-3 text-right">Кількість</th><th class="py-1 pr-3 text-left">№ накл.</th>' +
            '<th class="py-1 pr-3 text-right">Залишок</th><th class="py-1 pr-3 text-left">Документ</th>' +
            '<th class="py-1 pr-3 text-left">Джерело</th>' +
            '</tr></thead><tbody>';
        txs.forEach(tx => {
            const isInc = tx.operation_type === 'income';
            const badge = isInc ? 'badge-income' : 'badge-expense';
            const label = isInc ? 'Прихід' : 'Розхід';
            const sign = isInc ? '+' : '-';
            const date = tx.doc_date || formatTs(tx.created_at);
            const fileIcon = getFileIcon(tx.file_type);
            const docType = tx.doc_type || '';
            let docTypeBadge = '';
            if (docType === 'НАКЛАДНА') {
                docTypeBadge = '<span class="px-2 py-0.5 rounded-full text-[11px] font-medium badge-nakladna">Накл.</span>';
            } else if (docType === 'ВИМОГА') {
                docTypeBadge = '<span class="px-2 py-0.5 rounded-full text-[11px] font-medium badge-vymoha">Вимога</span>';
            } else if (docType) {
                docTypeBadge = `<span class="text-slate-400 text-[11px]">${esc(docType)}</span>`;
            }
            const srcRow = tx.source_row || '';
            h += `<tr class="border-t border-slate-800/30">
                <td class="py-2 pr-3 text-slate-300">${esc(date)}</td>
                <td class="py-2 pr-3"><span class="px-2 py-0.5 rounded-full text-[11px] font-medium ${badge}">${label}</span></td>
                <td class="py-2 pr-3">${docTypeBadge}</td>
                <td class="py-2 pr-3 text-right font-medium ${isInc ? 'text-emerald-400' : 'text-rose-400'}">${sign}${fmtNum(tx.quantity)}</td>
                <td class="py-2 pr-3 text-slate-300 font-mono">${esc(tx.doc_number)}</td>
                <td class="py-2 pr-3 text-right text-blue-400 font-medium">${fmtNum(tx.running_balance)}</td>
                <td class="py-2 pr-3">
                    <button onclick="event.stopPropagation(); viewDocument(${tx.document_id}, '${esc(tx.filename)}', '${tx.file_type}', '${esc(tx.source_row)}')"
                        class="text-slate-400 hover:text-blue-400 transition" title="${esc(tx.filename)}">
                        ${fileIcon} <span class="ml-1">${esc(tx.filename)}</span>
                    </button>
                </td>
                <td class="py-2 pr-3 text-slate-500 text-[11px] max-w-[200px] truncate" title="${esc(srcRow)}">${esc(srcRow)}</td>
            </tr>`;
        });
        h += '</tbody></table>';
        content.innerHTML = h;
    } catch(e) {
        content.innerHTML = '<p class="text-red-400">Помилка завантаження транзакцій.</p>';
    }
}

function filterItems() {
    const q = document.getElementById('search-items').value.toLowerCase().trim();
    if (!q) { renderItems(allItems); return; }
    const filtered = allItems.filter(it =>
        (it.name || '').toLowerCase().includes(q) ||
        (it.sku || '').toLowerCase().includes(q) ||
        (it.supplier || '').toLowerCase().includes(q)
    );
    renderItems(filtered);
}

// ---- Documents ----

async function fetchDocs() {
    try {
        const res = await fetch('/api/warehouse/documents');
        allDocs = await res.json();
        document.getElementById('docs-count').innerText = allDocs.length;
        renderDocs(allDocs);
    } catch(e) {
        console.error(e);
    }
}

function renderDocs(docs) {
    const tbody = document.getElementById('docs-tbody');
    if (docs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="py-12 text-center text-slate-500"><p>Документів немає.</p></td></tr>';
        return;
    }
    let html = '';
    docs.forEach(doc => {
        const icon = getFileIcon(doc.file_type);
        const typeLabel = doc.file_type === 'excel' ? 'Excel' : (doc.file_type === 'photo' ? 'Фото' : 'PDF');
        const date = formatTs(doc.uploaded_at);
        const docType = doc.doc_type || '';
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
        html += `
        <tr class="hover:bg-slate-800/40 transition cursor-pointer" onclick="toggleDocImpact(${doc.id})">
            <td class="py-4 px-3"><i id="doc-chevron-${doc.id}" class="fa-solid fa-chevron-right text-[10px] text-slate-500 transition-transform"></i></td>
            <td class="py-4 px-3">
                <button onclick="event.stopPropagation(); viewDocument(${doc.id}, '${esc(doc.filename)}', '${doc.file_type}')" class="${doc.file_type === 'excel' ? 'text-green-500 hover:text-green-400' : 'text-emerald-400 hover:text-emerald-300'}">
                    ${doc.file_type === 'excel' ? '<i class="fa-solid fa-file-excel text-2xl"></i>' : '<i class="fa-solid fa-image text-2xl"></i>'}
                </button>
            </td>
            <td class="py-4 px-3 font-medium text-slate-200">${esc(doc.filename)}</td>
            <td class="py-4 px-3"><span class="px-2 py-0.5 rounded-full text-[11px] font-medium badge-import">${typeLabel}</span></td>
            <td class="py-4 px-3">${docTypeBadge}</td>
            <td class="py-4 px-3 text-slate-300">${date}</td>
            <td class="py-4 px-3 font-mono text-slate-300">${esc(doc.doc_number)}</td>
            <td class="py-4 px-3 text-blue-400 font-medium">${doc.transaction_count}</td>
            <td class="py-4 px-3 text-right">
                <button onclick="event.stopPropagation(); openDeleteModal(${doc.id}, '${esc(doc.filename)}')" class="p-2 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition" title="Видалити">
                    <i class="fa-solid fa-trash"></i>
                </button>
            </td>
        </tr>
        <tr id="doc-impact-row-${doc.id}" class="hidden">
            <td colspan="9" class="p-0">
                <div class="expand-row px-8 py-3 border-t border-slate-800/40">
                    <div id="doc-impact-content-${doc.id}" class="text-xs text-slate-400">Завантаження...</div>
                </div>
            </td>
        </tr>`;
    });
    tbody.innerHTML = html;
}

async function toggleDocImpact(docId) {
    const row = document.getElementById('doc-impact-row-' + docId);
    const chevron = document.getElementById('doc-chevron-' + docId);
    if (!row.classList.contains('hidden')) {
        row.classList.add('hidden');
        chevron.style.transform = '';
        return;
    }
    row.classList.remove('hidden');
    chevron.style.transform = 'rotate(90deg)';

    const content = document.getElementById('doc-impact-content-' + docId);
    try {
        const res = await fetch('/api/warehouse/documents/' + docId + '/impact');
        const impacts = await res.json();
        if (impacts.length === 0) {
            content.innerHTML = '<p class="text-slate-500 py-2">Документ не вплинув на жодну позицію.</p>';
            return;
        }
        let h = '<table class="w-full"><thead><tr class="text-slate-500 text-[11px] uppercase">' +
            '<th class="py-1 pr-3 text-left">Ном. номер</th><th class="py-1 pr-3 text-left">Найменування</th>' +
            '<th class="py-1 pr-3 text-left">Тип</th><th class="py-1 pr-3 text-right">Кількість</th>' +
            '<th class="py-1 pr-3 text-left">Од.</th><th class="py-1 pr-3 text-left">Джерело</th>' +
            '</tr></thead><tbody>';
        impacts.forEach(imp => {
            const isInc = imp.operation_type === 'income';
            const badge = isInc ? 'badge-income' : 'badge-expense';
            const label = isInc ? 'Прихід' : 'Розхід';
            const sign = isInc ? '+' : '-';
            const srcRow = imp.source_row || '';
            h += `<tr class="border-t border-slate-800/30">
                <td class="py-2 pr-3 font-mono text-slate-400">${esc(imp.sku)}</td>
                <td class="py-2 pr-3 text-slate-200">${esc(imp.name)}</td>
                <td class="py-2 pr-3"><span class="px-2 py-0.5 rounded-full text-[11px] font-medium ${badge}">${label}</span></td>
                <td class="py-2 pr-3 text-right font-medium ${isInc ? 'text-emerald-400' : 'text-rose-400'}">${sign}${fmtNum(imp.quantity)}</td>
                <td class="py-2 pr-3 text-slate-400">${esc(imp.unit)}</td>
                <td class="py-2 pr-3 text-slate-500 text-[11px] max-w-[250px] truncate" title="${esc(srcRow)}">${esc(srcRow)}</td>
            </tr>`;
        });
        h += '</tbody></table>';
        content.innerHTML = h;
    } catch(e) {
        content.innerHTML = '<p class="text-red-400">Помилка завантаження.</p>';
    }
}

// ---- Import / Export ----

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

// ---- Document viewing ----

function viewDocument(docId, filename, fileType, sourceRow) {
    if (fileType === 'excel') {
        let highlightRows = [];
        if (sourceRow) {
            const m = sourceRow.match(/Рядок\s+(\d+)/);
            if (m) highlightRows.push(parseInt(m[1]));
        }
        openExcelPreview(docId, filename, highlightRows);
        return;
    }
    resetImgZoom();
    const img = document.getElementById('img-modal-src');
    img.src = '/api/warehouse/documents/' + docId + '/view';
    document.getElementById('img-modal-title').innerHTML = '<i class="fa-solid fa-image text-emerald-400"></i> ' + esc(filename);
    document.getElementById('img-modal').classList.remove('hidden');
}
function closeImgModal() {
    document.getElementById('img-modal').classList.add('hidden');
    resetImgZoom();
}

let imgZoom = 1;
let imgFitMode = true;

function getEffectiveZoom() {
    if (!imgFitMode) return imgZoom;
    const img = document.getElementById('img-modal-src');
    if (!img.naturalWidth) return 1;
    return img.clientWidth / img.naturalWidth;
}
function setImgZoom(level) {
    const img = document.getElementById('img-modal-src');
    const container = document.getElementById('img-modal-container');
    imgZoom = Math.max(0.05, Math.min(10, level));
    imgFitMode = false;
    img.style.maxWidth = 'none';
    img.style.maxHeight = 'none';
    img.style.width = (img.naturalWidth * imgZoom) + 'px';
    img.style.height = 'auto';
    container.style.justifyContent = 'flex-start';
    container.style.alignItems = 'flex-start';
    updateZoomLabel();
}
function zoomImgIn() { setImgZoom((imgFitMode ? getEffectiveZoom() : imgZoom) * 1.25); }
function zoomImgOut() { setImgZoom((imgFitMode ? getEffectiveZoom() : imgZoom) / 1.25); }
function resetImgZoom() {
    const img = document.getElementById('img-modal-src');
    const container = document.getElementById('img-modal-container');
    imgZoom = 1;
    imgFitMode = true;
    img.style.maxWidth = '';
    img.style.maxHeight = '';
    img.style.width = '';
    img.style.height = '';
    container.style.justifyContent = '';
    container.style.alignItems = '';
    updateZoomLabel();
}
function updateZoomLabel() {
    const el = document.getElementById('img-zoom-label');
    if (!el) return;
    el.textContent = imgFitMode ? 'Вписати' : (Math.round(imgZoom * 100) + '%');
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

// ---- Delete ----

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

// ---- Helpers ----

function esc(s) {
    return String(s || '').replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]));
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

document.addEventListener('DOMContentLoaded', function() {
    refreshAll();
    document.getElementById('img-modal-container').addEventListener('wheel', function(e) {
        if (!e.ctrlKey) return;
        e.preventDefault();
        const z = imgFitMode ? getEffectiveZoom() : imgZoom;
        setImgZoom(e.deltaY < 0 ? z * 1.15 : z / 1.15);
    }, {passive: false});
});
</script>
</body>
</html>
"""


class WebServer:

    def __init__(
        self,
        warehouse_db: WarehouseDB,
        file_store: FileStore,
        vector_store: Optional[VectorStore],
        owner_user_id: int,
        host: str = "127.0.0.1",
        port: int = 8000,
    ) -> None:
        self._db = warehouse_db
        self._fs = file_store
        self._vs = vector_store
        self._owner_id = owner_user_id
        self._host = host
        self._port = port

        self._app = web.Application(client_max_size=50 * 1024 * 1024)
        self._setup_routes()
        self._runner: web.AppRunner | None = None
        self._site: web.TCPSite | None = None

    def _setup_routes(self) -> None:
        self._app.router.add_get("/", self._index)
        self._app.router.add_get("/api/warehouse/items", self._api_items)
        self._app.router.add_get("/api/warehouse/items/{item_id}/transactions", self._api_item_transactions)
        self._app.router.add_get("/api/warehouse/documents", self._api_documents)
        self._app.router.add_get("/api/warehouse/documents/{doc_id}/impact", self._api_document_impact)
        self._app.router.add_get("/api/warehouse/documents/{doc_id}/view", self._api_document_view)
        self._app.router.add_get("/api/warehouse/documents/{doc_id}/download", self._api_document_download)
        self._app.router.add_get("/api/warehouse/documents/{doc_id}/preview", self._api_document_preview)
        self._app.router.add_delete("/api/warehouse/documents/{doc_id}", self._api_delete_document)
        self._app.router.add_post("/api/warehouse/import", self._api_import_excel)
        self._app.router.add_get("/api/warehouse/export", self._api_export_excel)

    async def _index(self, request: web.Request) -> web.Response:
        return web.Response(text=HTML_PAGE, content_type="text/html")

    async def _api_items(self, request: web.Request) -> web.Response:
        items = self._db.get_items_with_balance()
        return web.json_response(items)

    async def _api_item_transactions(self, request: web.Request) -> web.Response:
        item_id = int(request.match_info["item_id"])
        txs = self._db.get_item_transactions(item_id)
        return web.json_response(txs)

    async def _api_documents(self, request: web.Request) -> web.Response:
        docs = self._db.get_documents()
        return web.json_response(docs)

    async def _api_document_impact(self, request: web.Request) -> web.Response:
        doc_id = int(request.match_info["doc_id"])
        impact = self._db.get_document_impact(doc_id)
        return web.json_response(impact)

    async def _api_document_view(self, request: web.Request) -> web.Response:
        doc_id = int(request.match_info["doc_id"])
        doc = self._db.get_document(doc_id)
        if not doc:
            return web.json_response({"error": "Документ не знайдено"}, status=404)
        file_path = doc["file_path"]
        if not file_path or not os.path.exists(file_path):
            return web.json_response({"error": "Файл відсутній на диску"}, status=404)
        ct = "image/jpeg"
        if file_path.endswith(".png"):
            ct = "image/png"
        elif file_path.endswith(".pdf"):
            ct = "application/pdf"
        elif file_path.endswith(".xlsx"):
            ct = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        return web.FileResponse(path=file_path, headers={"Content-Type": ct})

    async def _api_document_download(self, request: web.Request) -> web.Response:
        doc_id = int(request.match_info["doc_id"])
        doc = self._db.get_document(doc_id)
        if not doc:
            return web.json_response({"error": "Документ не знайдено"}, status=404)
        file_path = doc["file_path"]
        if not file_path or not os.path.exists(file_path):
            return web.json_response({"error": "Файл відсутній"}, status=404)
        return web.FileResponse(
            path=file_path,
            headers={"Content-Disposition": f'attachment; filename="{doc["filename"]}"'},
        )

    async def _api_delete_document(self, request: web.Request) -> web.Response:
        doc_id = int(request.match_info["doc_id"])
        doc = self._db.get_document(doc_id)
        if not doc:
            return web.json_response({"error": "Документ не знайдено"}, status=404)

        file_path = doc.get("file_path", "")

        ok = self._db.delete_document(doc_id)
        if not ok:
            return web.json_response({"error": "Документ не знайдено"}, status=404)

        if file_path:
            chroma_doc_id = os.path.splitext(os.path.basename(file_path))[0]
            if self._vs and len(chroma_doc_id) == 10:
                try:
                    self._vs.delete(chroma_doc_id)
                except Exception:
                    pass
            try:
                os.remove(file_path)
            except FileNotFoundError:
                pass

        return web.json_response({"success": True})

    async def _api_document_preview(self, request: web.Request) -> web.Response:
        from kolobot.excel_service import preview_excel

        doc_id = int(request.match_info["doc_id"])
        doc = self._db.get_document(doc_id)
        if not doc:
            return web.json_response({"error": "Документ не знайдено"}, status=404)
        file_path = doc["file_path"]
        if not file_path or not os.path.exists(file_path):
            return web.json_response({"error": "Файл відсутній на диску"}, status=404)
        try:
            max_rows = 100
            highlight_param = request.query.get("highlight", "")
            if highlight_param:
                try:
                    highlight_nums = [int(x) for x in highlight_param.split(",") if x.strip()]
                    if highlight_nums:
                        max_rows = max(max_rows, max(highlight_nums) + 5)
                except ValueError:
                    pass
            data = preview_excel(file_path, max_rows=max_rows)
            return web.json_response(data)
        except Exception as exc:
            return web.json_response({"error": f"Помилка читання: {exc}"}, status=400)

    async def _api_import_excel(self, request: web.Request) -> web.Response:
        from kolobot.excel_service import parse_excel

        reader = await request.multipart()
        field = await reader.next()
        if field is None or field.name != "file":
            return web.json_response({"error": "Файл не надано"}, status=400)

        filename = field.filename or "import.xlsx"
        data = await field.read()

        logger.info("[Excel Import] Отримано файл: %s (%d байт)", filename, len(data))

        tmp_dir = os.path.join(self._fs._base, "tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        tmp_path = os.path.join(tmp_dir, f"import_{int(time.time())}_{filename}")
        with open(tmp_path, "wb") as f:
            f.write(data)

        logger.info("[Excel Import] Парсинг файлу...")
        try:
            doc_type, rows = parse_excel(tmp_path)
        except Exception as exc:
            logger.error("[Excel Import] Помилка парсингу: %s", exc)
            os.remove(tmp_path)
            return web.json_response({"error": f"Помилка парсингу: {exc}"}, status=400)

        if not rows:
            os.remove(tmp_path)
            logger.warning("[Excel Import] Файл порожній або структура не розпізнана")
            return web.json_response({"error": "Файл порожній або структура не розпізнана"}, status=400)

        logger.info("[Excel Import] Тип документу: %s, рядків: %d", doc_type or "не визначено", len(rows))

        final_path = os.path.join(str(self._fs._base), f"excel_{int(time.time())}_{filename}")
        os.replace(tmp_path, final_path)

        doc_id = self._db.add_document(
            filename=filename,
            file_type="excel",
            file_path=final_path,
            doc_type=doc_type,
        )

        items_created = 0
        items_updated = 0
        transactions_created = 0

        is_nakladna = doc_type == "НАКЛАДНА"
        is_vymoha = doc_type == "ВИМОГА"

        for i, row in enumerate(rows, 1):
            logger.info("[Excel Import] Обробка рядка %d/%d: %s", i, len(rows), row.get("name", ""))
            existing = self._db.find_item(sku=row.get("sku", ""), name=row["name"])
            if existing:
                item_id = existing["id"]
                items_updated += 1
                self._db.update_item(
                    item_id,
                    sku=row.get("sku", ""),
                    unit=row.get("unit", ""),
                    supplier=row.get("supplier", ""),
                    notes=row.get("notes", ""),
                )
            else:
                item_id = self._db.add_item(
                    name=row["name"],
                    sku=row.get("sku", ""),
                    unit=row.get("unit", ""),
                    supplier=row.get("supplier", ""),
                    notes=row.get("notes", ""),
                )
                items_created += 1

            source_row = row.get("source_row", "")
            row_doc_type = row.get("doc_type", "") or doc_type

            income = row.get("income")
            expense = row.get("expense")
            balance = row.get("balance")

            if is_nakladna or row_doc_type == "НАКЛАДНА":
                qty = 0.0
                if income and float(income) > 0:
                    qty = float(income)
                elif expense and float(expense) > 0:
                    qty = float(expense)
                elif balance and float(balance) > 0:
                    qty = float(balance)
                if qty > 0:
                    self._db.add_transaction(
                        item_id=item_id, document_id=doc_id,
                        operation_type="income", quantity=qty,
                        doc_number=row.get("doc_number", ""),
                        doc_date=row.get("doc_date", ""),
                        source_row=source_row,
                    )
                    transactions_created += 1
            elif is_vymoha or row_doc_type == "ВИМОГА":
                qty = 0.0
                if expense and float(expense) > 0:
                    qty = float(expense)
                elif income and float(income) > 0:
                    qty = float(income)
                elif balance and float(balance) > 0:
                    qty = float(balance)
                if qty > 0:
                    self._db.add_transaction(
                        item_id=item_id, document_id=doc_id,
                        operation_type="expense", quantity=qty,
                        doc_number=row.get("doc_number", ""),
                        doc_date=row.get("doc_date", ""),
                        source_row=source_row,
                    )
                    transactions_created += 1
            else:
                if income and float(income) > 0:
                    self._db.add_transaction(
                        item_id=item_id, document_id=doc_id,
                        operation_type="income", quantity=float(income),
                        doc_number=row.get("doc_number", ""),
                        doc_date=row.get("doc_date", ""),
                        source_row=source_row,
                    )
                    transactions_created += 1
                if expense and float(expense) > 0:
                    self._db.add_transaction(
                        item_id=item_id, document_id=doc_id,
                        operation_type="expense", quantity=float(expense),
                        doc_number=row.get("doc_number", ""),
                        doc_date=row.get("doc_date", ""),
                        source_row=source_row,
                    )
                    transactions_created += 1

                if not income and not expense and balance and float(balance) > 0:
                    self._db.add_transaction(
                        item_id=item_id, document_id=doc_id,
                        operation_type="income", quantity=float(balance),
                        doc_number=row.get("doc_number", ""),
                        doc_date=row.get("doc_date", ""),
                        source_row=source_row,
                    )
                    transactions_created += 1

        logger.info("[Excel Import] Завершено: %d нових, %d оновлено, %d транзакцій",
                    items_created, items_updated, transactions_created)

        return web.json_response({
            "success": True,
            "doc_type": doc_type,
            "items_created": items_created,
            "items_updated": items_updated,
            "transactions_created": transactions_created,
        })

    async def _api_export_excel(self, request: web.Request) -> web.Response:
        from kolobot.excel_service import export_excel

        items = self._db.get_items_with_balance()
        data = export_excel(items)
        return web.Response(
            body=data,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="warehouse_export.xlsx"'},
        )

    async def start(self) -> None:
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, self._host, self._port)
        await self._site.start()
        logger.info("WebServer running on http://%s:%s", self._host, self._port)

    async def stop(self) -> None:
        if self._runner:
            await self._runner.cleanup()
            logger.info("WebServer stopped.")
