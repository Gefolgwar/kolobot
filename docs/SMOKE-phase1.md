# Phase 1 Manual Smoke Checklist (Windows always-on)

**Prereqs:** Real `BOT_TOKEN` + Gemini API keys in `.env`, Python 3.9+, venv active.

```bash
pip install -e ".[dev]"
python -m kolobot.main
```

## Checklist

| # | Step | Expected result | Pass? |
|---|------|----------------|-------|
| 1 | Send a message from a **non-owner** Telegram account | Polite Ukrainian reject; no Gemini/storage side effects | |
| 2 | `/start` from owner | Ukrainian identity + readiness confirmation | |
| 3 | `/help` from owner | Phase 1 usage: images only, one at a time, Q&A, list/delete, /status | |
| 4 | `/status` from owner | Generate/Embed pool counts shown; **no raw API keys visible** | |
| 5 | Send a **single photo** (compressed) | "Розпізнаю…" → OCR card with title/type/summary/≤8 KVs | |
| 6 | Press **[Зберегти]** | "Збережено (id: ...)" — doc persists across bot restart | |
| 7 | Press **[Відхилити]** (on a new image) | "Відхилено" — tmp file deleted, no Chroma record | |
| 8 | Send **image as document** (jpeg/png/webp) | Accepted, same OCR flow as photo | |
| 9 | Send a **PDF** or non-image doc | Clear Ukrainian reject: "лише зображення" | |
| 10 | Send an **album** (multi-select photos) | One debounced reject: "по одному зображенню" | |
| 11 | Send a **second image** while confirm pending | "Спочатку заверши поточний документ" | |
| 12 | Re-send a **previously saved** image | Dedup warning: [Відкрити старий] / [Все одно зберегти] | |
| 13 | Press **[Відкрити старий]** | Original file sent via file_id | |
| 14 | Press **[Все одно зберегти]** | Full OCR → confirm → new doc_id | |
| 15 | Ask a question like "Яка сума в чеку?" | RAG answer with ≤3 source buttons | |
| 16 | Press a **📎 source button** | Original file sent | |
| 17 | Ask when **archive is empty** | "Архів порожній" (no Gemini calls) | |
| 18 | Send trivial text: "ок", "дякую", 👍 | No response (no Gemini calls) | |
| 19 | `/list` | Latest ≤10 docs with IDs | |
| 20 | `/delete <id>` | Confirm → delete from Chroma + disk | |
| 21 | Verify deleted doc gone from `/list` and RAG | Not found | |
| 22 | Wait **10+ minutes** with pending confirm | Auto-reject, tmp cleanup, can upload again | |
| 23 | **Restart bot** | `downloads/tmp` wiped; `downloads/{doc_id}.*` untouched; Chroma data survives | |
| 24 | `/status` after some use | Counts reflect actual key usage | |

## Security notes

- Secrets stay in `.env` — never committed to repo.
- `/status` must not show raw API key strings.
- Non-owner gets polite reject, zero Gemini/storage access.

---

*HITL: requires human with bot token + Gemini keys. Not CI-automatable.*
