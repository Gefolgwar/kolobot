"""Embedded aiohttp web server: warehouse inventory UI with two tabs + REST API."""

from __future__ import annotations

import asyncio
import datetime
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

from aiohttp import web

from kolobot.file_store import FileStore
from kolobot.log_service import LogBuffer, LogEntry, get_global_log_buffer, setup_logging_capture
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
        .badge-queued { background: rgba(245,158,11,0.15); color: #fbbf24; }
        .badge-ocr { background: rgba(59,130,246,0.15); color: #60a5fa; }
        .badge-emb { background: rgba(168,85,247,0.15); color: #c084fc; }
        .progress-bar { transition: width 0.3s ease; }
        .cursor-blink { animation: blink 1s step-end infinite; }
        @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
        .log-terminal { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }
        /* Компактизація таблиць: Tailwind підключається з CDN і вставляє свої утиліти в <head>
           пізніше за цей <style>, тому без !important правила програють класам px-3 / py-4.
           Клітинки з colspan (порожній стан і розгорнуті деталі) не чіпаємо — у них свої відступи. */
        .compact-table > thead > tr > th,
        .compact-table > tbody > tr > td:not([colspan]) { padding: 8px !important; }
        .compact-table > thead > tr > th { font-size: 10px !important; }
        /* Картковий режим: нижче 1000px таблиця з класом-маркером .card-table стає картками.
           Перемикання робить виключно CSS — у JS лишається один шаблон рядка, а підпис
           клітинки береться з її атрибута data-label (текст дорівнює відповідному <th>).
           Клітинки без data-label (шеврон і повноширинні блоки деталей) префікса не отримують.
           Клас-маркер увімкнено явно, тому таблиці, ще не переведені на картки, не ламаються. */
        @media (max-width: 999.98px) {
            .card-table thead { display: none; }
            .card-table,
            .card-table > tbody { display: block; width: 100%; }
            .card-table > tbody > tr:not(.hidden) {
                display: block;
                position: relative;
                margin-bottom: 0.75rem;
                padding: 0.75rem;
                border: 1px solid rgba(30, 41, 59, 0.9);
                border-radius: 0.75rem;
                background: rgba(15, 23, 42, 0.45);
            }
            .card-table > tbody > tr > td,
            .card-table > tbody > tr > td:not([colspan]) {
                display: block;
                width: auto;
                padding: 2px 0 !important;
                text-align: left !important;
            }
            .card-table > tbody > tr > td[colspan] { padding: 0 !important; }
            .card-table > tbody > tr > td[data-label]::before {
                content: attr(data-label) ": ";
                font-size: 10px;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                color: #94a3b8;
            }
            .card-table > tbody > tr > td:not([data-label])::before { content: none; }
            /* Кнопки в картці мусять бути видимими без наведення миші */
            .card-table > tbody > tr > td button { opacity: 1 !important; }
            /* Внутрішні flex-контейнери клітинок притискаємо до лівого краю */
            .card-table > tbody > tr > td > div.flex,
            .card-table > tbody > tr > td > span.flex { justify-content: flex-start !important; }
            /* Шеврон переїжджає у правий верхній кут картки: як окрема перша клітинка
               він інакше стає порожнім рядком угорі, який не читається як керування. */
            .card-table > tbody > tr:not(.hidden) > td:first-child:not([colspan]) {
                position: absolute;
                top: 0.75rem;
                right: 0.75rem;
                width: auto;
                padding: 0 !important;
            }
            /* Числа й дати не розриваються посеред значення */
            .card-table > tbody > tr > td[data-label="Дата завантаження"],
            .card-table > tbody > tr > td[data-label="№ документа"],
            .card-table > tbody > tr > td[data-label="Позицій"],
            .card-table > tbody > tr > td[data-label="Прихід"],
            .card-table > tbody > tr > td[data-label="Розхід"],
            .card-table > tbody > tr > td[data-label="Залишок"],
            .card-table > tbody > tr > td[data-label="Мін. залишок"] { white-space: nowrap; }
            /* Підсвітка «нижче мінімуму»: рамка й тло картки специфічніші за утиліти Tailwind
               з CDN, тому бордюр і тон позиції доводиться повертати явно за маркером row-low. */
            .card-table > tbody > tr.row-low {
                border-left: 4px solid #f43f5e !important;
                background: rgba(76, 5, 25, 0.55) !important;
            }
            /* Вкладені таблиці (історія транзакцій і позиції документа) — теж картки, але
               без шеврона: їхня перша клітинка є змістовною колонкою, тож правило правого
               верхнього кута з #21 до них не застосовується. Селектор із двома .card-table
               специфічніший за нього, тому скидання перемагає без !important на position. */
            .card-table .card-table > tbody > tr:not(.hidden) > td:first-child:not([colspan]) {
                position: static;
                width: auto;
                padding: 2px 0 !important;
            }
            /* Дати, кількості й номери накладних не рвуться посеред значення */
            .card-table > tbody > tr > td[data-label="Дата"],
            .card-table > tbody > tr > td[data-label="Кількість"],
            .card-table > tbody > tr > td[data-label="№ накл."] { white-space: nowrap; }
        }
    </style>
</head>
<body class="min-h-screen font-sans pb-12">
    <!-- Header -->
    <header class="glass sticky top-0 z-30 border-b border-slate-800 px-6 py-4 mb-0">
        <div class="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-y-2">
            <div class="flex items-center space-x-3">
                <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center text-white font-bold text-xl shadow-lg shadow-blue-500/20">
                    <i class="fa-solid fa-warehouse"></i>
                </div>
                <div>
                    <h1 class="text-xl font-bold text-slate-100">kolobot</h1>
                    <p class="text-xs text-slate-400">Складський облік</p>
                </div>
            </div>
            <div class="flex flex-wrap items-center space-x-2 gap-y-2">
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
            <button id="tab-logs" onclick="switchTab('logs')" class="pb-3 px-1 text-sm font-semibold tab-inactive transition flex items-center">
                <i class="fa-solid fa-terminal mr-1.5 text-xs"></i> Log
                <span id="logs-count" class="ml-1.5 px-2 py-0.5 bg-slate-800 text-slate-400 rounded-full text-xs font-mono">0</span>
            </button>
        </div>
    </div>

    <!-- Warehouse Tab -->
    <main id="panel-warehouse" class="max-w-7xl mx-auto px-6">
        <div class="glass rounded-2xl p-4 mb-6 space-y-3">
            <div class="flex flex-col sm:flex-row items-center justify-between gap-4">
                <div class="relative w-full sm:w-96">
                    <i class="fa-solid fa-magnifying-glass absolute left-3.5 top-3.5 text-slate-500"></i>
                    <input type="text" id="search-items" onkeyup="filterItems()" placeholder="Пошук за назвою або номенклатурним номером..."
                        class="w-full bg-slate-900/80 text-sm text-slate-200 pl-10 pr-4 py-2.5 rounded-xl border border-slate-700/60 focus:outline-none focus:border-blue-500 transition">
                </div>
                <div class="text-xs text-slate-400">
                    Показано: <span id="visible-items" class="font-bold text-slate-200">0</span>
                </div>
            </div>
            <div class="flex items-center gap-2 flex-wrap">
                <span class="text-xs text-slate-500 mr-0.5"><i class="fa-solid fa-filter"></i></span>
                <button onclick="setFilter('below-min')" id="filter-below-min" class="px-2.5 py-1 text-xs font-medium rounded-lg border border-slate-700/60 text-slate-400 bg-slate-900/50 hover:bg-slate-800/80 transition flex items-center gap-1.5">
                    <i class="fa-solid fa-triangle-exclamation text-rose-400"></i> Менше мінімального залишку
                    <span id="filter-below-min-count" class="px-1.5 py-0.5 bg-slate-800 rounded text-[10px] min-w-[20px] text-center">0</span>
                </button>
                <button onclick="setFilter('negative')" id="filter-negative" class="px-2.5 py-1 text-xs font-medium rounded-lg border border-slate-700/60 text-slate-400 bg-slate-900/50 hover:bg-slate-800/80 transition flex items-center gap-1.5">
                    <i class="fa-solid fa-arrow-trend-down"></i> Від'ємний залишок
                    <span id="filter-negative-count" class="px-1.5 py-0.5 bg-slate-800 rounded text-[10px] min-w-[20px] text-center">0</span>
                </button>
                <button onclick="setFilter('no-docs')" id="filter-no-docs" class="px-2.5 py-1 text-xs font-medium rounded-lg border border-slate-700/60 text-slate-400 bg-slate-900/50 hover:bg-slate-800/80 transition flex items-center gap-1.5">
                    <i class="fa-solid fa-file-circle-xmark"></i> Без документу
                    <span id="filter-no-docs-count" class="px-1.5 py-0.5 bg-slate-800 rounded text-[10px] min-w-[20px] text-center">0</span>
                </button>
                <button onclick="setFilter('dup-names')" id="filter-dup-names" class="px-2.5 py-1 text-xs font-medium rounded-lg border border-slate-700/60 text-slate-400 bg-slate-900/50 hover:bg-slate-800/80 transition flex items-center gap-1.5">
                    <i class="fa-solid fa-clone"></i> Однакові назви
                    <span id="filter-dup-names-count" class="px-1.5 py-0.5 bg-slate-800 rounded text-[10px] min-w-[20px] text-center">0</span>
                </button>
                <button onclick="setFilter('zeros')" id="filter-zeros" class="px-2.5 py-1 text-xs font-medium rounded-lg border border-slate-700/60 text-slate-400 bg-slate-900/50 hover:bg-slate-800/80 transition flex items-center gap-1.5">
                    <i class="fa-solid fa-circle-dot"></i> Скрізь нулі
                    <span id="filter-zeros-count" class="px-1.5 py-0.5 bg-slate-800 rounded text-[10px] min-w-[20px] text-center">0</span>
                </button>
            </div>
        </div>

        <div class="glass rounded-2xl border border-slate-800 overflow-hidden shadow-2xl">
            <div class="overflow-x-auto">
                <table class="w-full text-left border-collapse compact-table card-table">
                    <thead>
                        <tr class="bg-slate-900/90 text-slate-400 text-xs font-semibold uppercase border-b border-slate-800">
                            <th class="py-4 px-3 w-8"></th>
                            <th class="py-4 px-3">Ном. номер</th>
                            <th class="py-4 px-3">Найменування</th>
                            <th class="py-4 px-3">Прихід</th>
                            <th class="py-4 px-3">Розхід</th>
                            <th class="py-4 px-3">Залишок</th>
                            <th class="py-4 px-3">Мін. залишок</th>
                            <th class="py-4 px-3">Од.виміру</th>
                            <th class="py-4 px-3">Постачальник</th>
                            <th class="py-4 px-3">Примітки</th>
                        </tr>
                    </thead>
                    <tbody id="items-tbody" class="divide-y divide-slate-800/60 text-sm">
                        <tr><td colspan="10" class="py-12 text-center text-slate-500">
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
                <table class="w-full text-left border-collapse compact-table card-table">
                    <thead>
                        <tr class="bg-slate-900/90 text-slate-400 text-xs font-semibold uppercase border-b border-slate-800">
                            <th class="py-4 px-3 w-8"></th>
                            <th class="py-4 px-3">Превʼю</th>
                            <th class="py-4 px-3">Файл</th>
                            <th class="py-4 px-3">Тип</th>
                            <th class="py-4 px-3">Тип документу</th>
                            <th class="py-4 px-3">Статус</th>
                            <th class="py-4 px-3">Дата завантаження</th>
                            <th class="py-4 px-3">№ документа</th>
                            <th class="py-4 px-3">Затребував</th>
                            <th class="py-4 px-3">Через кого</th>
                            <th class="py-4 px-3">Позицій</th>
                            <th class="py-4 px-3 text-right">Дії</th>
                        </tr>
                    </thead>
                    <tbody id="docs-tbody" class="divide-y divide-slate-800/60 text-sm">
                        <tr><td colspan="12" class="py-12 text-center text-slate-500">
                            <p>Документів немає.</p>
                        </td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    </main>

    <!-- Log Tab -->
    <main id="panel-logs" class="max-w-7xl mx-auto px-6 hidden">
        <div class="rounded-2xl border border-slate-800/80 bg-[#090d16] shadow-2xl overflow-hidden flex flex-col">
            <!-- Terminal Header -->
            <div class="px-4 py-3 bg-[#0d1322] border-b border-slate-800 flex flex-wrap items-center justify-between gap-3 select-none">
                <!-- Left: macOS Window Controls & Title -->
                <div class="flex items-center space-x-2">
                    <div class="flex items-center space-x-1.5">
                        <span class="w-3 h-3 rounded-full bg-[#ff5f56] inline-block shadow-sm"></span>
                        <span class="w-3 h-3 rounded-full bg-[#ffbd2e] inline-block shadow-sm"></span>
                        <span class="w-3 h-3 rounded-full bg-[#27c93f] inline-block shadow-sm"></span>
                    </div>
                    <span class="font-mono text-xs font-semibold text-emerald-400/90 ml-2">~/logs</span>
                </div>

                <!-- Center: Grep Search Input -->
                <div class="relative flex-1 min-w-[180px] max-w-md mx-1">
                    <i class="fa-solid fa-magnifying-glass absolute left-3 top-2.5 text-slate-500 text-xs"></i>
                    <input type="text" id="log-search-input" oninput="onLogFilterChange()" placeholder="grep logs..."
                        class="w-full bg-[#070b14] text-xs text-slate-200 pl-8 pr-3 py-1.5 rounded-lg border border-slate-700/60 focus:outline-none focus:border-sky-500 font-mono transition">
                </div>

                <!-- Log Level Badges / Filters -->
                <div class="flex items-center gap-1.5 flex-wrap">
                    <label class="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold font-mono cursor-pointer transition select-none bg-sky-500/10 text-sky-400 border border-sky-500/30 hover:bg-sky-500/20">
                        <input type="checkbox" id="lvl-info" checked onchange="onLogFilterChange()" class="rounded border-sky-400 text-sky-500 focus:ring-0 w-3.5 h-3.5 accent-sky-500">
                        <span>INFO</span>
                    </label>
                    <label class="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold font-mono cursor-pointer transition select-none bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/20">
                        <input type="checkbox" id="lvl-success" checked onchange="onLogFilterChange()" class="rounded border-emerald-400 text-emerald-500 focus:ring-0 w-3.5 h-3.5 accent-emerald-500">
                        <span>SUCCESS</span>
                    </label>
                    <label class="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold font-mono cursor-pointer transition select-none bg-amber-500/10 text-amber-400 border border-amber-500/30 hover:bg-amber-500/20">
                        <input type="checkbox" id="lvl-warn" checked onchange="onLogFilterChange()" class="rounded border-amber-400 text-amber-500 focus:ring-0 w-3.5 h-3.5 accent-amber-500">
                        <span>WARN</span>
                    </label>
                    <label class="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold font-mono cursor-pointer transition select-none bg-rose-500/10 text-rose-400 border border-rose-500/30 hover:bg-rose-500/20">
                        <input type="checkbox" id="lvl-err" checked onchange="onLogFilterChange()" class="rounded border-rose-400 text-rose-500 focus:ring-0 w-3.5 h-3.5 accent-rose-500">
                        <span>ERR</span>
                    </label>
                </div>

                <!-- Right Controls: Ratio, Auto-Scroll, Clear -->
                <div class="flex items-center space-x-3">
                    <span id="log-count-ratio" class="font-mono text-xs text-sky-400/90 font-medium px-2 py-0.5 bg-[#070b14] rounded border border-slate-800">0/0</span>
                    <label class="flex items-center gap-1.5 cursor-pointer select-none text-[11px] font-bold tracking-wider text-slate-400 hover:text-slate-300">
                        <span>AUTO-SCROLL</span>
                        <div class="relative">
                            <input type="checkbox" id="log-autoscroll" checked class="sr-only peer" onchange="toggleAutoScroll()">
                            <div class="w-8 h-4 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-emerald-500"></div>
                        </div>
                    </label>
                    <button onclick="clearLogsServer()" class="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition" title="Очистити логи">
                        <i class="fa-solid fa-trash-can text-sm"></i>
                    </button>
                </div>
            </div>

            <!-- Terminal Body -->
            <div id="log-terminal" class="p-4 bg-[#060911] h-[600px] max-h-[75vh] overflow-y-auto font-mono text-[12px] leading-relaxed text-slate-300 space-y-0.5 select-text scroll-smooth border-t border-slate-900">
                <div id="log-lines" class="space-y-0.5"></div>
                <div id="log-empty-state" class="text-slate-600 italic py-6 text-center select-none">
                    [System] Очікування подій та повідомлень консолі...
                </div>
                <div id="log-cursor" class="text-emerald-400 font-mono text-xs pt-1 flex items-center gap-1 select-none">
                    <span class="text-slate-600">$</span> <span class="cursor-blink">▌</span>
                </div>
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

    <!-- Image Viewer Modal with Side-by-Side OCR Preview -->
    <div id="img-modal" class="fixed inset-0 z-50 bg-slate-950/90 backdrop-blur-md hidden flex items-center justify-center p-4">
        <div class="glass w-full max-w-7xl max-h-[92vh] rounded-2xl flex flex-col border border-slate-700 shadow-2xl overflow-hidden">
            <div class="px-6 py-3 border-b border-slate-800 flex flex-wrap items-center justify-between gap-y-2">
                <h3 id="img-modal-title" class="font-semibold text-lg text-slate-100 flex items-center gap-2">
                    <i class="fa-solid fa-image text-emerald-400"></i>
                    <span>Перегляд</span>
                </h3>
                <div class="flex flex-wrap items-center gap-2">
                    <div class="flex items-center bg-slate-800 rounded-lg border border-slate-700">
                        <button id="img-zoom-out-btn" onclick="zoomImgOut()" class="px-2.5 py-1.5 text-slate-400 hover:text-white transition disabled:opacity-30 disabled:cursor-not-allowed" title="Зменшити (Ctrl+Scroll)">
                            <i class="fa-solid fa-minus text-xs"></i>
                        </button>
                        <span id="img-zoom-label" class="px-2 py-1 text-xs text-slate-300 min-w-[56px] text-center select-none font-mono">100%</span>
                        <button id="img-zoom-in-btn" onclick="zoomImgIn()" class="px-2.5 py-1.5 text-slate-400 hover:text-white transition disabled:opacity-30 disabled:cursor-not-allowed" title="Збільшити (Ctrl+Scroll)">
                            <i class="fa-solid fa-plus text-xs"></i>
                        </button>
                    </div>
                    <button onclick="resetImgZoom()" class="px-2.5 py-1.5 text-slate-400 hover:text-white bg-slate-800 rounded-lg border border-slate-700 transition text-xs" title="Скинути масштаб (100%)">
                        <i class="fa-solid fa-expand"></i>
                    </button>
                    <button id="toggle-ocr-btn" onclick="toggleOcrPanel()" class="px-3 py-1.5 text-xs font-medium rounded-lg bg-blue-600/20 text-blue-400 border border-blue-500/30 hover:bg-blue-600/30 transition flex items-center gap-1.5" title="Показати/приховати текст OCR">
                        <i class="fa-solid fa-align-left"></i>
                        <span id="toggle-ocr-label">Текст OCR</span>
                    </button>
                    <button onclick="closeImgModal()" class="text-slate-400 hover:text-white p-1 rounded-lg">
                        <i class="fa-solid fa-xmark text-lg"></i>
                    </button>
                </div>
            </div>
            <div class="flex-1 flex overflow-hidden min-h-[420px]">
                <!-- Left: Image Canvas -->
                <div id="img-modal-container" class="flex-1 overflow-auto flex bg-slate-950/70 relative p-4 min-w-0">
                    <img id="img-modal-src" src="" alt="Документ" class="rounded-xl shadow-2xl m-auto shrink-0 select-none" draggable="false">
                </div>
                <!-- Right: OCR / Recognized Content Panel -->
                <div id="ocr-panel" class="w-[440px] max-w-[45vw] border-l border-slate-800 bg-slate-900/95 flex flex-col overflow-hidden">
                    <div class="p-3.5 border-b border-slate-800 flex items-center justify-between">
                        <div class="flex items-center gap-2">
                            <span class="text-xs font-semibold uppercase tracking-wider text-slate-400">Розпізнано</span>
                            <span id="ocr-doc-type-badge"></span>
                        </div>
                        <button onclick="copyOcrText()" class="text-xs text-slate-400 hover:text-slate-200 px-2.5 py-1 bg-slate-800 hover:bg-slate-700 rounded-lg transition flex items-center gap-1">
                            <i class="fa-solid fa-copy"></i>
                            <span id="copy-text-label">Копіювати</span>
                        </button>
                    </div>
                    <div class="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
                        <!-- Metadata summary -->
                        <div id="ocr-meta-box" class="glass rounded-xl p-3 space-y-2 border border-slate-800">
                            <div class="flex justify-between text-slate-300">
                                <span class="text-slate-500">Номер:</span>
                                <span id="ocr-meta-num" class="font-mono font-bold text-slate-200">—</span>
                            </div>
                            <div class="flex justify-between text-slate-300">
                                <span class="text-slate-500">Дата:</span>
                                <span id="ocr-meta-date" class="text-slate-200">—</span>
                            </div>
                            <div class="flex justify-between text-slate-300">
                                <span class="text-slate-500">Тип операції:</span>
                                <span id="ocr-meta-op" class="font-medium text-slate-200">—</span>
                            </div>
                            <div class="flex justify-between text-slate-300">
                                <span class="text-slate-500">Затребував:</span>
                                <span id="ocr-meta-requested-by" class="text-amber-200 text-right">—</span>
                            </div>
                            <div class="flex justify-between text-slate-300">
                                <span class="text-slate-500">Через кого:</span>
                                <span id="ocr-meta-requested-via" class="text-amber-200 text-right">—</span>
                            </div>
                        </div>

                        <!-- Impact / Items table if present -->
                        <div id="ocr-items-box" class="glass rounded-xl p-3 border border-slate-800 hidden">
                            <div class="text-slate-400 font-semibold mb-2 flex items-center justify-between">
                                <span>Позиції в документі</span>
                                <span id="ocr-items-count" class="text-[10px] bg-slate-800 px-1.5 py-0.5 rounded text-blue-400">0</span>
                            </div>
                            <div id="ocr-items-list" class="space-y-1.5 max-h-48 overflow-y-auto pr-1"></div>
                        </div>

                        <!-- Full OCR raw text -->
                        <div>
                            <div class="text-slate-400 font-semibold mb-2 flex items-center justify-between">
                                <span>Повний розпізнаний текст:</span>
                            </div>
                            <pre id="ocr-raw-text" class="bg-slate-950/80 p-3 rounded-xl border border-slate-800/80 text-slate-300 font-mono text-[11px] whitespace-pre-wrap break-words leading-relaxed max-h-[340px] overflow-y-auto select-text"></pre>
                        </div>
                    </div>
                </div>
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

    <!-- Edit Item Field Modal -->
    <div id="edit-modal" class="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm hidden flex items-center justify-center p-4">
        <div class="glass w-full max-w-md rounded-2xl p-6 border border-blue-500/30 shadow-2xl space-y-4">
            <div class="flex items-center justify-between border-b border-slate-800 pb-3">
                <h3 class="text-base font-bold text-slate-100 flex items-center gap-2">
                    <i class="fa-solid fa-pen-to-square text-blue-400"></i>
                    <span id="edit-modal-title">Редагування поля</span>
                </h3>
                <button onclick="closeEditModal()" class="text-slate-400 hover:text-white p-1 rounded-lg">
                    <i class="fa-solid fa-xmark text-lg"></i>
                </button>
            </div>
            <div class="space-y-3 text-sm">
                <div>
                    <label class="block text-xs font-semibold text-slate-400 mb-1">Поточне значення:</label>
                    <div id="edit-current-value" class="p-2.5 bg-slate-900/90 rounded-xl border border-slate-800 text-slate-300 font-mono text-xs break-all select-all min-h-[38px] flex items-center"></div>
                </div>
                <div>
                    <label id="edit-field-label" class="block text-xs font-semibold text-slate-300 mb-1">Нове значення:</label>
                    <input type="text" id="edit-new-value" class="w-full bg-slate-900 text-slate-100 p-2.5 rounded-xl border border-slate-700 focus:outline-none focus:border-blue-500 text-sm transition" placeholder="Введіть нове значення...">
                </div>
                <div>
                    <label class="block text-xs font-semibold text-slate-400 mb-1">Коментар / причина зміни (необов'язково):</label>
                    <input type="text" id="edit-comment" class="w-full bg-slate-900 text-slate-100 p-2.5 rounded-xl border border-slate-700 focus:outline-none focus:border-blue-500 text-sm transition" placeholder="Наприклад: Виправлення помилки OCR">
                </div>
                <div id="edit-error" class="text-xs text-rose-400 hidden"></div>
            </div>
            <div class="flex items-center justify-end space-x-3 pt-2">
                <button onclick="closeEditModal()" class="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium rounded-xl transition">
                    Скасувати (Esc)
                </button>
                <button id="edit-save-btn" onclick="submitEditField()" class="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-xl transition shadow-lg shadow-blue-600/30 flex items-center gap-2">
                    <i class="fa-solid fa-check"></i> <span>Зберегти</span>
                </button>
            </div>
        </div>
    </div>

<script>
let allItems = [];
let allDocs = [];
let currentViewingDocId = null;
let activeFilter = '';

function switchTab(tab) {
    const wh = document.getElementById('panel-warehouse');
    const dc = document.getElementById('panel-documents');
    const lg = document.getElementById('panel-logs');
    const tw = document.getElementById('tab-warehouse');
    const td = document.getElementById('tab-documents');
    const tl = document.getElementById('tab-logs');

    wh.classList.add('hidden');
    dc.classList.add('hidden');
    lg.classList.add('hidden');

    tw.className = tw.className.replace('tab-active', 'tab-inactive');
    td.className = td.className.replace('tab-active', 'tab-inactive');
    tl.className = tl.className.replace('tab-active', 'tab-inactive');

    if (tab === 'warehouse') {
        wh.classList.remove('hidden');
        tw.className = tw.className.replace('tab-inactive', 'tab-active');
    } else if (tab === 'documents') {
        dc.classList.remove('hidden');
        td.className = td.className.replace('tab-inactive', 'tab-active');
    } else if (tab === 'logs') {
        lg.classList.remove('hidden');
        tl.className = tl.className.replace('tab-inactive', 'tab-active');
        if (allLogs.length === 0) {
            fetchLogs();
        }
        if (autoScroll) {
            scrollLogsToBottom();
        }
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
        updateFilterCounts();
        filterItems();
    } catch(e) {
        console.error(e);
    }
}

function renderItems(items) {
    const tbody = document.getElementById('items-tbody');
    document.getElementById('visible-items').innerText = items.length;
    if (items.length === 0) {
        tbody.innerHTML = '<tr><td colspan="10" class="py-12 text-center text-slate-500"><i class="fa-solid fa-boxes-stacked text-2xl mb-2 text-slate-600"></i><p>Склад порожній.</p></td></tr>';
        return;
    }
    let html = '';
    items.forEach(it => {
        const bal = it.balance || 0;
        const minBal = (it.min_balance !== null && it.min_balance !== undefined) ? Number(it.min_balance) : 0;
        const isBelowMin = minBal > 0 && bal < minBal;

        let rowClass = 'hover:bg-slate-800/40 transition cursor-pointer group';
        if (isBelowMin) {
            // клас-маркер row-low: у картковому режимі CSS картки перебиває рамку й тло,
            // тож підсвітку «нижче мінімуму» доводиться повертати окремим правилом
            rowClass = 'row-low bg-rose-950/40 hover:bg-rose-900/50 border-l-4 border-l-rose-500 transition cursor-pointer group shadow-[inset_0_0_20px_rgba(244,63,94,0.15)] text-rose-100';
        }

        const balClass = isBelowMin ? 'text-rose-400 font-bold' : (bal > 0 ? 'text-blue-400 font-bold' : (bal < 0 ? 'text-red-400 font-bold' : 'text-slate-500 font-bold'));
        const minBalClass = isBelowMin ? 'text-rose-300 font-bold' : 'text-slate-400';
        const minBalDisplay = minBal > 0 ? fmtNum(minBal) : '<span class="text-slate-600">—</span>';

        html += `
        <tr class="${rowClass}" onclick="toggleTransactions(${it.id})">
            <td class="py-4 px-3"><i id="chevron-${it.id}" class="fa-solid fa-chevron-right text-[10px] ${isBelowMin ? 'text-rose-400' : 'text-slate-500'} transition-transform"></i></td>
            <td class="py-4 px-3 font-mono text-xs text-slate-400" data-label="Ном. номер">
                <div class="flex items-center justify-between gap-1">
                    <span id="item-sku-${it.id}">${esc(it.sku)}</span>
                    <button onclick="event.stopPropagation(); openEditModal(${it.id}, 'sku', '${esc(it.sku)}', 'Номенклатурний номер (SKU)')" class="text-slate-500 hover:text-blue-400 p-1 rounded transition opacity-0 hover:opacity-100 group-hover:opacity-100" title="Редагувати номенклатурний номер">
                        <i class="fa-solid fa-pencil text-[10px]"></i>
                    </button>
                </div>
            </td>
            <td class="py-4 px-3 font-medium ${isBelowMin ? 'text-rose-100 font-semibold' : 'text-slate-200'}" data-label="Найменування">
                <div class="flex items-center justify-between gap-1">
                    <span id="item-name-${it.id}">${esc(it.name)} ${isBelowMin ? '<i class="fa-solid fa-triangle-exclamation text-rose-400 text-xs ml-1" title="Залишок менше мінімального!"></i>' : ''}</span>
                    <button onclick="event.stopPropagation(); openEditModal(${it.id}, 'name', '${esc(it.name)}', 'Найменування')" class="text-slate-500 hover:text-blue-400 p-1 rounded transition opacity-0 hover:opacity-100 group-hover:opacity-100" title="Редагувати найменування">
                        <i class="fa-solid fa-pencil text-[10px]"></i>
                    </button>
                </div>
            </td>
            <td class="py-4 px-3 text-emerald-400 font-medium" data-label="Прихід">${fmtNum(it.total_income)}</td>
            <td class="py-4 px-3 text-rose-400 font-medium" data-label="Розхід">${fmtNum(it.total_expense)}</td>
            <td class="py-4 px-3 ${balClass}" data-label="Залишок">
                <div class="flex items-center justify-between gap-1">
                    <span id="item-balance-${it.id}">${fmtNum(bal)}</span>
                    <button onclick="event.stopPropagation(); openEditModal(${it.id}, 'balance', '${bal}', 'Залишок (кількість)')" class="text-slate-500 hover:text-blue-400 p-1 rounded transition opacity-0 hover:opacity-100 group-hover:opacity-100" title="Редагувати залишок">
                        <i class="fa-solid fa-pencil text-[10px]"></i>
                    </button>
                </div>
            </td>
            <td class="py-4 px-3 ${minBalClass}" data-label="Мін. залишок">
                <div class="flex items-center justify-between gap-1">
                    <span id="item-min-balance-${it.id}">${minBalDisplay}</span>
                    <button onclick="event.stopPropagation(); openEditModal(${it.id}, 'min_balance', '${minBal > 0 ? minBal : ''}', 'Мінімальний залишок')" class="text-slate-500 hover:text-blue-400 p-1 rounded transition opacity-0 hover:opacity-100 group-hover:opacity-100" title="Встановити мінімальний залишок">
                        <i class="fa-solid fa-pencil text-[10px]"></i>
                    </button>
                </div>
            </td>
            <td class="py-4 px-3 text-slate-400" data-label="Од.виміру">
                <div class="flex items-center justify-between gap-1">
                    <span id="item-unit-${it.id}">${esc(it.unit)}</span>
                    <button onclick="event.stopPropagation(); openEditModal(${it.id}, 'unit', '${esc(it.unit)}', 'Одиниця виміру')" class="text-slate-500 hover:text-blue-400 p-1 rounded transition opacity-0 hover:opacity-100 group-hover:opacity-100" title="Редагувати одиницю виміру">
                        <i class="fa-solid fa-pencil text-[10px]"></i>
                    </button>
                </div>
            </td>
            <td class="py-4 px-3 text-slate-300" data-label="Постачальник">
                <div class="flex items-center justify-between gap-1">
                    <span id="item-supplier-${it.id}">${esc(it.supplier)}</span>
                    <button onclick="event.stopPropagation(); openEditModal(${it.id}, 'supplier', '${esc(it.supplier)}', 'Постачальник')" class="text-slate-500 hover:text-blue-400 p-1 rounded transition opacity-0 hover:opacity-100 group-hover:opacity-100" title="Редагувати постачальника">
                        <i class="fa-solid fa-pencil text-[10px]"></i>
                    </button>
                </div>
            </td>
            <td class="py-4 px-3 text-xs text-slate-400" data-label="Примітки">
                <div class="flex items-center justify-between gap-1">
                    <span id="item-notes-${it.id}" class="min-w-0 break-words">${esc(it.notes)}</span>
                    <button onclick="event.stopPropagation(); openEditModal(${it.id}, 'notes', '${esc(it.notes)}', 'Примітки')" class="text-slate-500 hover:text-blue-400 p-1 rounded transition opacity-0 hover:opacity-100 group-hover:opacity-100 shrink-0" title="Редагувати примітки">
                        <i class="fa-solid fa-pencil text-[10px]"></i>
                    </button>
                </div>
            </td>
        </tr>
        <tr id="tx-row-${it.id}" class="hidden">
            <td colspan="10" class="p-0">
                <div class="expand-row px-8 py-3 border-t border-slate-800/40">
                    <div id="tx-content-${it.id}" class="text-xs text-slate-400">Завантаження...</div>
                </div>
            </td>
        </tr>`;
    });
    tbody.innerHTML = html;
}

// ---- Item Edit Modal Logic ----

let currentEditItemId = null;
let currentEditField = null;

function openEditModal(itemId, field, currentVal, fieldLabel) {
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
    document.getElementById('edit-modal').classList.add('hidden');
}

async function submitEditField() {
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

async function reloadTransactions(itemId) {
    const content = document.getElementById('tx-content-' + itemId);
    if (!content) return;
    try {
        const res = await fetch('/api/warehouse/items/' + itemId + '/transactions');
        const txs = await res.json();
        const it = allItems.find(x => x.id === itemId);
        const curBal = it ? (it.balance || 0) : 0;
        const curUnit = it ? (it.unit || '') : '';
        const balColor = curBal > 0 ? 'text-blue-400' : (curBal < 0 ? 'text-red-400' : 'text-slate-400');

        let headerBar = `<div class="flex items-center justify-between pb-2 mb-2 border-b border-slate-800/60">
            <div class="text-xs text-slate-300 flex items-center gap-2">
                <span class="text-slate-400">Поточний залишок:</span>
                <span class="font-bold ${balColor}">${fmtNum(curBal)} ${esc(curUnit)}</span>
            </div>
        </div>`;

        if (txs.length === 0) {
            content.innerHTML = headerBar + '<p class="text-slate-500 py-2">Немає транзакцій.</p>';
            return;
        }
        let h = headerBar + '<table class="w-full card-table"><thead><tr class="text-slate-500 text-[11px] uppercase">' +
            '<th class="py-1 pr-3 text-left">Дата</th><th class="py-1 pr-3 text-left">Тип</th>' +
            '<th class="py-1 pr-3 text-left">Тип док.</th>' +
            '<th class="py-1 pr-3 text-right">Кількість</th><th class="py-1 pr-3 text-left">№ накл.</th>' +
            '<th class="py-1 pr-3 text-right">Залишок</th><th class="py-1 pr-3 text-left">Документ</th>' +
            '<th class="py-1 pr-3 text-left">Затребував</th>' +
            '<th class="py-1 pr-3 text-left">Через кого</th>' +
            '<th class="py-1 pr-3 text-left">Джерело</th>' +
            '</tr></thead><tbody>';
        txs.forEach(tx => {
            const isManual = tx.file_type === 'manual' || tx.doc_type === 'РУЧНЕ_КОРИГУВАННЯ';
            const isInc = tx.operation_type === 'income';
            let badge = isInc ? 'badge-income' : 'badge-expense';
            let label = isInc ? 'Прихід' : 'Розхід';
            if (isManual) {
                badge = 'badge-vymoha';
                label = 'Коригування';
            }
            const date = tx.doc_date || formatTs(tx.created_at);
            const docType = tx.doc_type || '';
            let docTypeBadge = '';
            if (docType === 'НАКЛАДНА') {
                docTypeBadge = '<span class="px-2 py-0.5 rounded-full text-[11px] font-medium badge-nakladna">Накл.</span>';
            } else if (docType === 'ВИМОГА') {
                docTypeBadge = '<span class="px-2 py-0.5 rounded-full text-[11px] font-medium badge-vymoha">Вимога</span>';
            } else if (docType === 'РУЧНЕ_КОРИГУВАННЯ' || isManual) {
                docTypeBadge = '<span class="px-2 py-0.5 rounded-full text-[11px] font-medium" style="background: rgba(245, 158, 11, 0.15); color: #fbbf24;">Коригування</span>';
            } else if (docType) {
                docTypeBadge = `<span class="text-slate-400 text-[11px]">${esc(docType)}</span>`;
            }
            const srcRow = tx.source_row || '';
            const requestedBy = tx.requested_by || '';
            const requestedVia = tx.requested_via || '';
            let qtyDisplay = '';
            if (tx.quantity === 0) {
                qtyDisplay = '<span class="text-slate-400 font-medium">0</span>';
            } else {
                const sign = isInc ? '+' : '-';
                const color = isInc ? 'text-emerald-400' : 'text-rose-400';
                qtyDisplay = `<span class="${color} font-medium">${sign}${fmtNum(tx.quantity)}</span>`;
            }
            let docDisplay = '';
            if (isManual) {
                docDisplay = `<span class="text-amber-400/90 text-xs font-medium" title="Ручне редагування"><i class="fa-solid fa-user-pen mr-1"></i>${esc(tx.filename)}</span>`;
            } else {
                const fileIcon = getFileIcon(tx.file_type);
                docDisplay = `<button onclick="event.stopPropagation(); viewDocument(${tx.document_id}, '${esc(tx.filename)}', '${tx.file_type}', '${esc(tx.source_row)}')"
                    class="text-slate-400 hover:text-blue-400 transition">
                    ${fileIcon} <span class="ml-1">${esc(tx.filename)}</span>
                </button>`;
            }
            h += `<tr class="border-t border-slate-800/30">
                <td class="py-2 pr-3 text-slate-300" data-label="Дата">${esc(date)}</td>
                <td class="py-2 pr-3" data-label="Тип"><span class="px-2 py-0.5 rounded-full text-[11px] font-medium ${badge}" ${isManual ? 'style="background: rgba(245, 158, 11, 0.15); color: #fbbf24;"' : ''}>${label}</span></td>
                <td class="py-2 pr-3" data-label="Тип док.">${docTypeBadge}</td>
                <td class="py-2 pr-3 text-right font-medium" data-label="Кількість">${qtyDisplay}</td>
                <td class="py-2 pr-3 text-slate-300 font-mono" data-label="№ накл.">${esc(tx.doc_number)}</td>
                <td class="py-2 pr-3 text-right text-blue-400 font-medium" data-label="Залишок">${fmtNum(tx.running_balance)}</td>
                <td class="py-2 pr-3 break-words" data-label="Документ">${docDisplay}</td>
                <td class="py-2 pr-3 text-slate-300 break-words" data-label="Затребував">${fmtRequestedBy(requestedBy)}</td>
                <td class="py-2 pr-3 text-slate-300 break-words" data-label="Через кого">${fmtRequestedBy(requestedVia)}</td>
                <td class="py-2 pr-3 text-slate-500 text-[11px] break-words" data-label="Джерело">${esc(srcRow)}</td>
            </tr>`;
        });
        h += '</tbody></table>';
        content.innerHTML = h;
    } catch(e) {
        content.innerHTML = '<p class="text-red-400">Помилка завантаження транзакцій.</p>';
    }
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
    content.innerHTML = '<div class="py-2 text-slate-500"><i class="fa-solid fa-spinner fa-spin mr-1.5"></i>Завантаження...</div>';
    await reloadTransactions(itemId);
}

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

// ---- Documents ----

const QUEUED_OCR_HINT = '⏳ Документ у черзі на розпізнавання. Текст з\'явиться після завершення обробки.';
const PROCESSING_OCR_HINT = '🔄 Документ у процесі обробки. Текст з\'явиться після завершення.';

function getOcrPlaceholder(status) {
    if (status === 'queued') return QUEUED_OCR_HINT;
    if (status === 'processing_ocr' || status === 'processing_emb') return PROCESSING_OCR_HINT;
    return '(Розпізнаний текст відсутній)';
}

const DOC_STATUS_BADGES = {
    queued: { label: '⏳ В черзі', cls: 'badge-queued' },
    processing_ocr: { label: '🔄 Розпізнавання', cls: 'badge-ocr' },
    processing_emb: { label: '🧠 Embeddings', cls: 'badge-emb' },
    completed: { label: '✅ Готово', cls: 'badge-import' },
    error: { label: '❌ Помилка', cls: 'badge-expense' },
};

function docStatusBadge(doc) {
    const status = doc.status || 'completed';
    const known = DOC_STATUS_BADGES[status];
    const errMsg = doc.error_message ? ` title="${esc(doc.error_message)}"` : '';
    if (known) {
        return `<span class="px-2 py-0.5 rounded-full text-[11px] font-medium whitespace-nowrap ${known.cls}"${errMsg}>${known.label}</span>`;
    }
    return `<span class="px-2 py-0.5 rounded-full text-[11px] font-medium whitespace-nowrap badge-import"${errMsg}>${esc(status)}</span>`;
}

let smartPollingTimer = null;
let hadActiveDocs = false;

function checkSmartPolling() {
    const hasActive = allDocs.some(d => d.status === 'queued' || (d.status && d.status.startsWith('processing_')));
    if (hasActive) {
        hadActiveDocs = true;
        if (!smartPollingTimer) {
            smartPollingTimer = setTimeout(smartPollTick, 3000);
        }
    } else {
        if (smartPollingTimer) {
            clearTimeout(smartPollingTimer);
            smartPollingTimer = null;
        }
        if (hadActiveDocs) {
            hadActiveDocs = false;
            fetchItems();
        }
    }
}

async function smartPollTick() {
    smartPollingTimer = null;
    await fetchDocs();
    if (currentViewingDocId) {
        const curDoc = allDocs.find(d => d.id === currentViewingDocId);
        if (curDoc && (curDoc.status === 'queued' || (curDoc.status && curDoc.status.startsWith('processing_')))) {
            loadDocumentOcr(currentViewingDocId);
        }
    }
    const openImpactRows = document.querySelectorAll('[id^="doc-impact-row-"]:not(.hidden)');
    for (const row of openImpactRows) {
        const docId = parseInt(row.id.replace('doc-impact-row-', ''));
        if (docId) {
            const d = allDocs.find(x => x.id === docId);
            if (d && (d.status === 'queued' || (d.status && d.status.startsWith('processing_')))) {
                reloadDocImpact(docId);
            }
        }
    }
    checkSmartPolling();
}

async function retryDocument(docId) {
    try {
        const res = await fetch('/api/warehouse/documents/' + docId + '/retry', { method: 'POST' });
        const data = await res.json();
        if (!res.ok || data.error) {
            alert(data.error || 'Помилка повтору');
            return;
        }
        await fetchDocs();
    } catch(e) {
        alert('Помилка: ' + e.message);
    }
}

async function fetchDocs() {
    try {
        const res = await fetch('/api/warehouse/documents');
        allDocs = await res.json();
        document.getElementById('docs-count').innerText = allDocs.length;
        renderDocs(allDocs);
        checkSmartPolling();
    } catch(e) {
        console.error(e);
    }
}

function renderDocs(docs) {
    const tbody = document.getElementById('docs-tbody');
    if (docs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="12" class="py-12 text-center text-slate-500"><p>Документів немає.</p></td></tr>';
        return;
    }
    let html = '';
    docs.forEach(doc => {
        const icon = getFileIcon(doc.file_type);
        const typeLabel = doc.file_type === 'excel' ? 'Excel' : (doc.file_type === 'photo' ? 'Фото' : 'PDF');
        const date = formatTs(doc.uploaded_at);
        const docType = doc.doc_type || '';
        const requestedBy = doc.requested_by || '';
        const requestedVia = doc.requested_via || '';
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
        let previewBtn = '';
        if (doc.file_type === 'excel') {
            previewBtn = `<button onclick="event.stopPropagation(); viewDocument(${doc.id}, '${esc(doc.filename)}', '${doc.file_type}')" class="w-10 h-10 flex items-center justify-center rounded-lg bg-green-500/10 text-green-500 hover:bg-green-500/20 border border-green-500/20 transition" title="Перегляд Excel">
                <i class="fa-solid fa-file-excel text-xl"></i>
            </button>`;
        } else if (doc.file_type === 'pdf') {
            previewBtn = `<button onclick="event.stopPropagation(); viewDocument(${doc.id}, '${esc(doc.filename)}', '${doc.file_type}')" class="w-10 h-10 flex items-center justify-center rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20 border border-red-500/20 transition" title="Перегляд PDF">
                <i class="fa-solid fa-file-pdf text-xl"></i>
            </button>`;
        } else {
            previewBtn = `<button onclick="event.stopPropagation(); viewDocument(${doc.id}, '${esc(doc.filename)}', '${doc.file_type}')" class="group relative block w-10 h-10 rounded-lg overflow-hidden border border-slate-700 bg-slate-900 hover:border-blue-500 transition shadow" title="Переглянути фото та текст OCR">
                <img src="/api/warehouse/documents/${doc.id}/view" alt="Превʼю" class="w-full h-full object-cover group-hover:scale-110 transition duration-200" onerror="this.outerHTML='<div class=\\'w-full h-full flex items-center justify-center text-emerald-400\\'><i class=\\'fa-solid fa-image text-lg\\'></i></div>'">
            </button>`;
        }

        let retryBtn = '';
        if (doc.status === 'error') {
            retryBtn = `<button onclick="event.stopPropagation(); retryDocument(${doc.id})" class="p-2 text-amber-400 hover:text-amber-300 hover:bg-amber-500/10 rounded-lg transition mr-1" title="Повторити">
                <i class="fa-solid fa-rotate-right"></i>
            </button>`;
        }

        html += `
        <tr class="hover:bg-slate-800/40 transition cursor-pointer" onclick="toggleDocImpact(${doc.id})">
            <td class="py-4 px-3"><i id="doc-chevron-${doc.id}" class="fa-solid fa-chevron-right text-[10px] text-slate-500 transition-transform"></i></td>
            <td class="py-4 px-3" data-label="Превʼю">${previewBtn}</td>
            <td class="py-4 px-3 font-medium text-slate-200 break-words" data-label="Файл">${esc(doc.filename)}</td>
            <td class="py-4 px-3" data-label="Тип"><span class="px-2 py-0.5 rounded-full text-[11px] font-medium badge-import">${typeLabel}</span></td>
            <td class="py-4 px-3" data-label="Тип документу">${docTypeBadge}</td>
            <td class="py-4 px-3" data-label="Статус">${docStatusBadge(doc)}</td>
            <td class="py-4 px-3 text-slate-300" data-label="Дата завантаження">${date}</td>
            <td class="py-4 px-3 font-mono text-slate-300" data-label="№ документа">${esc(doc.doc_number)}</td>
            <td class="py-4 px-3 text-slate-300" data-label="Затребував">
                <span class="block break-words">${fmtRequestedBy(requestedBy)}</span>
            </td>
            <td class="py-4 px-3 text-slate-300" data-label="Через кого">
                <span class="block break-words">${fmtRequestedBy(requestedVia)}</span>
            </td>
            <td class="py-4 px-3 text-blue-400 font-medium" data-label="Позицій">${doc.transaction_count}</td>
            <td class="py-4 px-3 text-right" data-label="Дії">
                ${retryBtn}<button onclick="event.stopPropagation(); openDeleteModal(${doc.id}, '${esc(doc.filename)}')" class="p-2 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition" title="Видалити">
                    <i class="fa-solid fa-trash"></i>
                </button>
            </td>
        </tr>
        <tr id="doc-impact-row-${doc.id}" class="hidden">
            <td colspan="12" class="p-0">
                <div class="expand-row px-8 py-4 border-t border-slate-800/40">
                    <div id="doc-impact-content-${doc.id}" class="text-xs text-slate-400">Завантаження...</div>
                </div>
            </td>
        </tr>`;
    });
    tbody.innerHTML = html;
}

async function reloadDocImpact(docId) {
    const content = document.getElementById('doc-impact-content-' + docId);
    if (!content) return;

    try {
        const res = await fetch('/api/warehouse/documents/' + docId + '/ocr');
        const data = await res.json();
        if (data.error) {
            content.innerHTML = '<p class="text-red-400 py-2">Помилка: ' + esc(data.error) + '</p>';
            return;
        }

        const isPhoto = data.file_type === 'photo' || (data.filename && data.filename.match(/\.(jpg|jpeg|png|webp)$/i));
        const rawText = data.raw_text || '';
        const impacts = data.impact || [];

        let h = '<div class="space-y-4">';

        if (isPhoto) {
            h += '<div class="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">';

            // Left: Image Preview Card
            h += '<div class="lg:col-span-4 glass rounded-xl p-3 border border-slate-800 flex flex-col items-center space-y-3 bg-slate-900/60">';
            h += '<div class="relative w-full max-h-[320px] overflow-hidden rounded-lg bg-slate-950 flex items-center justify-center border border-slate-800/80 cursor-pointer group" onclick="viewDocument(' + docId + ', \'' + esc(data.filename) + '\', \'' + data.file_type + '\')">';
            h += '<img src="/api/warehouse/documents/' + docId + '/view" alt="' + esc(data.filename) + '" class="max-h-[300px] w-auto object-contain rounded select-none group-hover:scale-105 transition duration-300" />';
            h += '<div class="absolute inset-0 bg-slate-950/40 opacity-0 group-hover:opacity-100 flex items-center justify-center transition duration-200"><span class="px-3 py-1.5 bg-blue-600/90 text-white rounded-lg text-xs font-medium shadow-lg"><i class="fa-solid fa-expand mr-1.5"></i>Відкрити в повному розмірі</span></div>';
            h += '</div>';
            h += '<div class="w-full flex items-center justify-between text-xs text-slate-400 px-1">';
            h += '<span class="font-medium text-slate-300 min-w-0 break-words"><i class="fa-solid fa-image text-emerald-400 mr-1.5"></i>' + esc(data.filename) + '</span>';
            h += '<button onclick="viewDocument(' + docId + ', \'' + esc(data.filename) + '\', \'' + data.file_type + '\')" class="text-blue-400 hover:text-blue-300 font-medium transition"><i class="fa-solid fa-magnifying-glass-plus mr-1"></i>Збільшити</button>';
            h += '</div>';
            h += '</div>';

            // Right: OCR Text and Metadata Card
            h += '<div class="lg:col-span-8 space-y-3">';

            // Meta bar — усі пʼять полів розпізнавання рендеряться завжди: значення або прочерк.
            const metaField = (label, valueHtml) => '<span class="text-xs text-slate-300"><span class="text-slate-500">' + label + ':</span> ' + valueHtml + '</span>';
            const metaDash = '<span class="text-slate-600">—</span>';
            h += '<div class="glass rounded-xl p-3 border border-slate-800 flex flex-wrap items-center justify-between gap-2 bg-slate-900/60">';
            h += '<div class="flex items-center gap-3">';
            const dt = (data.doc_type || '').toUpperCase();
            if (dt) {
                const badge = dt === 'НАКЛАДНА' ? 'badge-nakladna' : (dt === 'ВИМОГА' ? 'badge-vymoha' : 'badge-import');
                h += metaField('Тип', '<span class="px-2.5 py-0.5 rounded-full text-xs font-semibold ' + badge + '">' + esc(dt) + '</span>');
            } else {
                h += metaField('Тип', metaDash);
            }
            h += metaField('№', data.doc_number ? '<span class="font-mono font-bold text-slate-200">' + esc(data.doc_number) + '</span>' : metaDash);
            h += metaField('Дата', data.doc_date ? esc(data.doc_date) : metaDash);
            h += metaField('Затребував', data.requested_by ? '<span class="text-amber-200">' + esc(data.requested_by) + '</span>' : metaDash);
            h += metaField('Через кого', data.requested_via ? '<span class="text-amber-200">' + esc(data.requested_via) + '</span>' : metaDash);
            h += '</div>';
            if (rawText) {
                h += '<button onclick="copyTextDirect(\'ocr-acc-text-' + docId + '\', this)" class="px-2.5 py-1 text-xs text-slate-400 hover:text-slate-200 bg-slate-800 hover:bg-slate-700 rounded-lg transition flex items-center gap-1"><i class="fa-solid fa-copy"></i><span>Копіювати текст</span></button>';
            }
            h += '</div>';

            // OCR Text Box
            h += '<div class="glass rounded-xl p-3 border border-slate-800 bg-slate-900/60">';
            h += '<div class="text-xs font-semibold text-slate-400 mb-1.5 flex items-center gap-1.5"><i class="fa-solid fa-align-left text-blue-400"></i><span>Розпізнаний OCR текст з файлу:</span></div>';
            h += '<pre id="ocr-acc-text-' + docId + '" class="bg-slate-950/80 p-3 rounded-lg border border-slate-800/80 text-slate-300 font-mono text-[11px] whitespace-pre-wrap break-words leading-relaxed max-h-[160px] overflow-y-auto select-text">' + (rawText ? esc(rawText) : esc(getOcrPlaceholder(data.status))) + '</pre>';
            h += '</div>';

            // Items Impact Table
            if (impacts.length > 0) {
                h += '<div class="glass rounded-xl p-3 border border-slate-800 bg-slate-900/60">';
                h += '<div class="text-xs font-semibold text-slate-400 mb-2 flex items-center justify-between"><span>Позиції в документі (' + impacts.length + ')</span></div>';
                h += '<div class="overflow-x-auto"><table class="w-full text-xs card-table"><thead><tr class="text-slate-500 text-[11px] uppercase"><th class="py-1 pr-3 text-left">Ном. номер</th><th class="py-1 pr-3 text-left">Найменування</th><th class="py-1 pr-3 text-left">Тип</th><th class="py-1 pr-3 text-right">Кількість</th><th class="py-1 pr-3 text-left">Од.</th><th class="py-1 pr-3 text-left">Джерело</th></tr></thead><tbody>';
                impacts.forEach(imp => {
                    const isInc = imp.operation_type === 'income';
                    const badge = isInc ? 'badge-income' : 'badge-expense';
                    const label = isInc ? 'Прихід' : 'Розхід';
                    const qi = fmtImpactQty(imp.quantity, isInc);
                    h += `<tr class="border-t border-slate-800/30 hover:bg-slate-800/30 transition group">
                        <td class="py-1.5 pr-3 font-mono text-slate-400" data-label="Ном. номер">
                            <div class="flex items-center justify-between gap-1">
                                <span>${esc(imp.sku)}</span>
                                <button onclick="event.stopPropagation(); openEditModal(${imp.item_id}, 'sku', '${esc(imp.sku)}', 'Номенклатурний номер (SKU)')" class="text-slate-500 hover:text-blue-400 p-0.5 rounded transition opacity-0 hover:opacity-100 group-hover:opacity-100" title="Редагувати номенклатурний номер">
                                    <i class="fa-solid fa-pencil text-[10px]"></i>
                                </button>
                            </div>
                        </td>
                        <td class="py-1.5 pr-3 text-slate-200" data-label="Найменування">
                            <div class="flex items-center justify-between gap-1">
                                <span class="min-w-0 break-words">${esc(imp.name)}</span>
                                <button onclick="event.stopPropagation(); openEditModal(${imp.item_id}, 'name', '${esc(imp.name)}', 'Найменування')" class="text-slate-500 hover:text-blue-400 p-0.5 rounded transition opacity-0 hover:opacity-100 group-hover:opacity-100 shrink-0" title="Редагувати найменування">
                                    <i class="fa-solid fa-pencil text-[10px]"></i>
                                </button>
                            </div>
                        </td>
                        <td class="py-1.5 pr-3" data-label="Тип"><span class="px-2 py-0.5 rounded-full text-[10px] font-medium ${badge}">${label}</span></td>
                        <td class="py-1.5 pr-3 text-right font-medium ${qi[1]}" data-label="Кількість">
                            <div class="flex items-center justify-end gap-1">
                                <span>${qi[0]}</span>
                                <button onclick="event.stopPropagation(); openEditModal(${imp.item_id}, 'balance', '${imp.quantity}', 'Залишок (кількість)')" class="text-slate-500 hover:text-blue-400 p-0.5 rounded transition opacity-0 hover:opacity-100 group-hover:opacity-100" title="Коригувати кількість/залишок">
                                    <i class="fa-solid fa-pencil text-[10px]"></i>
                                </button>
                            </div>
                        </td>
                        <td class="py-1.5 pr-3 text-slate-400" data-label="Од.">
                            <div class="flex items-center justify-between gap-1">
                                <span>${esc(imp.unit)}</span>
                                <button onclick="event.stopPropagation(); openEditModal(${imp.item_id}, 'unit', '${esc(imp.unit)}', 'Одиниця виміру')" class="text-slate-500 hover:text-blue-400 p-0.5 rounded transition opacity-0 hover:opacity-100 group-hover:opacity-100" title="Редагувати одиницю виміру">
                                    <i class="fa-solid fa-pencil text-[10px]"></i>
                                </button>
                            </div>
                        </td>
                        <td class="py-1.5 pr-3 text-slate-500 text-[11px] break-words" data-label="Джерело">${esc(imp.source_row || '')}</td>
                    </tr>`;
                });
                h += '</tbody></table></div></div>';
            }

            h += '</div></div>'; // end grid
        } else {
            // Excel / other non-photo documents
            if (impacts.length === 0) {
                h += '<p class="text-slate-500 py-2">Документ не вплинув на жодну позицію.</p>';
            } else {
                h += '<table class="w-full text-xs card-table"><thead><tr class="text-slate-500 text-[11px] uppercase">' +
                    '<th class="py-1 pr-3 text-left">Ном. номер</th><th class="py-1 pr-3 text-left">Найменування</th>' +
                    '<th class="py-1 pr-3 text-left">Тип</th><th class="py-1 pr-3 text-right">Кількість</th>' +
                    '<th class="py-1 pr-3 text-left">Од.</th><th class="py-1 pr-3 text-left">Джерело</th>' +
                    '</tr></thead><tbody>';
                impacts.forEach(imp => {
                    const isInc = imp.operation_type === 'income';
                    const badge = isInc ? 'badge-income' : 'badge-expense';
                    const label = isInc ? 'Прихід' : 'Розхід';
                    const qi = fmtImpactQty(imp.quantity, isInc);
                    const srcRow = imp.source_row || '';
                    h += `<tr class="border-t border-slate-800/30 hover:bg-slate-800/30 transition group">
                        <td class="py-2 pr-3 font-mono text-slate-400" data-label="Ном. номер">
                            <div class="flex items-center justify-between gap-1">
                                <span>${esc(imp.sku)}</span>
                                <button onclick="event.stopPropagation(); openEditModal(${imp.item_id}, 'sku', '${esc(imp.sku)}', 'Номенклатурний номер (SKU)')" class="text-slate-500 hover:text-blue-400 p-0.5 rounded transition opacity-0 hover:opacity-100 group-hover:opacity-100" title="Редагувати номенклатурний номер">
                                    <i class="fa-solid fa-pencil text-[10px]"></i>
                                </button>
                            </div>
                        </td>
                        <td class="py-2 pr-3 text-slate-200" data-label="Найменування">
                            <div class="flex items-center justify-between gap-1">
                                <span class="min-w-0 break-words">${esc(imp.name)}</span>
                                <button onclick="event.stopPropagation(); openEditModal(${imp.item_id}, 'name', '${esc(imp.name)}', 'Найменування')" class="text-slate-500 hover:text-blue-400 p-0.5 rounded transition opacity-0 hover:opacity-100 group-hover:opacity-100 shrink-0" title="Редагувати найменування">
                                    <i class="fa-solid fa-pencil text-[10px]"></i>
                                </button>
                            </div>
                        </td>
                        <td class="py-2 pr-3" data-label="Тип"><span class="px-2 py-0.5 rounded-full text-[11px] font-medium ${badge}">${label}</span></td>
                        <td class="py-2 pr-3 text-right font-medium ${qi[1]}" data-label="Кількість">
                            <div class="flex items-center justify-end gap-1">
                                <span>${qi[0]}</span>
                                <button onclick="event.stopPropagation(); openEditModal(${imp.item_id}, 'balance', '${imp.quantity}', 'Залишок (кількість)')" class="text-slate-500 hover:text-blue-400 p-0.5 rounded transition opacity-0 hover:opacity-100 group-hover:opacity-100" title="Коригувати кількість/залишок">
                                    <i class="fa-solid fa-pencil text-[10px]"></i>
                                </button>
                            </div>
                        </td>
                        <td class="py-2 pr-3 text-slate-400" data-label="Од.">
                            <div class="flex items-center justify-between gap-1">
                                <span>${esc(imp.unit)}</span>
                                <button onclick="event.stopPropagation(); openEditModal(${imp.item_id}, 'unit', '${esc(imp.unit)}', 'Одиниця виміру')" class="text-slate-500 hover:text-blue-400 p-0.5 rounded transition opacity-0 hover:opacity-100 group-hover:opacity-100" title="Редагувати одиницю виміру">
                                    <i class="fa-solid fa-pencil text-[10px]"></i>
                                </button>
                            </div>
                        </td>
                        <td class="py-2 pr-3 text-slate-500 text-[11px] break-words" data-label="Джерело">${esc(srcRow)}</td>
                    </tr>`;
                });
                h += '</tbody></table>';
            }
        }

        h += '</div>';
        content.innerHTML = h;
    } catch(e) {
        content.innerHTML = '<p class="text-red-400 py-2">Помилка завантаження: ' + esc(e.message) + '</p>';
    }
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
    content.innerHTML = '<div class="py-4 text-center text-slate-500"><i class="fa-solid fa-spinner fa-spin mr-2"></i>Завантаження даних...</div>';
    await reloadDocImpact(docId);
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

let imgZoom = 1.0;
const MIN_ZOOM = 0.25;
const MAX_ZOOM = 3.0;
const ZOOM_STEP = 0.25;
let currentOcrText = '';

async function viewDocument(docId, filename, fileType, sourceRow) {
    if (fileType === 'excel') {
        let highlightRows = [];
        if (sourceRow) {
            const m = sourceRow.match(/Рядок\s+(\d+)/);
            if (m) highlightRows.push(parseInt(m[1]));
        }
        openExcelPreview(docId, filename, highlightRows);
        return;
    }
    currentViewingDocId = docId;
    const img = document.getElementById('img-modal-src');
    imgZoom = 1.0;
    img.onload = function() {
        applyImgZoom();
    };
    img.src = '/api/warehouse/documents/' + docId + '/view';
    if (img.complete && img.naturalWidth > 0) {
        applyImgZoom();
    }
    document.getElementById('img-modal-title').innerHTML = '<i class="fa-solid fa-image text-emerald-400"></i> ' + esc(filename);
    document.getElementById('img-modal').classList.remove('hidden');
    updateZoomUI();

    await loadDocumentOcr(docId);
}

async function loadDocumentOcr(docId) {
    const docTypeBadge = document.getElementById('ocr-doc-type-badge');
    const numEl = document.getElementById('ocr-meta-num');
    const dateEl = document.getElementById('ocr-meta-date');
    const opEl = document.getElementById('ocr-meta-op');
    const requestedByEl = document.getElementById('ocr-meta-requested-by');
    const requestedViaEl = document.getElementById('ocr-meta-requested-via');
    const rawEl = document.getElementById('ocr-raw-text');
    const itemsBox = document.getElementById('ocr-items-box');
    const itemsList = document.getElementById('ocr-items-list');
    const itemsCount = document.getElementById('ocr-items-count');

    currentOcrText = '';
    rawEl.textContent = 'Завантаження розпізнаного тексту...';
    numEl.textContent = '—';
    dateEl.textContent = '—';
    opEl.textContent = '—';
    if (requestedByEl) requestedByEl.textContent = '—';
    if (requestedViaEl) requestedViaEl.textContent = '—';
    docTypeBadge.innerHTML = '';
    itemsBox.classList.add('hidden');
    itemsList.innerHTML = '';

    try {
        const res = await fetch('/api/warehouse/documents/' + docId + '/ocr');
        const data = await res.json();
        if (data.error) {
            rawEl.textContent = 'Помилка: ' + data.error;
            return;
        }

        currentOcrText = data.raw_text || '';
        rawEl.textContent = currentOcrText || getOcrPlaceholder(data.status);
        numEl.textContent = data.doc_number || '—';
        dateEl.textContent = data.doc_date || '—';
        if (requestedByEl) requestedByEl.textContent = data.requested_by || '—';
        if (requestedViaEl) requestedViaEl.textContent = data.requested_via || '—';

        const dt = (data.doc_type || '').toUpperCase();
        if (dt === 'НАКЛАДНА') {
            docTypeBadge.innerHTML = '<span class="px-2 py-0.5 rounded-full text-[11px] font-medium badge-nakladna"><i class="fa-solid fa-arrow-down mr-1"></i>Накладна</span>';
            opEl.innerHTML = '<span class="text-emerald-400 font-semibold">НАКЛАДНА (Прихід)</span>';
        } else if (dt === 'ВИМОГА') {
            docTypeBadge.innerHTML = '<span class="px-2 py-0.5 rounded-full text-[11px] font-medium badge-vymoha"><i class="fa-solid fa-arrow-up mr-1"></i>Вимога</span>';
            opEl.innerHTML = '<span class="text-rose-400 font-semibold">ВИМОГА (Розхід / Видача)</span>';
        } else if (dt) {
            docTypeBadge.innerHTML = `<span class="px-2 py-0.5 rounded-full text-[11px] font-medium badge-import">${esc(dt)}</span>`;
            opEl.textContent = dt;
        } else {
            docTypeBadge.innerHTML = '';
            opEl.textContent = '—';
        }

        const items = data.impact || [];
        if (items.length > 0) {
            itemsBox.classList.remove('hidden');
            itemsCount.textContent = items.length;
            let listHtml = '';
            items.forEach((it, idx) => {
                const isInc = it.operation_type === 'income';
                const qi = fmtImpactQty(it.quantity, isInc);
                listHtml += `<div class="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/60 flex items-start justify-between gap-2 hover:border-slate-700/80 transition group">
                    <div class="min-w-0 flex-1">
                        <div class="flex items-center justify-between gap-1">
                            <span class="font-medium text-slate-200 min-w-0 break-words">${idx + 1}. ${esc(it.name)}</span>
                            <button onclick="event.stopPropagation(); openEditModal(${it.item_id}, 'name', '${esc(it.name)}', 'Найменування')" class="text-slate-500 hover:text-blue-400 p-0.5 rounded transition opacity-0 hover:opacity-100 group-hover:opacity-100 shrink-0" title="Редагувати найменування">
                                <i class="fa-solid fa-pencil text-[10px]"></i>
                            </button>
                        </div>
                        <div class="flex items-center justify-between gap-1 mt-0.5">
                            <span class="text-[10px] text-slate-500 font-mono min-w-0 break-words">${esc(it.sku || '(без SKU)')}</span>
                            <button onclick="event.stopPropagation(); openEditModal(${it.item_id}, 'sku', '${esc(it.sku)}', 'Номенклатурний номер (SKU)')" class="text-slate-500 hover:text-blue-400 p-0.5 rounded transition opacity-0 hover:opacity-100 group-hover:opacity-100 shrink-0" title="Редагувати SKU">
                                <i class="fa-solid fa-pencil text-[9px]"></i>
                            </button>
                        </div>
                    </div>
                    <div class="text-right shrink-0">
                        <div class="flex items-center justify-end gap-1 font-medium ${qi[1]}">
                            <span>${qi[0]}</span>
                            <button onclick="event.stopPropagation(); openEditModal(${it.item_id}, 'balance', '${it.quantity}', 'Залишок (кількість)')" class="text-slate-500 hover:text-blue-400 p-0.5 rounded transition opacity-0 hover:opacity-100 group-hover:opacity-100" title="Коригувати кількість/залишок">
                                <i class="fa-solid fa-pencil text-[10px]"></i>
                            </button>
                        </div>
                        <div class="flex items-center justify-end gap-1 text-[10px] text-slate-400 mt-0.5">
                            <span>${esc(it.unit || '')}</span>
                            <button onclick="event.stopPropagation(); openEditModal(${it.item_id}, 'unit', '${esc(it.unit)}', 'Одиниця виміру')" class="text-slate-500 hover:text-blue-400 p-0.5 rounded transition opacity-0 hover:opacity-100 group-hover:opacity-100" title="Редагувати одиницю виміру">
                                <i class="fa-solid fa-pencil text-[9px]"></i>
                            </button>
                        </div>
                    </div>
                </div>`;
            });
            itemsList.innerHTML = listHtml;
        }
    } catch (e) {
        rawEl.textContent = 'Помилка завантаження OCR: ' + e.message;
    }
}

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

// ---- Log Console Logic ----

let allLogs = [];
let lastLogId = 0;
let autoScroll = true;
let logEventSource = null;
let logPollInterval = null;

function toggleAutoScroll() {
    const el = document.getElementById('log-autoscroll');
    autoScroll = el ? el.checked : true;
    if (autoScroll) {
        scrollLogsToBottom();
    }
}

function scrollLogsToBottom() {
    const term = document.getElementById('log-terminal');
    if (term) {
        term.scrollTop = term.scrollHeight;
    }
}

async function fetchLogs() {
    try {
        const res = await fetch('/api/logs?since_id=' + lastLogId);
        if (!res.ok) return;
        const data = await res.json();
        if (data.logs && data.logs.length > 0) {
            appendLogs(data.logs);
        }
        if (data.last_id) {
            lastLogId = Math.max(lastLogId, data.last_id);
        }
        updateLogBadge(data.total_count || allLogs.length);
    } catch (e) {
        console.error('Fetch logs error:', e);
    }
}

function updateLogBadge(totalCount) {
    const badge = document.getElementById('logs-count');
    if (badge) {
        badge.textContent = totalCount;
    }
}

function appendLogs(newEntries) {
    if (!newEntries || newEntries.length === 0) return;
    const existingIds = new Set(allLogs.map(l => l.id));
    for (const entry of newEntries) {
        if (!existingIds.has(entry.id)) {
            allLogs.push(entry);
            existingIds.add(entry.id);
            if (entry.id > lastLogId) {
                lastLogId = entry.id;
            }
        }
    }
    if (allLogs.length > 5000) {
        allLogs = allLogs.slice(-5000);
    }
    renderLogs();
    updateLogBadge(allLogs.length);
}

function onLogFilterChange() {
    renderLogs();
}

function renderLogs() {
    const container = document.getElementById('log-lines');
    const emptyState = document.getElementById('log-empty-state');
    const ratioEl = document.getElementById('log-count-ratio');
    if (!container) return;

    const query = (document.getElementById('log-search-input')?.value || '').toLowerCase().trim();
    const showInfo = document.getElementById('lvl-info')?.checked ?? true;
    const showSuccess = document.getElementById('lvl-success')?.checked ?? true;
    const showWarn = document.getElementById('lvl-warn')?.checked ?? true;
    const showErr = document.getElementById('lvl-err')?.checked ?? true;

    const filtered = allLogs.filter(entry => {
        const lvl = (entry.level || 'INFO').toUpperCase();
        if (lvl === 'INFO' && !showInfo) return false;
        if (lvl === 'SUCCESS' && !showSuccess) return false;
        if (lvl === 'WARN' && !showWarn) return false;
        if (lvl === 'ERR' && !showErr) return false;

        if (query) {
            const text = (entry.timestamp + ' ' + entry.level + ' ' + entry.logger + ' ' + entry.message + ' ' + (entry.raw || '')).toLowerCase();
            if (!text.includes(query)) return false;
        }
        return true;
    });

    if (ratioEl) {
        ratioEl.textContent = filtered.length + '/' + allLogs.length;
    }

    if (filtered.length === 0) {
        container.innerHTML = '';
        if (emptyState) emptyState.classList.remove('hidden');
        return;
    }

    if (emptyState) emptyState.classList.add('hidden');

    let html = '';
    for (const l of filtered) {
        const lvl = (l.level || 'INFO').toUpperCase();
        let lvlBg = 'bg-sky-500/10 text-sky-400 border border-sky-500/20';
        if (lvl === 'SUCCESS') {
            lvlBg = 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20';
        } else if (lvl === 'WARN') {
            lvlBg = 'bg-amber-500/10 text-amber-400 border border-amber-500/20';
        } else if (lvl === 'ERR') {
            lvlBg = 'bg-rose-500/10 text-rose-400 border border-rose-500/20';
        } else if (lvl === 'DEBUG') {
            lvlBg = 'bg-purple-500/10 text-purple-400 border border-purple-500/20';
        }

        const ts = esc(l.timestamp || '');
        const lg = esc(l.logger || '');
        const msg = esc(l.message || '');

        let formattedMsg = msg;
        if (query) {
            const regex = new RegExp('(' + query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'gi');
            formattedMsg = formattedMsg.replace(regex, '<mark class="bg-yellow-500/30 text-yellow-200 px-0.5 rounded">$1</mark>');
        }

        html += `<div class="hover:bg-slate-900/60 py-0.5 px-1.5 rounded transition flex items-start gap-2 text-[11px] font-mono leading-relaxed border-b border-slate-900/40">
            <span class="text-slate-500 shrink-0 select-none">${ts}</span>
            <span class="px-1.5 py-0.2 rounded text-[10px] font-bold shrink-0 ${lvlBg}">${lvl}</span>
            <span class="text-slate-400 shrink-0 select-none">[${lg}]</span>
            <span class="text-slate-200 break-words flex-1 select-text ${lvl === 'ERR' ? 'text-rose-300 font-semibold' : ''}">${formattedMsg}</span>
        </div>`;
    }

    container.innerHTML = html;

    if (autoScroll) {
        scrollLogsToBottom();
    }
}

async function clearLogsServer() {
    try {
        await fetch('/api/logs/clear', { method: 'POST' });
        allLogs = [];
        lastLogId = 0;
        renderLogs();
        updateLogBadge(0);
    } catch (e) {
        console.error('Clear logs error:', e);
    }
}

function connectLogStream() {
    try {
        if (window.EventSource) {
            logEventSource = new EventSource('/api/logs/stream');
            logEventSource.onmessage = function(event) {
                try {
                    const entry = JSON.parse(event.data);
                    appendLogs([entry]);
                } catch (err) {
                    console.error('SSE parse error:', err);
                }
            };
            logEventSource.onerror = function() {
                if (!logPollInterval) {
                    logPollInterval = setInterval(fetchLogs, 2000);
                }
            };
        } else {
            logPollInterval = setInterval(fetchLogs, 2000);
        }
    } catch (e) {
        logPollInterval = setInterval(fetchLogs, 2000);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    refreshAll();
    fetchLogs();
    connectLogStream();
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
        log_buffer: Optional[LogBuffer] = None,
        queue_service: Optional[Any] = None,
    ) -> None:
        self._db = warehouse_db
        self._fs = file_store
        self._vs = vector_store
        self._owner_id = owner_user_id
        self._host = host
        self._port = port
        self._log_buffer = log_buffer or get_global_log_buffer()
        self._queue_service = queue_service
        setup_logging_capture(buffer=self._log_buffer)

        self._app = web.Application(client_max_size=50 * 1024 * 1024)
        self._setup_routes()
        self._runner: web.AppRunner | None = None
        self._site: web.TCPSite | None = None

    def _setup_routes(self) -> None:
        self._app.router.add_get("/", self._index)
        self._app.router.add_get("/api/warehouse/items", self._api_items)
        self._app.router.add_get("/api/warehouse/items/{item_id}/transactions", self._api_item_transactions)
        self._app.router.add_post("/api/warehouse/items/{item_id}/edit", self._api_edit_item)
        self._app.router.add_patch("/api/warehouse/items/{item_id}", self._api_edit_item)
        self._app.router.add_post("/api/warehouse/items/{item_id}", self._api_edit_item)
        self._app.router.add_get("/api/warehouse/documents", self._api_documents)
        self._app.router.add_post("/api/warehouse/documents/{doc_id}/retry", self._api_retry_document)
        self._app.router.add_get("/api/warehouse/documents/{doc_id}/impact", self._api_document_impact)
        self._app.router.add_get("/api/warehouse/documents/{doc_id}/ocr", self._api_document_ocr)
        self._app.router.add_get("/api/warehouse/documents/{doc_id}/view", self._api_document_view)
        self._app.router.add_get("/api/warehouse/documents/{doc_id}/download", self._api_document_download)
        self._app.router.add_get("/api/warehouse/documents/{doc_id}/preview", self._api_document_preview)
        self._app.router.add_delete("/api/warehouse/documents/{doc_id}", self._api_delete_document)
        self._app.router.add_post("/api/warehouse/import", self._api_import_excel)
        self._app.router.add_get("/api/warehouse/export", self._api_export_excel)
        self._app.router.add_get("/api/logs", self._api_logs)
        self._app.router.add_post("/api/logs/clear", self._api_clear_logs)
        self._app.router.add_delete("/api/logs", self._api_clear_logs)
        self._app.router.add_get("/api/logs/stream", self._api_stream_logs)

    async def _index(self, request: web.Request) -> web.Response:
        return web.Response(text=HTML_PAGE, content_type="text/html")

    async def _api_items(self, request: web.Request) -> web.Response:
        items = self._db.get_items_with_balance()
        return web.json_response(items)

    async def _api_item_transactions(self, request: web.Request) -> web.Response:
        item_id = int(request.match_info["item_id"])
        txs = self._db.get_item_transactions(item_id)
        return web.json_response(txs)

    async def _api_edit_item(self, request: web.Request) -> web.Response:
        try:
            item_id = int(request.match_info["item_id"])
        except (KeyError, ValueError):
            return web.json_response({"error": "Некоректний ID позиції"}, status=400)

        try:
            data = await request.json()
        except Exception:
            return web.json_response({"error": "Некоректний JSON"}, status=400)

        if not isinstance(data, dict):
            return web.json_response({"error": "Тіло запиту має бути JSON об'єктом"}, status=400)

        field = data.get("field")
        value = data.get("value")
        comment = data.get("comment", "")

        allowed_fields = {"name", "sku", "unit", "supplier", "notes", "balance", "quantity", "min_balance"}
        if not field:
            matching_fields = [k for k in data.keys() if k in allowed_fields]
            if len(matching_fields) == 1:
                field = matching_fields[0]
                value = data[field]
            else:
                return web.json_response({"error": "Не вказано поле для редагування ('field')"}, status=400)

        if field not in allowed_fields:
            return web.json_response(
                {"error": f"Непідтримуване поле: {field}. Дозволені: {sorted(allowed_fields)}"},
                status=400,
            )

        if value is None or (isinstance(value, str) and not value.strip() and field in {"balance", "quantity"}):
            return web.json_response({"error": "Значення ('value') не може бути порожнім/null"}, status=400)

        item = self._db.get_item(item_id)
        if not item:
            return web.json_response({"error": "Позицію не знайдено"}, status=404)

        if field == "min_balance":
            try:
                min_val = float(value) if value not in (None, "") else 0.0
                if min_val < 0:
                    min_val = 0.0
            except (ValueError, TypeError):
                return web.json_response({"error": "Значення мінімального залишку має бути числом"}, status=400)

            try:
                result = self._db.adjust_item_field(
                    item_id=item_id,
                    field="min_balance",
                    new_value=min_val,
                    comment=str(comment or ""),
                )
            except Exception as exc:
                logger.error("Error adjusting item min_balance: %s", exc)
                return web.json_response({"error": f"Помилка оновлення: {exc}"}, status=400)

            if not result:
                return web.json_response({"error": "Позицію не знайдено"}, status=404)

            return web.json_response(result)

        if field in {"balance", "quantity"}:
            try:
                target_qty = float(value)
            except (ValueError, TypeError):
                return web.json_response({"error": "Значення кількості має бути числом"}, status=400)

            try:
                result = self._db.adjust_item_quantity(
                    item_id=item_id,
                    target_quantity=target_qty,
                    comment=str(comment or ""),
                )
            except Exception as exc:
                logger.error("Error adjusting item quantity: %s", exc)
                return web.json_response({"error": f"Помилка оновлення кількості: {exc}"}, status=400)

            if not result:
                return web.json_response({"error": "Позицію не знайдено"}, status=404)

            updated_item = self._db.get_item(item_id)
            if updated_item:
                updated_item["balance"] = target_qty
                result["item"] = updated_item

            return web.json_response(result)

        try:
            result = self._db.adjust_item_field(
                item_id=item_id,
                field=field,
                new_value=str(value),
                comment=str(comment or ""),
            )
        except Exception as exc:
            logger.error("Error adjusting item field: %s", exc)
            return web.json_response({"error": f"Помилка оновлення: {exc}"}, status=400)

        if not result:
            return web.json_response({"error": "Позицію не знайдено"}, status=404)

        return web.json_response(result)

    async def _api_documents(self, request: web.Request) -> web.Response:
        docs = self._db.get_documents()
        return web.json_response(docs)

    async def _api_retry_document(self, request: web.Request) -> web.Response:
        try:
            doc_id = int(request.match_info["doc_id"])
        except (KeyError, ValueError):
            return web.json_response({"error": "Некоректний ID документа"}, status=400)

        doc = self._db.get_document(doc_id)
        if not doc:
            return web.json_response({"error": "Документ не знайдено"}, status=404)

        # Reset status to queued in DB
        self._db.update_document(doc_id, status="queued", error_message="")

        if self._queue_service:
            try:
                await self._queue_service.retry_document(doc_id)
            except Exception as exc:
                logger.error("Error re-enqueuing document %d: %s", doc_id, exc)

        updated_doc = self._db.get_document(doc_id)
        return web.json_response({
            "success": True,
            "status": "queued",
            "document": updated_doc,
        })

    async def _api_document_impact(self, request: web.Request) -> web.Response:
        doc_id = int(request.match_info["doc_id"])
        impact = self._db.get_document_impact(doc_id)
        return web.json_response(impact)

    async def _api_document_ocr(self, request: web.Request) -> web.Response:
        doc_id = int(request.match_info["doc_id"])
        doc = self._db.get_document(doc_id)
        if not doc:
            return web.json_response({"error": "Документ не знайдено"}, status=404)
        impact = self._db.get_document_impact(doc_id)
        raw_text = ""
        # 1. Try reading from .txt file on disk via FileStore or direct file_path
        stems_to_try: list[str] = []
        if doc.get("file_path"):
            stems_to_try.append(os.path.splitext(os.path.basename(doc["file_path"]))[0])
            txt_direct = os.path.splitext(doc["file_path"])[0] + ".txt"
            if os.path.exists(txt_direct):
                try:
                    with open(txt_direct, "r", encoding="utf-8") as f:
                        raw_text = f.read()
                except Exception:
                    pass
        if not raw_text and doc.get("filename"):
            stems_to_try.append(os.path.splitext(os.path.basename(doc["filename"]))[0])
        stems_to_try.append(str(doc_id))

        if not raw_text:
            for stem in stems_to_try:
                if stem:
                    try:
                        t = self._fs.read_text(stem)
                        if isinstance(t, str) and t:
                            raw_text = t
                            break
                    except Exception:
                        pass

        # 2. Fallback to DB raw_text
        if not raw_text:
            raw_text = doc.get("raw_text", "")
            if not isinstance(raw_text, str):
                raw_text = str(raw_text or "")

        return web.json_response({
            "id": doc["id"],
            "filename": doc["filename"],
            "file_type": doc["file_type"],
            # Усі пʼять полів розпізнавання присутні завжди: порожнє — порожній рядок, а не пропущений ключ.
            "doc_type": doc.get("doc_type") or "",
            "doc_number": doc.get("doc_number") or "",
            "doc_date": doc.get("doc_date") or "",
            "requested_by": doc.get("requested_by") or "",
            "requested_via": doc.get("requested_via") or "",
            "raw_text": raw_text,
            "impact": impact,
            "status": doc.get("status", "completed"),
            "error_message": doc.get("error_message", ""),
        })

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
            min_bal_val = row.get("min_balance")
            min_bal = float(min_bal_val) if min_bal_val is not None else 0.0
            existing = self._db.find_item(sku=row.get("sku", ""), name=row["name"])
            if existing:
                item_id = existing["id"]
                items_updated += 1
                update_kwargs: dict[str, Any] = {
                    "sku": row.get("sku", ""),
                    "unit": row.get("unit", ""),
                    "supplier": row.get("supplier", ""),
                    "notes": row.get("notes", ""),
                }
                if min_bal_val is not None:
                    update_kwargs["min_balance"] = min_bal
                self._db.update_item(
                    item_id,
                    **update_kwargs,
                )
            else:
                item_id = self._db.add_item(
                    name=row["name"],
                    sku=row.get("sku", ""),
                    unit=row.get("unit", ""),
                    supplier=row.get("supplier", ""),
                    notes=row.get("notes", ""),
                    min_balance=min_bal,
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
                self._db.add_transaction(
                    item_id=item_id, document_id=doc_id,
                    operation_type="expense", quantity=qty,
                    doc_number=row.get("doc_number", ""),
                    doc_date=row.get("doc_date", ""),
                    source_row=source_row,
                )
                transactions_created += 1
            else:
                created_any = False
                if income and float(income) > 0:
                    self._db.add_transaction(
                        item_id=item_id, document_id=doc_id,
                        operation_type="income", quantity=float(income),
                        doc_number=row.get("doc_number", ""),
                        doc_date=row.get("doc_date", ""),
                        source_row=source_row,
                    )
                    transactions_created += 1
                    created_any = True
                if expense and float(expense) > 0:
                    self._db.add_transaction(
                        item_id=item_id, document_id=doc_id,
                        operation_type="expense", quantity=float(expense),
                        doc_number=row.get("doc_number", ""),
                        doc_date=row.get("doc_date", ""),
                        source_row=source_row,
                    )
                    transactions_created += 1
                    created_any = True

                if not created_any:
                    bal_qty = float(balance) if balance else 0.0
                    self._db.add_transaction(
                        item_id=item_id, document_id=doc_id,
                        operation_type="income", quantity=max(bal_qty, 0.0),
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

    async def _api_logs(self, request: web.Request) -> web.Response:
        try:
            since_id = int(request.query.get("since_id", 0))
        except ValueError:
            since_id = 0
        try:
            limit = int(request.query.get("limit", 1000))
        except ValueError:
            limit = 1000
        level = request.query.get("level")
        query = request.query.get("q")

        entries, total, last_id = self._log_buffer.get_logs(
            since_id=since_id,
            limit=limit,
            level=level,
            query=query,
        )
        return web.json_response({
            "logs": [e.to_dict() for e in entries],
            "total_count": total,
            "last_id": last_id,
        })

    async def _api_clear_logs(self, request: web.Request) -> web.Response:
        count = self._log_buffer.clear()
        return web.json_response({"success": True, "cleared_count": count})

    async def _api_stream_logs(self, request: web.Request) -> web.StreamResponse:
        resp = web.StreamResponse(
            status=200,
            reason="OK",
            headers={
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
        await resp.prepare(request)

        queue = self._log_buffer.subscribe()
        try:
            # Send initial ping comment
            await resp.write(b": ping\n\n")
            while True:
                try:
                    entry = await asyncio.wait_for(queue.get(), timeout=15.0)
                    data_str = json.dumps(entry.to_dict(), ensure_ascii=False)
                    payload = f"data: {data_str}\n\n"
                    await resp.write(payload.encode("utf-8"))
                except asyncio.TimeoutError:
                    # Heartbeat comment to prevent client timeout
                    await resp.write(b": ping\n\n")
        except (asyncio.CancelledError, ConnectionResetError):
            pass
        finally:
            self._log_buffer.unsubscribe(queue)

        return resp

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
