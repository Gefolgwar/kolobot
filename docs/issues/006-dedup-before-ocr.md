# 006 — Dedup before OCR (`file_unique_id`)

**Type:** AFK  
**Status:** Open  
**Parent:** [docs/PRD-phase1.md](../PRD-phase1.md)

## What to build

Before download/OCR, look up `file_unique_id` in Chroma/archive metadata. If found, show Ukrainian warn with **[Відкрити старий]** and **[Все одно зберегти]** (no GENERATE call yet).

- **Open existing:** send original via `telegram_file_id` (disk fallback optional if already implemented) and show identity context; do not create pending OCR confirm.
- **Force save:** run full pipeline (OCR → confirm → Save) and always allocate a **new `doc_id`** (second archive row allowed).

Dedup warn should follow PRD: not the same long-lived single-flight confirm lock as OCR card (avoid glueing warn to 10‑minute confirm); still behave sanely if user spams media.

## Acceptance criteria

- [ ] Known `file_unique_id` is detected before Gemini OCR/embed
- [ ] UI offers open existing vs force new
- [ ] Open existing delivers prior original without new OCR
- [ ] Force runs full OCR→confirm→save with a new `doc_id` (two rows possible)
- [ ] No false “already exists” for never-saved images
- [ ] Owner-only; non-owner still gated by 001

## Blocked by

- Blocked by **005** (indexed rows with `file_unique_id`)

## User stories

11–15
