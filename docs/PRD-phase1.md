# PRD: kolobot Phase 1 — Smart Gemini Archive Bot

**Product:** kolobot (KoloBot — Smart Gemini Archive Bot)  
**Platform:** Telegram (Python)  
**Status:** Locked Phase 1 (post design grill, July 2026)  
**Repo state at authoring:** greenfield (no application code yet)

---

## Problem Statement

As a personal user, I accumulate photos of receipts, contracts, notes, and screenshots across chats and camera rolls. Finding a specific fact later (“what did I pay for the repair?”) means scrolling galleries or re-opening blurry images. I want a private Telegram bot that:

1. Accepts my images,
2. Extracts structured meaning with Gemini OCR,
3. Lets me confirm before anything is indexed,
4. Answers natural-language questions over my archive,
5. Can re-send the original file in one tap,
6. Keeps working on Google Free Tier by rotating multiple API keys without constant 429 failures,
7. Never serves other Telegram users (personal bot only).

Without access control, a stable key pool, confirm-before-index, and basic list/delete, a “smart archive” either burns quota, indexes garbage, or becomes a write-only folder I cannot manage.

---

## Solution

kolobot is an asynchronous personal Telegram bot (aiogram v3) that:

- Accepts **images only** (Telegram photo or image document).
- Runs **Gemini vision pre-structure** (English system prompts) into a semi-structured JSON card plus raw text.
- Shows a **Ukrainian confirm card**; only on **Save** embeds and upserts into **ChromaDB** (source of truth) and best-effort promotes a file under `./downloads`.
- Answers free-text questions with **RAG** (top-3, hard distance cutoff, up to three original-file buttons).
- Provides **/list** and **/delete** with inline confirms (Chroma + disk).
- Uses dual in-memory **Key Pools** (`GENERATE` and `EMBED`), overlap of physical keys allowed, cooldown on 429, short wait-then-sorry on exhaustion.
- Rejects non-owners politely; rejects albums and non-images with clear UX copy.

UI language is Ukrainian; Gemini system/instruction prompts are English.

---

## User Stories

