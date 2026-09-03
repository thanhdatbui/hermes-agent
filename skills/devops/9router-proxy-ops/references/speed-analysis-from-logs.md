# Speed analysis from real logs (9router / Hermes)

Session 2026-08-14: user asked to compare speed of `deepseek-v4-flash` (via cmc/commandcode)
vs `gpt-5.6-luna`, then corrected me twice: (1) my synthetic curl probe with a made-up
prompt wasn't what they wanted — "prompt m test chuẩn chưa, sao k test ở session t sử
dụng"; (2) "t bảo đo ở log session cũ mà" — they wanted numbers from the OLD session
log, i.e. before the combo was changed ~10:00 that morning. Rule: **speed claims must be
backed by real session logs, not ad-hoc probes.**

## Combo history — how to find the OLD combo
- Current combo: `combos` table in `%APPDATA%\9router\db\data.sqlite` — has `createdAt`,
  `updatedAt`. The change moment = `updatedAt` (UTC): e.g. `2026-08-14T02:45:59.990Z` =
  09:46 VN, matching the user's "10h sáng".
- Old combo (the one that was replaced): read the backup that 9Router writes before combo
  edits: `db/data.sqlite.bak-before-combo-*.sqlite` (e.g.
  `data.sqlite.bak-before-combo-ds-20260813-104248`). This gave the definitive old
  `deepseek-v4-flash` = `["oc/deepseek-v4-flash-free", "cmc/deepseek/deepseek-v4-flash"]`
  (opencode-free FIRST).
- Do NOT trust the current DB or `/v1/models` to describe the old state.

## Data sources (authoritative order)
1. **`usageHistory` table** (NOT truncated): `timestamp, provider, model, connectionId,
   apiKey, endpoint, promptTokens, completionTokens, cost, status, tokens, meta`.
   - `provider` = actual upstream route: `commandcode` (= cmc), `opencode` (= oc free),
     `codex` (= luna/sol/terra cx). This is the ONLY per-request route truth that survives.
   - Verified: 14/08 OLD window = 168 commandcode + 101 opencode calls; NEW window = 968
     commandcode, ZERO opencode → combo change completely removed the oc route.
2. **agent.log** `agent.conversation_loop: API call #N: model=... in=... out=... latency=...`:
   real latency per call, but `model=` is the COMBO name (`deepseek-v4-flash`) — you
   cannot tell which member answered from this alone.
3. **`requestDetails` table** — DO NOT use for old windows: keeps only ~1000 most-recent
   rows (verified: 0 rows before 02:45Z even though traffic existed). OK for last-hour
   triage only.

## Join recipe (agent.log latency ↔ usageHistory route)
- Parse agent.log lines: `latency=([0-9.]+)s`, `in=`, `out=`, timestamp.
- Parse usageHistory rows into sorted list of `(datetime, route)` where route =
  `"oc" if "opencode" in provider else "cmc"`.
- For each agent.log call, `bisect` the usage list and take the nearest row within ±600s;
  assign its route. (usageHistory timestamp is when the request *finished*, agent.log
  latency is when Hermes got the response — small skew is fine at ±600s.)
- Sample: matched 20 oc / 180 cmc from 2815 calls (rest unmatched because OLD calls fall
  outside the usage window or >10 min gap). Small n for oc is expected — don't over-read.

## The ~250-280s fixed-latency trap (retry, NOT slow model)
OLD oc-first numbers: latency ~257-283s constant for out=73..930 tokens. This is NOT the
model being slow — it's Hermes retrying a failing request:
- errors.log shows `Streaming response failed: [upstream_error] An internal error
  occurred` then `Retrying API call in ... (attempt N/8)` (api_max_retries=8, jittered
  backoff 2-60s).
- Signature: latency ≈ constant regardless of output size; med >> p50 spread; giant max
  (up to 2932s) = stacked retries.
- Correct conclusion: `oc/deepseek-v4-flash-free` FAILS upstream often; each failure
  costs ~4.3 min of retry. "Đi qua opencode free làm chậm đáng kể" → TRUE, but the
  mechanism is fail+retry, not slow generation.

## Results (2026-08-14, deepseek-v4-flash)
| Combo | n | avg | med | core_avg |
|---|---|---|---|---|
| OLD oc-first (before 09:46) | 1876 | 106.7s | 24.7s | 75.3s |
| NEW cmc-first (after 09:46) | 926 | 10.2s | 6.3s | 6.9s |

- Bucket by out tokens (0-300 / 300-1000 / 1000-4000): NEW is 5-15× faster in every
  bucket; OLD avg 88-108s per bucket even for tiny outputs = retry contamination.
- Luna (codex) med ~15s vs cmc med ~6.3s → cmc ~2.4× faster than luna on real traffic.
- Takeaway: putting cmc first in the combo removes the retry source entirely; luna stays
  behind as fallback.

## Pitfalls
- **Timezone**: usageHistory = UTC (`Z`); agent.log = local VN (+7). Filter/join with the
  right domain or you'll get empty/absurd windows.
- **`execute_code` is blocked in cron/background contexts** — write the analysis script to
  a temp file and run via `terminal python`.
- **curl probe timing (`time_starttransfer`/`time_total`) is NOT what the user wants** for
  "speed of my session" — it measures a fresh non-stream request, not their real
  streamed multi-turn workload. Use it only to sanity-check liveness, not to answer
  speed questions.
- Clean up analysis scripts afterwards (user expects a tidy `~/AppData/Local/hermes`).
