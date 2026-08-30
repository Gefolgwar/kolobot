# 003 — Media intake: images only, album reject, FileStore tmp, single-flight shell

**Type:** AFK  
**Status:** Open  
**Parent:** [docs/PRD-phase1.md](../PRD-phase1.md)

## What to build

Accept owner media end-to-end into a safe on-disk temp area. Support Telegram **photo** (largest size) and **document** images (`image/jpeg|png|webp`) up to the practical ~20MB cap; reject other MIME/types with clear Ukrainian copy. Reject **albums** (`media_group_id`) with a **debounced** single reply per group (“send one at a time”). Implement **FileStore**: write tmp under `./downloads/tmp`, API for later promote to `./downloads/{doc_id}{ext}`, delete tmp/final (ignore-missing), and startup-ready tmp GC function (wiring of GC-on-boot can complete in 009 if needed, but API+tests land here).

Establish **single-flight** intake/pending lock for the owner: while a media pipeline slot is held, an additional image gets an explicit “finish current item first” style message (full confirm semantics complete in 004). Demo path may stop at “accepted into tmp / ready for OCR” without calling Gemini yet.

## Acceptance criteria

- [ ] Photo uses largest available Telegram size; image documents allowed for jpeg/png/webp only
- [ ] Non-images (e.g. PDF) rejected with clear Ukrainian message
- [ ] Oversize (~20MB) rejected clearly
- [ ] Albums rejected; at most one service message per `media_group_id` within debounce window
- [ ] Accepted media lands under `DOWNLOADS_PATH/tmp/...` via FileStore
- [ ] FileStore supports promote-to-`{doc_id}{ext}`, delete tmp, delete final ignore-missing
- [ ] Second concurrent image while slot held is rejected/explained (single-flight shell)
- [ ] pytest for FileStore tmp/promote/delete/GC-tmp-only behavior
- [ ] No Chroma commit and no Gemini required to demo this slice

## Blocked by

- Blocked by **001**

## User stories

6–10, 24 (shell), 55 (FileStore API), 58 (FileStore)