1. As the owner, I want only my Telegram `user_id` to use the bot, so that strangers cannot burn my Gemini quota or read my archive.
2. As a non-owner, I want a polite access-denied message and no API calls, so that the bot fails closed without leaking behavior details.
3. As the owner, I want `/start` to confirm the bot is mine and ready, so that I know whitelist and startup succeeded.
4. As the owner, I want `/help` in Ukrainian describing image upload, Q&A, `/list`, `/delete`, and limits (one image at a time, images only), so that I do not need external docs day to day.
5. As the owner, I want `/status` showing generate/embed key availability (counts in cooldown vs free, never raw secrets), document count, and basic path health, so that I can debug quota issues on Windows.
6. As the owner, I want to send a Telegram **photo** and have the bot use the largest available size, so that OCR gets the best Telegram-compressed image.
7. As the owner, I want to send an image as a **document** (`jpeg`/`png`/`webp`) so that I can preserve quality better than compressed photos.
8. As the owner, I want non-image documents (PDF, DOCX, etc.) rejected with a clear Ukrainian message, so that I am not stuck on a silent failure.
9. As the owner, I want images larger than the bot API practical cap (~20MB) rejected clearly, so that downloads do not hang or crash the process.
10. As the owner, I want Telegram **albums** (`media_group_id`) rejected with a single debounced message “send one photo at a time”, so that single-flight confirm is not corrupted and I do not silently lose files.
11. As the owner, I want duplicate detection by `file_unique_id` **before** OCR, so that I do not waste GENERATE quota on known files.
12. As the owner, when a duplicate is found, I want buttons **[Відкрити старий]** and **[Все одно зберегти]**, so that I can either retrieve the existing original or force a new archive entry.
13. As the owner, when I choose **[Відкрити старий]**, I want the bot to send the prior original via `telegram_file_id` (and show identity context), so that I get the file immediately.
14. As the owner, when I choose **[Все одно зберегти]**, I want a full new OCR → confirm → **new `doc_id`** path, so that intentional second copies are possible.
15. As the owner, I want duplicate warn UI **not** to block single-flight the same way OCR confirm does (per locked design), so that dedup friction stays low—while OCR confirm remains single-flight.
16. As the owner, after a new image is accepted, I want a progress message such as “Розпізнаю…”, so that I know the bot is working during Gemini latency.
17. As the owner, I want Gemini vision to return semi-structured JSON (`doc_type`, `title`, `summary`, `key_value_pairs`, `raw_text`, `language`) plus usable raw text, so that both facts and full text can be indexed.
18. As the owner, if structured JSON is invalid once, I want one retry with a stricter repair-oriented prompt, so that transient model failures do not drop the file.
19. As the owner, if JSON still fails after retry, I want a **raw fallback** card (e.g. `doc_type=other`, summary from leading raw text) still offered for confirm, so that I can save something useful instead of a hard fail.
20. As the owner, I want a confirm **card only** (title, type, summary, up to ~8 key-value pairs)—not full raw in chat—so that Telegram’s 4096 limit is respected and confirm stays scannable.
21. As the owner, I want **[Зберегти]** and **[Відхилити]** on the confirm card, so that bad OCR never enters the vector archive without my consent.
22. As the owner, when I reject, I want temp files removed and no Chroma write, so that the archive stays clean.
23. As the owner, when OCR yields empty/unusable text even after fallback policy, I want no Save affordance and a request to reshoot, so that empty documents are not indexed.
24. As the owner, I want only **one** pending confirm at a time (single-flight); if I send another image during confirm, I want an explicit “finish Save/Reject first” message, so that state does not race.
25. As the owner, if I abandon confirm for **10 minutes**, I want auto-reject, tmp cleanup, and the ability to upload again, so that the bot cannot soft-lock forever on Windows.
26. As the owner, on Save I want a stable short UUID `doc_id`, so that list/delete/callbacks share one identifier.
27. As the owner, on Save I want text embedded with `text-embedding-004` and stored in Chroma as **one document blob** (title+summary+KVs+raw) with rich metadata, so that semantic search works.
28. As the owner, I want Chroma to be the **source of truth**: successful embed+upsert means “saved”, so that search/list always reflect committed archive state.
29. As the owner, I want the image promoted from `./downloads/tmp/...` to `./downloads/{doc_id}{ext}` best-effort after Chroma success, so that I have a local backup when disk works.
30. As the owner, if disk promote fails after Chroma success, I still want “saved” with a warning that local copy failed, so that RAG and Telegram re-send still work via `file_id`.
31. As the owner, if Chroma/embed fails, I want a clear failure, no successful-save claim, and tmp retained until reject/timeout, so that I can retry without silent data loss.
32. As the owner, I want metadata to include at least `user_id`, `telegram_file_id`, `file_unique_id`, `file_name` (when present), mime/type, source (`photo`|`document`), `created_at`, so that delivery, dedup, and list work.
33. As the owner, I want free-text messages (outside commands and confirm FSM) to run RAG, so that I can ask natural questions like “Яка сума була в чеку за ремонт?”
34. As the owner, I want trivial messages such as “ок” / “дякую” / bare thumbs-up ignored without calling Gemini, so that chit-chat does not waste quota.
35. As the owner, if my archive has zero documents, I want “Архів порожній…” without useless generate calls, so that empty state is honest and cheap.
36. As the owner, if top hits fail a configurable hard distance/similarity cutoff, I want “Не знайшов…” without generate, so that the bot does not hallucinate from irrelevant neighbors.
37. As the owner, on a successful retrieval I want an answer grounded in top-**3** chunks/docs with anti-hallucination instructions, so that answers stay faithful to sources.
38. As the owner, under a RAG answer I want up to **3** inline buttons to fetch originals for distinct source files, so that I can open evidence immediately (US4).
39. As the owner, when multiple chunks share one `doc_id`, I want original buttons deduplicated per file, so that the keyboard is not noisy.
40. As the owner, I want originals sent primarily via `telegram_file_id`, so that re-delivery is instant without re-upload.
41. As the owner, if `file_id` send fails, I want best-effort fallback from disk when the local file exists, so that delivery is more resilient.
42. As the owner, I want `/list` to show the latest **10** documents (title/name + date) with **[Файл]** and **[🗑]** actions, so that I can browse without semantic search.
43. As the owner, I want **[Файл]** from list to send the original, so that management UX matches RAG source buttons.
44. As the owner, I want **[🗑]** to ask **[Так]/[Ні]** confirmation naming the document, so that mis-taps do not destroy data.
45. As the owner, on confirmed delete I want Chroma deletion and disk delete with ignore-missing, so that both index and backup stay consistent enough for Phase 1.
46. As the owner, I want an optional `/delete <id>` power-user path consistent with the same cascade rules, so that I can delete without hunting in list when I know the id.
47. As the owner, I want GENERATE pool keys used for vision OCR and for RAG answer generation, so that all `generateContent`-style calls share one tracked budget.
48. As the owner, I want EMBED pool keys used only for embeddings (query + document), so that embed quotas are tracked separately.
49. As the owner, I want the same physical API key string allowed in both pools with **separate** RPM/RPD/cooldown trackers per `(key, pool)`, so that two–three Free Tier keys remain usable.
50. As the owner, I want sliding-window RPM (default 15) and RPD (default 1500) per key per pool, round-robin across free keys, and `asyncio.Lock` during selection, so that concurrent tasks do not race the pool.
51. As the owner, on HTTP 429 I want that key cooled down for 60 seconds and the call retried on another key when possible, so that transient quota errors self-heal.
52. As the owner, when no key is free, I want a short wait/retry through cooldowns then a Ukrainian “try later” style message, so that the bot does not hang forever or die silently.
53. As the owner, I want pool limit state **in-memory only** in Phase 1, accepting reset on process restart, so that implementation stays simple on always-on Windows.
54. As the owner, I want secrets and tunables in `.env` (`BOT_TOKEN`, `OWNER_USER_ID`, comma-separated key lists, paths, RPM/RPD/cooldown, `RAG_TOP_K`, `RAG_MAX_DISTANCE`, `CONFIRM_TIMEOUT_SEC=600`), so that nothing secret is hardcoded.
55. As the owner, on bot startup I want `./downloads/tmp` wiped, so that crash mid-confirm does not leave blocking temp junk (final orphans outside tmp are not auto-deleted in Phase 1).
56. As the owner, I want the bot fully async so Telegram handling does not freeze during Gemini or disk I/O, so that the chat stays responsive.
57. As the owner, I want Chroma PersistentClient so archive survives restarts, so that I do not re-upload after reboots.
58. As the developer, I want deep modules with narrow interfaces (KeyPool, DocStructurer, VectorStore, FileStore, gateways/services) unit-tested with mocks, so that rate limiting and save ordering do not regress without live Telegram/Gemini.
59. As the owner, I want all owner-facing bot strings in Ukrainian, so that daily use matches my language.
60. As the developer, I want Gemini system prompts in English for structured extraction and RAG, so that JSON adherence and instruction following stay more reliable.

