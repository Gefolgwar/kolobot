# 008 — `/list` + `/delete` (inline confirm, cascade)

**Type:** AFK  
**Status:** Open  
**Parent:** [docs/PRD-phase1.md](../PRD-phase1.md)

## What to build

Owner archive management without semantic search:

- `/list` — latest **10** by `created_at` with title/name + date; each row actions **[Файл]** and **[🗑]**
- **[Файл]** — send original (`telegram_file_id`, disk fallback if present)
- **[🗑]** — confirm **[Так]|[Ні]** with document identity; on Yes: delete Chroma id (required) + disk ignore-missing
- Optional power-user `/delete <id>` using the same cascade rules

Update `/help` if needed so list/delete are documented.

## Acceptance criteria

- [ ] `/list` shows at most 10 newest docs with stable ids usable for delete
- [ ] File button delivers original
- [ ] Delete requires explicit confirm; No cancels without changes
- [ ] Yes deletes Chroma record and best-effort removes `./downloads/{doc_id}{ext}` (ignore missing)
- [ ] Deleted docs no longer appear in `/list` or RAG
- [ ] Optional `/delete <id>` behaves consistently or is explicitly omitted with reason in PR notes—if omitted, uncheck only after documenting; prefer implement alias
- [ ] Owner-only

## Blocked by

- Blocked by **005**

## User stories

42–46
