# 007 — RAG Q&A + original buttons + hard cutoff

**Type:** AFK  
**Status:** Open  
**Parent:** [docs/PRD-phase1.md](../PRD-phase1.md)

## What to build

Owner free-text (not a command, not confirm FSM) flows through **RagService**:

1. Ignore trivial chit-chat (`ок`, `дякую`, thumbs-up, etc.) with no Gemini calls
2. If archive empty → Ukrainian empty-archive message (no generate)
3. Embed query via EMBED pool; VectorStore top-`RAG_TOP_K` (default 3) with distances
4. If best hit fails hard `RAG_MAX_DISTANCE` (or configured equivalent) → “Не знайшов…” **without** generate
5. Else GENERATE pool answers with English anti-hallucination system prompt + retrieved contexts; user-facing answer Ukrainian as appropriate
6. Attach up to **3** inline buttons for **distinct** source files (`telegram_file_id` primary send; disk fallback if available)

## Acceptance criteria

- [ ] Non-command owner text triggers RAG outside FSM
- [ ] Trivial messages do not call embed/generate
- [ ] Empty archive short-circuits without generate
- [ ] Hard distance cutoff yields not-found without generate
- [ ] Successful path uses top-3 context and GENERATE pool for the answer
- [ ] ≤3 original buttons, deduped by document/file
- [ ] Button sends original via file_id (disk fallback if implemented)
- [ ] pytest for RagService: empty, cutoff, source dedupe ≤3, “would call generate” vs not (mocked gateway)

## Blocked by

- Blocked by **005** (searchable archive)
- Uses pools from **002**

## User stories

33–41, 47–48