---

## Implementation Decisions

### Architecture / modules (deep modules preferred)

Greenfield layout conceptually (names indicate responsibility, not mandatory filenames):

1. **Config**  
   Load and validate `.env`: tokens, owner id, dual key lists, paths, numeric limits. Fail fast on missing required values. No secrets in source.

2. **KeyPool (×2 logical pools, shared implementation)**  
   Deep module: given pool kind (`generate` | `embed`) and a key list, select a usable key under sliding RPM/RPD, round-robin, per-key cooldown on 429, async lock-safe. Report status snapshot for `/status` without exposing secrets. Overlap of key strings across pools is allowed; trackers are per `(key, pool_kind)`.

3. **GeminiGateway**  
   Thin-ish adapter over `google-genai`:  
   - `extract_document(image_bytes, mime) -> raw model text` via GENERATE pool + `gemini-2.5-flash` vision  
   - `embed_texts(texts) -> vectors` via EMBED pool + `text-embedding-004`  
   - `answer_with_context(question, contexts) -> answer` via GENERATE pool  
   Encapsulates retries that are API-transport level; pool exhaustion policy surfaces as structured errors to services.

4. **DocStructurer**  
   Pure-ish domain module: prompt contract, parse JSON, validate schema, one retry policy hook input/output, raw fallback, **card view model** for Telegram (truncate to ≤8 KVs, length-safe). No I/O.

5. **VectorStore**  
   Chroma PersistentClient wrapper: upsert one blob doc + metadata + embedding, query top-k with optional distance metadata, get/list recent by `created_at`, delete by `doc_id`, count, lookup by `file_unique_id`. Always conceptually filter by owner `user_id` even though Phase 1 is single-user (keeps isolation invariant).

6. **FileStore**  
   Temp path under `./downloads/tmp`, promote to `./downloads/{doc_id}{ext}`, delete tmp, delete final ignore-missing, startup GC of tmp only. No Chroma knowledge.

