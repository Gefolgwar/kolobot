# 010 — Manual smoke checklist (Windows always-on)

**Type:** HITL  
**Status:** Open  
**Parent:** [docs/PRD-phase1.md](../PRD-phase1.md)

## What to build

Author a short **human** smoke checklist under `docs/` (e.g. `docs/SMOKE-phase1.md`) for local Windows runs with real Telegram + real Gemini keys. Not CI e2e. Steps should cover: non-owner reject, `/start` `/help` `/status`, image OCR confirm save, reject, duplicate warn, RAG hit/miss, list/file/delete, album reject, confirm timeout optional long-wait note, restart tmp GC / Chroma durability.

Operator records pass/fail; no automation required.

## Acceptance criteria

- [ ] Checklist file exists and matches locked Phase 1 PRD behavior
- [ ] Each critical path has an expected observable result
- [ ] Explicitly notes secrets stay in `.env` and `/status` must not show raw keys
- [ ] Marked HITL: requires human with bot token + Gemini keys

## Blocked by

- Blocked by **001–009** (full Phase 1 feature set)

## User stories

Cross-cutting manual verification
