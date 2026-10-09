# OmniRoute Combo Reviewer Topology & Process Reboot Recovery

## 1. Background & The Critical Coordinator Trap

During Closeout Gate execution, a coordinator might encounter an error like:
```text
[OmniRouteClient] Attempt 1/3 failed: HTTPConnectionPool(host='192.168.110.123', port=20129): 
Max retries exceeded with url: /v1/chat/completions 
(Caused by NewConnectionError("... [WinError 10061] No connection could be made because the target machine actively refused it"))
```

### The Fatal Misdiagnosis
Coordinators often falsely diagnose this as:
- *"Reviewer model bị chết / Sol bị sập nên không chấm điểm được."*
- *"Hết quota Sol nên closeout gate không chạy được."*

**This misdiagnosis is 100% FALSE.**
User explicitly corrected (07/10/2026):
> *"Ủa khi chạy chốt phiên là gọi combo model review chứ, sol có chết thì vẫn có fallback qua claude opus 4.6 chấm mà, combo trên omniroute? Chứ sao chết đc"*

---

## 2. OmniRoute Combo Reviewer Architecture

In OmniRoute (`http://127.0.0.1:20129/v1`), the model specified in `closeout_gate.py` (`model: "review"`) is NOT a single model. It is an **active Priority Fallback Combo** configured in `~/.omniroute/storage.sqlite`:

```text
[Incoming Review Request (model="review")]
                    │
                    ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ [Tier 0] ChatGPT Web Pool (12 Live Accounts)                │
  │ Model: GPT-5.6 Sol High (Primary Reviewer)                  │
  └──────────────────────────────┬──────────────────────────────┘
                                 │ Failover on 429/timeout/error
                                 ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ [Tier 1] Codex Farm Pool                                    │
  │ Model: codex/gpt-5.6-terra-high (Reasoning Reviewer)        │
  └──────────────────────────────┬──────────────────────────────┘
                                 │ Failover on 429/timeout/error
                                 ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ [Tier 2] ag-opus-pool (78 Google Gemini / AGY Accounts)     │
  │ Model: Claude Opus 4.6 Thinking (Antigravity Pool)          │
  └──────────────────────────────┬──────────────────────────────┘
                                 │ Failover on 429/timeout/error
                                 ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ [Tier 3+] OpenCode / OpenRouter Nemotron 3.5 & Muse Spark   │
  │ Model: Free High-Capacity Fallbacks                         │
  └─────────────────────────────────────────────────────────────┘
```

Because of this multi-tier combo:
1. **Model failure NEVER kills the review gate:** If Sol Web accounts are rate-limited, OmniRoute transparently fails over to Codex Terra, then to Claude Opus 4.6 (`ag-opus-pool`), then to Nemotron.
2. The user has 78 AGY accounts backing Claude Opus 4.6 Thinking in Tier 2. The review combo is effectively bulletproof against upstream quota issues.

---

## 3. Root Cause of Connection Refused (`WinError 10061`)

When `closeout_gate.py` throws `[WinError 10061]`, it is **NEVER a model failure**. It is a **Transient Process Reboot** at the network layer.

### The Two Mechanics:
1. **OmniRoute Watchdog Restart (`node.exe`):**
   - The OmniRoute process (PID running on port `:20129`) periodically reboots for garbage collection, memory cleanup, or watchdog maintenance.
   - A reboot takes **10 to 15 seconds**.
   - During those 10–15 seconds, port `:20129` is temporarily closed.
2. **`closeout_gate.py` Candidate Probing Flaw on Windows:**
   - In `resolve_omni_url()`:
     ```python
     candidates = [
         "http://localhost:20129/v1/chat/completions",
         "http://127.0.0.1:20129/v1/chat/completions",
         "http://192.168.110.123:20129/v1/chat/completions",
     ]
     ```
   - On Windows, `localhost` often resolves to IPv6 `[::1]`, which OmniRoute does not listen on, or probes with a very short `timeout=1.0s`.
   - If `:20129` is rebooting or queueing, all three candidates time out in 1s.
   - The function falls through to the hardcoded ultimate return:
     `return "http://192.168.110.123:20129/v1/chat/completions"`
   - But OmniRoute binds to loopback (`127.0.0.1` or `0.0.0.0`), and requests routed through LAN interfaces can be rejected by Windows firewall/socket policies, resulting in immediate `[WinError 10061]`.

---

## 4. Operational Recovery Playbook for Coordinator

When running Closeout Gate (`closeout_gate.py`):

### Rule 1: Always specify `--base-url` explicitly
Never rely on candidate auto-probing falling back to LAN IP:
```bash
python D:/Taadaa/tools/closeout_gate.py \
  --repo <repo_path> \
  --base HEAD~1 \
  --base-url http://127.0.0.1:20129/v1/chat/completions \
  --json-output
```

### Rule 2: Treat `WinError 10061` as TRANSIENT (Reboot State)
If `closeout_gate.py` fails with connection refused on port 20129:
- **DO NOT** tell the user "Sol chết" or "Reviewer offline".
- **DO NOT** surrender or declare L3 BLOCKED.
- Check if OmniRoute is rebooting: `curl -s http://127.0.0.1:20129/api/health`
- Wait 10 seconds for `node.exe` to finish initialization.
- Re-run the gate. It will connect and review immediately.

### Rule 3: AGY (Antigravity) is Already in the Loop
If the user asks whether Antigravity (AGY) can be used as a fallback, reassure them:
- `ag-opus-pool` (Claude Opus 4.6 Thinking qua 78 Antigravity/Gemini accounts) is **already configured at Tier 2** inside the `review` combo.
- Any time Sol is slow or rate-limited, OmniRoute routes directly to AGY without needing any code changes.