7. **ArchiveService**  
   Orchestrates ingest after user Save (and the pre-Save OCR path coordination):  
   assign `doc_id`, call embed, upsert Chroma (SoT), best-effort promote disk, compose user-facing success/warning/failure. Dedup lookup before OCR lives at service or handler+service boundary using VectorStore.

8. **RagService**  
   Embed query, short-circuit empty archive, VectorStore query, hard cutoff vs `RAG_MAX_DISTANCE` (or equivalent score config), build context, call generate answer, map sources to max 3 unique file buttons. No Telegram types in core if practical.

9. **AccessMiddleware / gate**  
   Allow only `OWNER_USER_ID`; polite reject otherwise; never call Gemini.

10. **Handlers (aiogram, intentionally thin)**  
    Commands (`/start`, `/help`, `/status`, `/list`, `/delete`), media handlers (photo/document), album debounce reject, dedup keyboard, confirm FSM single-flight + 10 min timeout checks, RAG on text, callback handlers for save/reject/list/delete/open. Ukrainian copy lives near handlers or a small messages module (shallow is fine).

### Product / behavior locks (from design grill)

- **Audience:** strict personal bot; access control day one.  
- **Ingest path:** images only → OCR pre-structure → confirm → embed/index. No “save without OCR” in Phase 1.  
- **Confirm:** card only; embedding only after Save.  
- **Concurrency:** single-flight pending confirm; albums rejected; 10 minutes auto-reject.  
- **Dedup:** `file_unique_id` before OCR; open existing or force new `doc_id` via full pipeline.  
- **Persistence:** Chroma SoT; disk best-effort backup; US4 primary `telegram_file_id`.  
- **Indexing:** one Chroma document per saved file; document text = title+summary+KVs+raw.  
- **Schema:** semi-structured bag, not receipt-only fixed fields; not two-pass classify+extract.  
- **RAG:** any non-command text (with trivial ignore list); top-3; ≤3 original buttons; hard distance cutoff; anti-hallucination prompt.  
- **Management:** `/list` last 10 + inline file/delete with confirm; delete cascades Chroma + disk ignore-missing.  
- **Keys:** `GEMINI_KEYS_GENERATE` + `GEMINI_KEYS_EMBED`; in-memory limits; 60s cooldown; wait-retry then sorry.  
- **Runtime:** local Windows always-on; startup tmp GC only.  
- **Languages:** UI uk; prompts en.  
- **Models:** `gemini-2.5-flash`, `text-embedding-004`.  
- **Stack:** Python 3.9+, aiogram v3, google-genai, chromadb PersistentClient.

### Identity & metadata

- Canonical id: short UUID hex (8–12 chars) as Chroma id and final filename stem.  
- Telegram `file_id` / `file_unique_id` stored in metadata, not used as canonical id.  
- Final path pattern: `./downloads/{doc_id}{ext}` (temp under `tmp/`).

### Save ordering

1. Embed via EMBED pool  
2. Chroma upsert success ⇒ committed  
3. Disk promote best-effort  
4. User message success or success+disk warning  
5. On Chroma failure ⇒ do not claim save; do not promote as committed final

### Delete ordering

1. Delete Chroma id (required for success)  
2. Delete disk path ignore-missing  
3. Confirm to user

### Config contract (minimal)

- `BOT_TOKEN`  
- `OWNER_USER_ID`  
- `GEMINI_KEYS_GENERATE` (comma-separated)  
- `GEMINI_KEYS_EMBED` (comma-separated)  
- `CHROMA_PATH`  
- `DOWNLOADS_PATH`  
- RPM / RPD / cooldown settings (generate & embed may share defaults)  
- `RAG_TOP_K=3`  
- `RAG_MAX_DISTANCE` (tunable)  
- `CONFIRM_TIMEOUT_SEC=600`

### Interactions (high level)

```
Non-owner update → polite reject
Album → debounced reject
Image → dedup? → (open | force pipeline | new pipeline)
New pipeline → download tmp → GENERATE OCR → structure/card → confirm FSM
Save → embed → Chroma → promote disk → done
Reject/timeout → wipe tmp → clear FSM
Text → (ignore trivial | RAG)
/list|/delete callbacks → file send or confirm cascade delete
```

---

## Testing Decisions

### What good tests look like

