# OmniRoute Session Stickiness & Fusion Combos Guide

## 1. Session Account Affinity / Prompt Cache Stickiness

### Mechanism (`open-sse/services/combo/sessionStickiness.ts`)
- **Key Derivation**: SHA-256 hash of the **first user message** in the conversation, namespaced by Combo ID.
- **Behavior**: Pins all subsequent turns of a multi-turn conversation to the same `connectionId` (Google Antigravity / OpenAI account) for 15 minutes (TTL 15m).
- **Benefit**: Ensures Google/Anthropic prompt cache (KV Cache) remains hot across conversational turns, reducing multi-turn latency by 50–70% and preserving context quota.
- **Safety / Fail-open**: If the pinned account encounters:
  - Utilization headroom < 0.15 (`STICKINESS_HEADROOM_THRESHOLD`),
  - Upstream 429 / Rate limit cooldown,
  - Depleted quota / error,
  The sticky pin is automatically released and combo routing fails over to the next healthy account in priority order.

### Enabling on Combos via Live API
Always mutate via `PUT /api/combos/[id]` on `:20129` (never direct raw SQLite to avoid stale in-memory caches):
```json
{
  "name": "ag-gemini-pool-3",
  "config": {
    "maxRetries": 0,
    "disableSessionStickiness": false,
    "disablePromptCacheAffinity": false,
    "failoverBeforeRetry": true
  }
}
```

---

## 2. Fusion Strategy Architecture (`open-sse/services/fusion.ts`)

### Concept & Flow
1. **Parallel Fan-out (Panel)**: Dispatches the user prompt simultaneously to $N$ panel models without streaming.
2. **Quorum & Grace Period**:
   - `minPanel`: Quorum size (default 2). Once $N \ge minPanel$ models finish, starts `stragglerGraceMs` (default 8s) for remaining models.
   - `panelHardTimeoutMs`: Hard timeout cap (default 90s).
3. **Anonymized Judge Synthesis**:
   - Collects panel outputs formatted as `[Source 1]`, `[Source 2]`, ...
   - Passes to `judgeModel` with full conversation history and an internal consensus/contradiction/blind-spot analysis directive.
   - The judge produces a single, synthesized, authoritative answer directly to the user.
4. **Tool-bearing Bypass (#6771)**:
   - If `tools` are present and `tool_choice !== "none"`, panel synthesis is bypassed and the request routes directly to the single `judgeModel` with full tool parameters intact.

### Plan-Review Hard Fusion Setup (Sol + Opus)
- **Panel**: `["cx/gpt-5.6-sol", "ag/claude-opus-4-6-thinking"]`
- **Judge**: `cx/gpt-5.6-sol` (or `ag/claude-opus-4-6-thinking`)
- **Advantage**: Combines OpenAI's strict type/contract checking with Anthropic's multi-step side-effect and architectural reasoning, eliminating blind spots in code review.

---

## 3. Automation Token Compression Caution (RTK)
- **Code & General Text**: RTK compression safely strips ANSI codes and redundant whitespace.
- **Android / Farm Automation (`atx-agent` / UI XML)**: High compression can mutate or truncate detailed XML attributes (`resource-id`, `bounds`, node index). Keep RTK disabled or at minimal level for automation workloads to prevent coordinate distortion.
