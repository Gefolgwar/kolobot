# 004 — OCR → structure → confirm card → Reject

**Type:** AFK  
**Status:** Open  
**Parent:** [docs/PRD-phase1.md](../PRD-phase1.md)

## What to build

Complete the pre-index vertical path: owner image already in tmp → progress “Розпізнаю…” → **GeminiGateway** vision call via **GENERATE** pool (`gemini-2.5-flash`) → **DocStructurer** parses semi-structured JSON (`doc_type`, `title`, `summary`, `key_value_pairs`, `raw_text`, `language`) with English prompts → on invalid JSON, **one retry**, then **raw fallback** → Ukrainian **confirm card only** (title, type, summary, ≤8 KVs; no full raw in chat; length-safe) with **[Зберегти]|[Відхилити]**.

**[Відхилити]** clears FSM/pending, deletes tmp, does **not** write Chroma or final downloads. **[Зберегти]** may show a stub “save coming” **or** no-op with message if 005 not merged—prefer wiring the callback to ArchiveService interface so 005 only fills implementation. Empty/unusable OCR: no Save affordance + reshoot message. Enforce single-flight around this confirm pending state.

## Acceptance criteria

- [ ] Successful image path shows progress then a length-safe Ukrainian card with ≤8 key-value pairs
- [ ] System/extraction prompts are English; user-visible strings Ukrainian
- [ ] Invalid model JSON triggers exactly one retry then raw fallback card still confirmable when text exists
- [ ] Empty/failed OCR does not offer Save; user told to reshoot/retry
- [ ] Reject deletes tmp, clears pending, no Chroma/final file
- [ ] GENERATE pool is used for vision calls (real or test double in integration)
- [ ] pytest for DocStructurer: valid parse, retry signal, raw fallback, KV cap / card safety
- [ ] Gemini client mocked in unit tests (no live API required for CI)

## Blocked by

- Blocked by **002** (GENERATE pool)
- Blocked by **003** (tmp intake + single-flight shell)

## User stories

16–23, 58–60 (and generate path toward 48–52)
