# 009 — Hardening: confirm timeout, startup tmp GC, quota wait-then-sorry

**Type:** AFK  
**Status:** Open  
**Parent:** [docs/PRD-phase1.md](../PRD-phase1.md)

## What to build

Production-friction vertical polish on the already-working personal bot:

1. **Confirm timeout:** pending Save/Reject older than `CONFIRM_TIMEOUT_SEC` (600 → **10 minutes** per lock) auto-rejects, deletes tmp, clears FSM; next owner action can upload again. Prefer check-on-update and/or lightweight scheduling consistent with aiogram on Windows.
2. **Startup recovery:** on boot, wipe only `DOWNLOADS_PATH/tmp/**`; do not auto-delete final orphans outside tmp.
3. **Quota UX:** when GENERATE/EMBED pools are exhausted, short wait/retry through cooldowns then Ukrainian “try later” (or equivalent); do not silently strand confirm without feedback; do not implement durable job queues.

## Acceptance criteria

- [ ] Pending confirm expires after configured 10 minutes with tmp cleanup and user-visible cancellation (immediate or on next interaction—behavior documented and consistent)
- [ ] Process start clears `downloads/tmp` only
- [ ] Final `downloads/{doc_id}.*` not deleted by startup GC
- [ ] Pool exhaustion produces short wait/retry then clear sorry message on OCR and/or RAG paths
- [ ] No silent infinite hang on dead pools
- [ ] Tests or focused tests for timeout eligibility helper and/or tmp GC; quota messaging can be unit-tested at service boundary with fake pool exhaustion

## Blocked by

- Blocked by **004** (confirm pending exists)
- Practically after **002** (pools) and **003** (tmp); ideally after main paths **005–007** so UX is exercised on real flows

## User stories

25, 51–52, 55
