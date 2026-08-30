# 002 — Dual KeyPool + `/status` (+ unit tests)

**Type:** AFK  
**Status:** Open  
**Parent:** [docs/PRD-phase1.md](../PRD-phase1.md)

## What to build

Implement the deep **KeyPool** module for two logical pools loaded from `.env`: `GEMINI_KEYS_GENERATE` and `GEMINI_KEYS_EMBED` (comma-separated). Each pool supports round-robin selection, in-memory sliding-window RPM/RPD, per-key cooldown on 429, and `asyncio.Lock`-safe acquisition. The same physical API key string **may** appear in both pools with **separate** trackers per `(key, pool_kind)`. Expose owner-only `/status` showing available vs cooldown counts per pool (never raw key material), plus basic readiness fields already available (e.g. config paths present). Ship **pytest** coverage for pool behavior with deterministic time.

This slice does not require live Gemini calls; acquisition/release/cooldown can be exercised via unit tests and a status command wired to real pool instances.

## Acceptance criteria

- [ ] `GEMINI_KEYS_GENERATE` and `GEMINI_KEYS_EMBED` load from `.env`; empty required lists fail fast
- [ ] Key overlap across pools is allowed; limits/cooldowns are independent per `(key, pool)`
- [ ] Sliding RPM (default 15) and RPD (default 1500) configurable; round-robin among currently free keys
- [ ] On simulated/recorded 429 path, key enters ~60s cooldown and is skipped until expiry
- [ ] Concurrent acquirers do not hand out the same slot unsafely (lock-covered selection)
- [ ] Exhaustion surfaces a clear error/result for callers (wait-then-sorry UX can be polished in 009)
- [ ] Owner `/status` shows generate/embed availability counts and does not print secrets
- [ ] Non-owner cannot use `/status` (gate from 001)
- [ ] pytest covers: RR, RPM block, RPD block, cooldown, exhaustion, concurrent acquisition

## Blocked by

- Blocked by **001** (config, owner gate, command surface)

## User stories

5, 47–53, 58 (KeyPool)
