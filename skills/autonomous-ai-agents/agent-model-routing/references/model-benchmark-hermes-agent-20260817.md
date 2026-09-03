# Model Benchmark in Hermes Agent — DS Command Code vs Gemini 3.7 Flash (2026-08-17)

## Context
User asked to benchmark DeepSeek V4 Flash vs Gemini 3.7 Flash on real Android-automation tasks (build/fix scripts in `D:\Taadaa` repos), to decide the worker model inside Hermes ("t chỉ xài hermes để làm việc").

## Methodology that worked (fair A/B in Hermes)
- Both models run INSIDE the Hermes agent, not raw API:
  `hermes chat -q <prompt> -m <model> --provider 9router -Q --max-turns 8` (cwd = repo root).
- Same prompt, same default toolset (read_file/grep/bash available), same `--max-turns` cap.
- Interleave model order per task; `sleep 60` between calls (AG burst lock).
- Score output independently: correctness, depth (did it read real files / run live tests / trace callers / challenge a false premise), stability, speed.
- Tasks (all from real repos, model may read the actual file): T6 canonical_header bug fix; T7 FollowState budget rollover (timezone); T8 device_lock fail-closed review; T11 safety_check review; T12 VPN proxy-mapping source-error classification.

## Route IDs verified 17/08 (9router :20128)
| Route | Status |
|---|---|
| `ag/gemini-3.7-flash-high` | OK, stable, 10–130s |
| `commandcode/deepseek/deepseek-v4-flash` | OK after user added provider `commandcode` (lequynh27032002, active). NOT `commandcode-direct/...` (that's the OpenCode CLI provider name — no creds in 9router), NOT `cc/...` |
| `deepseek-v4-flash` (combo name) | Works but emits `reasoning_content` that can squeeze `content` empty unless max_tokens ≥ 20000; resolves to oc free tier (slow/502) |
| `oc/deepseek-v4-flash-free` | Frequent HTTP 502, up to 213s+ per call, timeouts on long contexts — infrastructure unreliable |
| `v98/deepseek-v4-flash` | 503 `service_migrated` (v98store → cheapkeyai.shop). Dead |
| `opencode-go/deepseek-v4-flash`, `commandcode-direct/deepseek/deepseek-v4-flash` | "No active credentials" |
| `cmc/deepseek/deepseek-v4-flash` (bare, non-combo) | 404 via /v1/chat/completions |

## Critical quirks
1. **Command Code DS via plain chat API emits XML tool-calls** (`<read_file path="..."/>`) inside `content` with `finish_reason=stop` — no OpenAI `tool_calls`. Raw-API benchmarks are meaningless for it, and "cấm dùng tool" prompts cripple it. It works properly only inside a tool-executing runtime (Hermes agent, CLI).
2. **Reasoning models (combo deepseek)**: `content` can be `""` while `reasoning_content` holds 20K+ chars; set max_tokens ≥ 20000 and read BOTH fields.
3. **AG Gemini burst lock**: ~10 sequential Gemini calls → HTTP 429 "Resource has been exhausted" for ~5 min even though the quota dashboard shows 99–100% free. Space calls 60s apart; a single call always OK.
4. **Hermes agent runaway**: without `--max-turns`, the agent loop can emit 160K+ chars (tool output dumped into response). Always pass `--max-turns 8`.
5. **AG identity denylist is GONE**: original identity "You are Hermes Agent, a helpful and direct AI assistant..." returns 200 (was 429 earlier on 17/08). Ground truth = `http://localhost:20128/dashboard/quota`, not error codes.

## Results (worker-role evidence)
| Metric | DS Command Code | Gemini 3.7 Flash |
|---|---|---|
| Correctness/depth | 9.5 — reads real files, runs live tests, traces callers (e.g. `calibrate_screens.py:1306`), CHALLENGES false bug premise (T7: timezone bug didn't exist; real reset source was `_load()` returning `{}` + 17/08 spec removing the daily cap) | 8 — correct per premise, more passive, less reality-verification |
| Stability | 4/5 — one HTTP 500 server error (T6) | 5/5 |
| Speed | ~264s avg (218–304) | ~71s avg (25–126) |
| Behavior | active worker (git status, run live tests, multi-file) | answers from 1–2 files |

## Routing conclusion (PENDING user approval to change combo)
- **Gemini 3.7 Flash = default worker** (fast, stable, good enough for routine build/fix).
- **DS Command Code = hard tasks** (ambiguous bug, multi-file, recovery, audit) — accept slowness + retry on 500.
- User frustration signal: "ds sửa mãi lỗi đéo xong → chuyển qua gemini" — repeated same-model retries without escalation frustrates the user; escalate after 1–2 failed cycles.
