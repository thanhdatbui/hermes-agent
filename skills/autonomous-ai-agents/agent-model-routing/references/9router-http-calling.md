# 9router HTTP calling recipes (D:\Taadaa, endpoint http://127.0.0.1:20128/v1)

Verified live 2026-08-06; catalog re-verified 2026-08-15 (467 models). All calls: `POST /v1/chat/completions`, header
`Authorization: Bearer $NINEROUTER_API_KEY` (env), `Content-Type: application/json`.

## Verified model reachability (curl smoke, max_tokens=10)

| Model id | Result 2026-08-06 | 2026-08-15 catalog |
|---|---|---|
| `cmc/deepseek/deepseek-v4-flash` | OK (main Hermes model) | ✅ present |
| `cmc/deepseek/deepseek-v4-pro` | OK — returns `reasoning_content` (thinking model) | ✅ present |
| `cmc/deepseek/deepseek-v4-pro-max` | 403 FORBIDDEN (commandcode upstream) | ❌ gone |
| `gemini/gemini-3.6-flash` | OK (vision + audit fallback) | ❌ GONE — use `ag/gemini-3.6-flash-high` / `-low` / `-medium` |
| `gpt-5.6-luna` / `cx/gpt-5.6-luna` | OK after user added GPT upstream (was 401 before) | ✅ `gpt-5.6-luna` (bare) |
| `gpt-5.6-terra` / `cx/gpt-5.6-terra` | OK after GPT added (was 401) | ✅ `gpt-5.6-terra` (bare) |
| `gpt-5.6-sol` / `cx/gpt-5.6-sol` | OK after GPT added (was 401) | ✅ `gpt-5.6-sol` (bare) |
| `cx/gpt-5.6-terra-review` / `cx/gpt-5.6-sol-review` | (older audit route) | ❌ GONE — use bare `gpt-5.6-terra` / `gpt-5.6-sol` |
| `v98/claude-opus-4-8` | OK for tiny prompt; **403 new_api_error on large payloads** | ✅ present (same caveat) |
| `v98/claude-opus-5` | — | ✅ present (Opus 5 — chain khó #2) |
| `v98/claude-sonnet-4-6` | 403 even on small prompt (upstream blocked) | ✅ present (still upstream-limited) |
| `v98/kimi-k2.6` | 429 rate-limited | ✅ present |
| `cmc/moonshotai/Kimi-K2.6` | OK — but `finish_reason=length` on long audits | — |
| `ag/claude-opus-4-6-thinking` | — | ✅ present (AG Opus — chain thường #2) |
| `oc/deepseek-v4-flash-free` | — | NOT top-level — combo member (xem Pitfall 7) |
| `oc/hy3-free` | — | NOT top-level — combo member |

**Combo members are NOT in `/v1/models`** — read the `combos` table in
`~/AppData/Roaming/9router/db/data.sqlite` (`SELECT name,models FROM combos`) to see member lists. 9 combos
2026-08-15: `deepseek-v4-flash` (`cmc/deepseek/deepseek-v4-flash`, `oc/deepseek-v4-flash-free`, `oc/hy3-free`,
`gpt-5.6-luna`, `openrouter/*:free`), `deepseek-v4-pro`, `gpt-5.6-luna`, `gpt-5.6-terra` (terra +
`ag/claude-opus-4-6-thinking` + `cmc/deepseek/deepseek-v4-pro`), `gpt-5.6-sol`, `gemini-3.6-flash-high`,
`claude-sonnet-4-6`, `opencode-audit`, `opencode-free`.

**Re-probe before relying — upstream keys/quota change.**

## Pitfalls from real calls (2026-08-06 + 2026-08-15)

1. **DeepSeek v4-pro can emit fake `<tool_calls>`** when the prompt resembles an
   agent task ("lên kế hoạch" etc.). Content then comes back empty/truncated.
   FIX: send `"tools": [], "tool_choice": "none"` in the payload → it returns
   pure text. If content is still empty, check `message.tool_calls` and salvage
   `function.arguments`.
2. **Large prompts + Claude upstream (v98/claude-*) → 403 new_api_error** even
   when the same model answers a tiny "Reply OK" fine. This is an upstream key
   input-length/quota limit, NOT a payload bug. Don't retry harder; switch model
   (Kimi K2.6 / GPT Sol) or split the prompt.
3. **Kimi K2.6 (`cmc/moonshotai/Kimi-K2.6`) truncates long audits**:
   `finish_reason=length` even at max_tokens=8000. Plan for continuation rounds:
   round 2 asks only for the remaining criteria; round 3 for the final verdict
   with a strict short-answer instruction (`dưới 600 chữ`).
4. **`reasoning_effort` is accepted by deepseek via 9router** (`max`/`high` both
   return 200) — so "flash max" is expressible in-app, no CLI.
5. **Model ids with a `(high)` suffix are display-only** — never send the suffix.
6. **DeepSeek-family 429 `RATE_LIMITED` is upstream-wide, GPT family stays up** (live
   2026-08-07): `cmc/deepseek/deepseek-v4-pro` AND `cmc/deepseek/deepseek-v4-flash`
   BOTH returned `429 RATE_LIMITED (reset after ~50s)` simultaneously, while
   `gpt-5.6-luna` answered 200 the same minute. The reset window is SLIDING —
   every probe/retry within the window pushes it further out (50s → 2m41s after
   2 extra probes). When the 2-model plan/audit consensus needs deepseek but it
   is 429'd: **switch the audit to the GPT family (luna/terra/sol via bare or
   `cx/` prefix) instead of hammering retries**; if deepseek is genuinely needed,
   wait the FULL reported reset with ZERO probes (a background `sleep N && call`
   job is the right pattern), then call once. Probe messages do not consume the
   quota but DO extend the reset — probing a rate-limited family is actively
   counterproductive.
7. **Combo member resolution** (2026-08-15): a model like `oc/deepseek-v4-flash-free`
   or `oc/hy3-free` that the user references may not appear in `/v1/models` at all —
   it is a member of a `combos` row. Query the combos table before concluding
   "model doesn't exist"; when the client supports combo routing, call via the
   combo name rather than the bare member id.

## Minimal verified recipe (plan/audit from Hermes)

```python
import json, os, urllib.request
key = os.environ["NINEROUTER_API_KEY"]
payload = {
    "model": "gpt-5.6-terra",   # or gpt-5.6-sol / cmc/deepseek/deepseek-v4-pro
    "messages": [{"role": "user", "content": prompt}],
    "max_tokens": 8000,
    "temperature": 0.2,
    "tools": [],            # REQUIRED: stops fake tool_calls on deepseek-pro
    "tool_choice": "none",
}
req = urllib.request.Request(
    "http://127.0.0.1:20128/v1/chat/completions",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json",
             "Authorization": f"Bearer {key}"},
)
with urllib.request.urlopen(req, timeout=900) as resp:
    data = json.loads(resp.read().decode())
content = data["choices"][0]["message"].get("content") or ""
```

## Finalized user chains (2026-08-15 — worker/plan/review)

- Worker fallback (in 9router, NOT Hermes `fallback_providers`):
  `cmc/deepseek/deepseek-v4-flash → gpt-5.6-luna → oc/deepseek-v4-flash-free → oc/hy3-free → ag/gemini-3.6-flash-high`
- Plan/review thường: `gpt-5.6-terra → ag/claude-opus-4-6-thinking → cmc/deepseek/deepseek-v4-pro`
- Plan/review khó: `gpt-5.6-sol → v98/claude-opus-5 → cmc/deepseek/deepseek-v4-pro`

## Full-stack pattern that worked (AGENTS.md split audit, 2026-08-06)

- Planner: `cmc/deepseek/deepseek-v4-pro` with full AGENTS.md in prompt
  (99KB fits; 17.9KB plan returned, `finish=stop`).
- Auditor: `gpt-5.6-sol` with the plan → **REJECT with 6 concrete findings**
  (lossless-integrity proof missing, root size mismeasured, topic files not
  auto-loaded, marker test would fail, setup-codex.ps1 unaddressed, 25-file
  immutability self-contradiction). Sol finishing `stop` with a real verdict —
  the crossover (deepseek plans, GPT audits) catches real bugs.
- Lesson: when auditing a plan, prompt for PASS/WARN/FAIL **per criterion** +
  "problems to fix before implementation" + final APPROVE/APPROVE_WITH_FIXES/
  REJECT. Capture the audit to a file immediately (long outputs).

## Sol audit >300s → run in background (verified 2026-08-06, scope-split v2/v3)

`execute_code` has a 300s cap; GPT-5.6-Sol auditing a 16-29KB policy plan takes
3-6+ minutes (reasoning-heavy). FIX: write the audit call to a `.py` file that
POSTs to 9router (timeout=840) and writes the verdict to a file, then run it
with `terminal(background=true, notify_on_complete=true)` and `process
wait/poll`. Verification = the verdict artifact file, not a test suite. Delete
the throwaway `.py` after it exits. Sol response with `finish=stop` can still
truncate mid-file (tool output cap) — read the full verdict from the saved
file, not the process tail.

## Policy-change plan: 3-round REJECT progression (scope-split, 2026-08-06)

User decision "fallback luna↔flash ngang hàng cho CẢ live" → Sol REJECT ×3:
- **v1 (8 findings)**: rule repeated 3× with different force (may/pinned/permitted)
  → 1 canonical source; classification not fail-closed (no consumer-root
  allowlist, symlink/submodule/shared-path, network/ADB test side effects);
  direct-fallback punching core gates; edit-boundary by line-number drifting +
  swallowing next heading (anchor by unique heading/marker); validator inferred
  from script name (run baseline-before + after, exit 0 release gate).
- **v2 (fallback mâu thuẫn)**: text said live MUST Luna + "no other model may
  substitute" but allowed Flash fallback → rewrite as primary/authorized-
  equivalent pair; `unavailable` must be fail-closed (transport ≠ model);
  canonical-path scope gate; `WORKER_PROFILE_MISMATCH` primary/effective pin;
  3 fallback layers distinct; validator baseline exit 0.
- **v3 (6 findings)**: live-STOP must be per-layer (transport/policy/safety
  block independently, no model swap); `unavailable` taxonomy conflated
  transport-unavailable with model-unavailable; effective pin unproven
  (record dispatch_generation_id, failed pin, transport, error source;
  verifier checks transition authorization); dispatch-generation lifecycle
  (no new generation to dodge 1-fallback cap); Model Routing still restated
  contract; validator semantic compare undefined.
- **Root-cause insight**: the user's equivalent-fallback-for-live decision IS
  the recurring REJECT trigger — a strong auditor protects fallback abuse
  hardest. After 3 REJECTs, propose simplification (live = Luna ONLY) instead
  of round 4. Details in `hermes-orchestration-dispatcher` SKILL.md →
  "AGENTS.md scope-split v3".
