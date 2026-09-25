---
name: implement-herdr
description: "Herdr Orchestrator: distributes sub-issues across agents with full issue lifecycle management."
disable-model-invocation: true
---

# implement-herdr

Orchestration of sub-issues from a parent GitHub Issue across existing Herdr agents.
Argument: `<parent-issue-number>` (prompt user if not provided).

## Critical Execution Rules

- **Herdr-only**: `test "${HERDR_ENV:-}" = 1` must pass — stop immediately otherwise.
- **Existing panes only**: Target `pane_id`s from `herdr agent list` (agents may share names — always use `pane_id`). Never create splits, tabs, or agents.
- **Windows / MSYS**: Send commands **exclusively via Bash**, prefixed with `MSYS_NO_PATHCONV=1`, task text in **single quotes `'...'`**.
- **No `--wait`**: Never pass `--wait` to prompt commands — it blocks parallel delegation.
- **Pauses**: Use PowerShell `Start-Sleep -Seconds <N>` (Bash `sleep` is blocked).

---

## Execution Workflow

### 1. Preparation
1. Verify environment: `test "${HERDR_ENV:-}" = 1`.
2. Retrieve open sub-issues from parent issue `#<ID>` (via GitHub MCP or `gh`). Filter out closed issues and those labelled `in-progress`.

**Done when:** every eligible sub-issue has `<NUMBER>`, `<TITLE>`, `<BODY>` collected.

### 2. Delegation (loop per sub-issue)
1. Pick an available agent (`idle` or `done` in `herdr agent list`). `blocked` → read its buffer (`herdr agent read <pane_id> --lines 20`) and notify Gefolgwar. All busy → `Start-Sleep -Seconds 10`, retry.
2. Reset context:
   ```bash
   MSYS_NO_PATHCONV=1 herdr agent prompt <pane_id> "/reset"
   ```
   `Start-Sleep -Seconds 2`
3. Dispatch:
   ```bash
   MSYS_NO_PATHCONV=1 herdr agent prompt <pane_id> '/implement Implement issue #<NUMBER>: <TITLE>.

   Requirements:
   1. Mark the issue as in progress (add label "in-progress").
   2. Complete the assigned task according to the description below:
   <BODY>
   3. Verify functionality (run tests and build checks).
   4. Once finished: commit changes, post a summary report in the issue comments, remove label "in-progress", and close the issue.'
   ```
   `Start-Sleep -Seconds 3`

**Done when:** `herdr agent list` shows agent `working`. If still `idle` after ~10 s, read its buffer — do not resend blindly.

### 3. Monitoring & Coordination
1. Poll `herdr agent list` + `Start-Sleep -Seconds 15` until every assigned agent reaches `idle` or `done`.
2. If an agent asks a question, reply to its pane without `/reset`. If the question exceeds issue scope (design change, cross-ticket impact), escalate to Gefolgwar first.

### 4. Verification

`done` / `idle` means the agent's turn ended — **not** that the work is complete. The agent may **stall** after analysis without a single edit. For every agent, check facts:
- New commit? `git log --oneline -1` (compare to pre-delegation HEAD).
- Issue closed with summary comment? `gh issue view <N> --repo Gefolgwar/ExamDE --comments`.

**If both confirmed** → issue is done.

#### First stall
Prompt the **same** agent — keep its context, do not `/reset` or re-delegate:
```bash
MSYS_NO_PATHCONV=1 herdr agent prompt <pane_id> 'You stopped without committing. Do NOT write analysis — immediately make the required changes, commit, post the report in the issue, and close it.'
```
`Start-Sleep -Seconds 8`, then confirm `working` via `agent list` and file edits (not analysis) via `agent read`.

#### Second consecutive stall — narrow, do not repeat
A full re-prompt burns context on exploration → auto-compaction → another empty stall. Send `/clear`, pause, then a **narrow** prompt:
```bash
MSYS_NO_PATHCONV=1 herdr agent prompt <pane_id> "/clear"
```
`Start-Sleep -Seconds 3`

Narrow prompt recipe:
- Numbered edits (5–7 items) with exact file paths — no spec recap.
- File-count cap and explicit list of files **not** to touch (belong to other tickets).
- "`git add` only your perimeter files — not `CLAUDE.md` or `.claude/skills/`."
- End with: "Start editing files NOW."

**Done when:** every delegated issue has a confirmed commit and is closed with a summary comment.

### 5. Close Parent Issue
Once all sub-issues are verified closed, post a summary comment on the parent issue (`#<ID>`) listing each sub-issue with its commit hash, then close it:
```bash
gh issue comment <ID> --repo Gefolgwar/ExamDE --body '<SUMMARY>'
gh issue close <ID> --repo Gefolgwar/ExamDE
```

### 6. Final Report

| Issue # | Pane ID | Issue Status | Commit Hash |
| :--- | :--- | :--- | :--- |
| #\<NUMBER\> | \<PANE_ID\> | Closed / Open | \<HASH\> |