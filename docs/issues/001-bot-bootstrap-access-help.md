# 001 — Bot bootstrap: config, owner gate, `/start` `/help`

**Type:** AFK  
**Status:** Open  
**Parent:** [docs/PRD-phase1.md](../PRD-phase1.md)

## What to build

Stand up a runnable aiogram v3 bot process driven entirely by `.env`. On every update, enforce a strict personal allowlist (`OWNER_USER_ID`): non-owners receive a polite Ukrainian access-denied message and **no** Gemini or archive work runs. The owner can call `/start` (identity + ready confirmation) and `/help` (Phase 1 usage: one image at a time, images only, Q&A, future list/delete pointers as implemented later). This slice is the vertical shell: config load → middleware/gate → command handlers → process entrypoint.

## Acceptance criteria

- [ ] Required env vars validated at startup; missing secrets/config fail fast with a clear error (no hardcoded tokens/keys)
- [ ] Bot starts on local Windows with `BOT_TOKEN` from `.env`
- [ ] Non-owner messages/commands get a polite Ukrainian reject and never reach Gemini or storage side effects
- [ ] Owner `/start` responds in Ukrainian confirming personal-bot readiness
- [ ] Owner `/help` documents Phase 1 flows and limits (images only, one at a time, natural-language Q&A, list/delete when present)
- [ ] Handlers remain thin; access check is centralized (middleware or equivalent gate)
- [ ] No KeyPool/OCR/RAG required for this slice to demo

## Blocked by

None — can start immediately

## User stories

1–4, 54, 56, 59 (partial)
