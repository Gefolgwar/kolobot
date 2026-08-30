# kolobot Phase 1 — Issue board (local)

Source of truth for product: [../PRD-phase1.md](../PRD-phase1.md)

GitHub/`gh` was unavailable when these were created. Each file is an issue body ready for `gh issue create --title "..." --body-file ...`.

## Slices (dependency order)

| ID | Title | Type | Blocked by |
|----|--------|------|------------|
| [001](001-bot-bootstrap-access-help.md) | Bot bootstrap: config, owner gate, `/start` `/help` | AFK | — |
| [002](002-keypool-status.md) | Dual KeyPool + `/status` (+ tests) | AFK | 001 |
| [003](003-media-intake-filestore.md) | Media intake + FileStore + single-flight shell | AFK | 001 |
| [004](004-ocr-confirm-reject.md) | OCR → structure → confirm → Reject | AFK | 002, 003 |
| [005](005-save-chroma-disk.md) | Save: embed → Chroma SoT → disk | AFK | 004 |
| [006](006-dedup-before-ocr.md) | Dedup before OCR | AFK | 005 |
| [007](007-rag-qa-originals.md) | RAG Q&A + originals + cutoff | AFK | 005 (+002) |
| [008](008-list-delete.md) | `/list` + `/delete` | AFK | 005 |
| [009](009-hardening-timeout-gc-quota.md) | Timeout, tmp GC, quota UX | AFK | 004 (+002/003; ideally after 005–007) |
| [010](010-manual-smoke-checklist.md) | Manual smoke checklist | HITL | 001–009 |

## Parallelism

```
001 ─┬─► 002 ─┐
     └─► 003 ─┴─► 004 ─► 005 ─┬─► 006
                              ├─► 007
                              └─► 008
              004+… ─► 009
              001..009 ─► 010
```

After **001**, run **002** and **003** in parallel. After **005**, run **006**, **007**, **008** in parallel.

## Publish to GitHub (later)

```bash
# from repo root, after git remote exists
gh issue create --title "001 — Bot bootstrap: config, owner gate, /start /help" --body-file docs/issues/001-bot-bootstrap-access-help.md
# …repeat; then edit bodies to replace “Blocked by 00x” with real #N numbers
```