- Test **external behavior** of deep modules through their public interfaces (inputs/outputs, error classes, ordering guarantees).  
- Do **not** assert on private timers internals, Chroma private layout, or aiogram wiring details unless an integration harness exists.  
- **Mock** `google-genai` and, where needed, Chroma or filesystem boundaries; no live Telegram and no live Gemini required for CI/unit.  
- Prefer deterministic time injection for RPM windows, cooldowns, and confirm timeout logic.  
- One behavior per test; name after the user-visible or contract-visible outcome.

### Modules in mandatory Phase 1 test scope

| Module | Example behaviors to lock |
|---|---|
| **KeyPool** | Round-robin among free keys; RPM/RPD blocking; 429 → cooldown; lock-safe concurrent acquisition; status counts; exhaustion error |
| **DocStructurer** | Valid JSON → card; invalid → retry signal; second failure → raw fallback shape; card KV cap; length-safe card fields |
| **VectorStore** | Upsert+get; query returns distances; list recent limit 10 ordering; delete; lookup by `file_unique_id`; user filter invariant (contract with real or test client as practical) |
| **FileStore** | tmp write; promote renames/moves to final id; delete tmp; delete final ignore-missing; startup tmp GC does not touch finals |
| **RagService** | empty archive short-circuit; cutoff → not found without generate; top-k context assembly; source button dedupe ≤3 |
| **ArchiveService** | Save order embed→Chroma→disk; disk failure still success+warning; Chroma failure is hard failure without promote-as-saved |

### Out of automated test scope (Phase 1)

- Full aiogram FSM e2e against Telegram network  
- Live Gemini vision/embed quality  
- Pixel-perfect Ukrainian copy strings (optional snapshot later)  
- Windows Task Scheduler packaging

### Prior art

None in-repo (greenfield). Establish `pytest` layout from scratch beside the package; mock patterns should keep KeyPool and DocStructurer free of Telegram imports.

---

## Out of Scope

Phase 2+ / explicitly deferred:

- “Просто зберегти” / archive-only without OCR  
- PDF, DOCX, audio, video, arbitrary documents  
- Edit OCR text in Telegram before Save  
- Multi-pending confirms and album queues  
- Persistent key-pool timestamps (SQLite/Redis) across restarts  
- Automatic orphan reconcile between final disk files and Chroma  
- `/list` pagination beyond latest 10  
- Multi-user allowlist / public bot  
- Replace-in-place dedup (force always creates new `doc_id` in Phase 1)  
- Third key pool dedicated only to RAG  
- Job queue for delayed OCR when quota exhausted  
- Full end-to-end live Telegram/Gemini test suite in CI  
- Mobile/desktop apps outside Telegram  
- Cloud deploy (Docker/VPS) as a Phase 1 requirement (local Windows is the target)

---

## Further Notes

### Conscious deltas vs earlier draft PRD

1. Access control is **in** Phase 1, not future work.  
2. US1 dual menu dropped: **no** save-without-OCR path.  
3. Data management (`/list`, `/delete`) **pulled into** Phase 1.  
4. Dual pools named **GENERATE** and **EMBED** (not a single “OCR” pool with hidden RAG use).  
5. OCR is **pre-structure + confirm**, not fire-and-forget plain text.  
6. Disk is **best-effort backup**; Chroma is SoT (still keeps local files when possible, aligning with “downloads exist” intent without dual-write fragility).  
7. Albums rejected; single-flight; 10-minute confirm timeout.  
8. Automated unit/contract tests required for core deep modules.

### Implementation sequencing suggestion (non-binding)

Vertical slices work well: Config+KeyPool → GeminiGateway+DocStructurer → FileStore+VectorStore → ArchiveService+confirm handlers → RagService+text handlers → list/delete → /status and hardening.

### Open tuning knobs after first real usage

- Default `RAG_MAX_DISTANCE` will need empirical calibration on real embeddings.  
- RPM/RPD defaults (15 / 1500) must match current Google Free Tier reality at implement time—config must remain the source of truth.  
- Short UUID length (8 vs 12) can be fixed at implementation without further product change if callback_data size stays safe.

### Delivery artifact

This PRD is stored at `docs/PRD-phase1.md` because the workspace had no git remote/`gh` at authoring time. When a GitHub repository exists, open an issue with this body (or link the file) for tracking.

---

*Locked decisions originate from the Phase 1 design grill (July 2026). Treat this document as the product contract for implementation unless explicitly revised.*
