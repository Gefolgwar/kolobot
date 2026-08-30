# 005 — Save: embed → Chroma SoT → disk best-effort

**Type:** AFK  
**Status:** Open  
**Parent:** [docs/PRD-phase1.md](../PRD-phase1.md)

## What to build

Implement **[Зберегти]** end-to-end via **ArchiveService** + **VectorStore** + **FileStore** + **EMBED** pool:

1. Allocate short UUID `doc_id` (8–12 hex)
2. Build **one document blob** = title + summary + KVs + raw
3. Embed with `text-embedding-004` through EMBED pool
4. Upsert Chroma (PersistentClient) with embedding, document, metadata (`user_id`, `telegram_file_id`, `file_unique_id`, `file_name`, mime/type, source, `created_at`, …) — **Chroma is source of truth**
5. Best-effort promote tmp → `./downloads/{doc_id}{ext}`
6. User message: success, or success + warning if disk failed; hard failure if embed/Chroma fails (no “saved”, no final promote-as-committed)

Owner can verify persistence across bot restart (Chroma durable). Save clears confirm pending.

## Acceptance criteria

- [ ] Save creates stable `doc_id` and one Chroma record with one-blob document text
- [ ] Metadata includes at least user_id, telegram_file_id, file_unique_id, file_name (if any), type/mime, source, created_at
- [ ] Embed uses EMBED pool and `text-embedding-004`
- [ ] Disk promote is best-effort after Chroma success; disk failure still reports saved + warning
- [ ] Chroma/embed failure does not claim success and does not leave a committed final+index pair inconsistently “OK”
- [ ] Chroma uses persistent path from config; data survives process restart
- [ ] Pending/tmp cleaned on successful save path as designed
- [ ] pytest: ArchiveService ordering (embed→Chroma→disk), disk-fail warning path, Chroma-fail hard fail
- [ ] VectorStore contract tests: upsert/get, delete, list-recent hook, lookup by file_unique_id (for 006)

## Blocked by

- Blocked by **004**

## User stories

26–32, 57, 58 (VectorStore, ArchiveService)
