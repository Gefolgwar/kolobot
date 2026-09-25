# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

---

## Project Context: kolobot

- **Description**: Asynchronous Telegram bot (`aiogram` v3) serving as a smart personal document archive with OCR, vector search (RAG), and Gemini API Key Pool Manager.
- **Tech Stack**: Python 3.9+, `aiogram` v3, `google-genai`, `chromadb`.
- **Models**: `gemini-2.5-flash` (Text & Vision), `text-embedding-004` (Embeddings).
- **Core Architecture**:
  - `AsyncGeminiPool`: API key rotator with sliding window rate limiting (RPM/RPD) and automatic 60s cooldown on HTTP 429.
  - `VectorStoreManager`: ChromaDB wrapper managing vector embeddings, `user_id` isolation, and `telegram_file_id` metadata.
  - **Handlers**: FSM-based file ingestion (OCR & save to `./downloads`) and natural language RAG querying with inline file download buttons.

---

## Development Principles

### 1. Think Before Coding

Don't assume. Don't hide confusion. Surface tradeoffs.

**Before implementing:**

- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

---

### 2. Simplicity First

Minimum code that solves the problem. Nothing speculative.

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.
- **Ask yourself:** _"Would a senior engineer say this is overcomplicated?"_ If yes, simplify.

---

### 3. Surgical Changes

Touch only what you must. Clean up only your own mess.

**When editing existing code:**

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it.

**When your changes create orphans:**

- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

> **The test:** Every changed line should trace directly to the user's request.

---

### 4. Goal-Driven Execution

Define success criteria. Loop until verified.

**Transform tasks into verifiable goals:**

- `"Add validation"` → `"Write tests for invalid inputs, then make them pass"`
- `"Fix the bug"` → `"Write a test that reproduces it, then make it pass"`
- `"Refactor X"` → `"Ensure tests pass before and after"`

For multi-step tasks, state a brief plan before executing.

---

### 5. Agent & Subagent Usage
- Treat agent files in `.claude/agents` strictly as reference files / context when needed.
- Spawning, launching, or orchestrating subagents is permitted **ONLY** via the `/herdr` skill. Direct or unmanaged spawning of subagents outside of `/herdr` is strictly prohibited.
- Execute all tasks within the single active session unless delegated via `/herdr`.
- If the user includes an agent's instructions or mentions an agent (e.g., `@fullstack-developer (agent)`) in the prompt outside `/herdr`, adopt those instructions and execute the task yourself in the current session.
- The user alone will decide if, when, and how to open an additional session and what to do in it.
- When a skill instructs to "look up" or "explore" facts — use Read/Glob/Grep directly. This does NOT override the subagent restriction above.

---

### 6. Communication & Addressing
- Always address the user by the name Gefolgwar.
- **EVERY response MUST start with the name Gefolgwar.**

---

### 7. MCP Servers & Tool Requests
- MCP servers are kept disabled by default to minimize context token usage.
- Do not assume, guess, or hallucinate external data if an MCP tool is not available.
- If a task genuinely requires an MCP server/tool (or if enabling one would significantly improve precision, efficiency, or safety):
  - **Do NOT proceed with assumptions.**
  - **Explicitly notify Gefolgwar and wait for a decision.**
  - Clearly specify:
    1. Which MCP server/tool is needed.
    2. Why it is necessary and what value it adds to this specific task.
    3. What the alternative or fallback approach is if it stays disabled.
- Only proceed after Gefolgwar confirms, enables the tool, or chooses an alternative route.
