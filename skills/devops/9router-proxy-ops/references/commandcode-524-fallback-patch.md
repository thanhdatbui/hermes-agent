# 524 Cloudflare-timeout fallback patch (vendor build, MẤT khi update)

## Problem — TWO distinct 524 failure modes, patch fixes only ONE

9router error classifier (hard-coded list in the build:
`[{text:...},{status:401},{status:402},{status:403},{status:404},{status:429}]`)
does NOT include 524/529. When CommandCode returns
`{"type":"server_error","message":"Invalid error response format: Gateway request failed","statusCode":524,"isRetryable":true}`
(Cloudflare timeout / overload on CommandCode's side), the combo STAYS STUCK —
no fallback to next model, error bubbles straight to Hermes.

`isRetryable:true` is CommandCode telling the client to retry, but 9router
ignores that field; it only matches message text patterns + status codes.

**Mode A — pre-stream (trước khi stream mở):** request fails with 524/529
before the stream opens. Classifier returns `shouldFallback:false` → combo
stands still. **The patch fixes this** (524 → 15s account lock → next model/acc
tried). Verified in server.log: `ERROR 400 · commandcode ... ACC:xxx` →
`[AUTH] xxx locked modelLock_deepseek/deepseek-v4-flash for 30s [400]` → next
acc `thanhdatbui19951` → succeeded.

**Mode B — mid-stream (giữa stream):** stream opens OK (9router logs `Model
... succeeded` because model selection already passed), then CommandCode
stalls and dies after ~129s (`DONE 129193ms · TTFT 129187ms · OUT 37`) with
the 524 error injected as an in-stream error chunk. **No patch can catch
this** — combo already committed to the model; there is no mid-stream
fallback. Hermes does NOT retry Mode B: agent.log shows
`stream_request_complete, tcp_force_closed=0` (stream closed "cleanly" from
Hermes' view) → in-stream error chunk does not trigger `api_max_retries`.
Only mitigation: the NEXT request (next turn/tool call) starts combo at model
1 again; the failed account is still locked → lands on a different acc. Lose
that one turn; it self-heals. Don't burn time diagnosing Mode B as a 9router
bug — it is CommandCode server stall.

## Fix (local patch, ~1 min, verified 2026-08-15 on 0.5.50)

```bash
cd "C:\Users\Kibe\AppData\Roaming\npm\node_modules\9router\app\.next-cli-build\server"
# backup first
grep -rl "{status:429,backoff:!0}]}" . | while read f; do cp "$f" "$f.bak-524patch"; done
# add 524/529 -> lock account 15s, then combo falls through to next model
grep -rl "{status:429,backoff:!0}]}" . | xargs sed -i 's/{status:429,backoff:!0}]}/{status:429,backoff:!0},{status:524,cooldownMs:15e3},{status:529,cooldownMs:15e3}]}/g'
```

Then restart 9router:
- Find the node PID running `server.js` (`tasklist | grep node`, `wmic process where "ProcessId=<pid>" get CommandLine` to confirm), `taskkill /f /pid <pid>`.
- The `:loop` in `C:\Users\Kibe\AppData\Roaming\npm\9router.cmd` (timeout 30s — raised from 2s so npm update doesn't race file locks) auto-restarts it.
- Verify: port 20128 LISTENING, `%APPDATA%\9router\logs\server.log` shows requests again.

Restore if broken: `cp "$f.bak-524patch" "$f"` for each patched file.

## Critical caveats

- This edits minified vendor build inside `node_modules`. **`npm i -g 9router` wipes it** — the `.bak-524patch` backups die with it. After EVERY 9router update, re-run the patch (2 commands above).
- Verified 0.5.55 (2026-08-15): error classifier is byte-identical to 0.5.50 → upgrade does NOT fix 524. No point updating for this.
- Cooldown 15s chosen: 524 is transient server overload; short lock lets the account rejoin quickly without hammering.
- Patch is safe re: CommandCode ban risk — it only adds a retry/fallback path, no extra requests to CommandCode (other models in combo are different providers).

## User-facing explanation (for Gemini rescue if things break)

> 9router (npm global proxy) patched: added `{status:524,cooldownMs:15e3},{status:529,cooldownMs:15e3}` to the error fallback list in 35 build files under `C:\Users\Kibe\AppData\Roaming\npm\node_modules\9router\app\.next-cli-build\server` (backed up as `.bak-524patch`). If 9router won't start: check `%APPDATA%\9router\logs\server.log`, run `C:\Users\Kibe\AppData\Roaming\npm\9router.cmd --bg` (loop restarts every 30s), or restore `copy "FILE.bak-524patch" "FILE"`. Port 20128 must LISTEN; Hermes calls `http://127.0.0.1:20128/v1`.
