# Free-Tier Model & Combo Timeout (499) Diagnosis

## 1. Dual 499 (Router Combo + Downstream Model) Pattern
When reading 9Router / OmniRoute logs (UI or SQLite `call_logs` table), seeing both a combo row (e.g. `omni-free`) and an individual model row (e.g. `nemotron-3.5-lightning-free`) marked orange/red with status **499 (Request aborted)** means:
- **Upstream Congestion / Hanging**: The upstream model did not respond within the client/gateway timeout threshold (typically 300s / 5 minutes).
- The router layer aborted the request at ~300.0s, and the upstream connection was terminated at ~296s-299s.
- `TI: 0 TO: 0` indicates zero tokens were streamed/generated before termination.
- **Do not misinterpret** the inner log line as a successful fallback; if both show 499, both timed out.

## 2. Inspecting Live Free Tier Health via SQLite & API
- **SQLite DB location**: `C:\Users\Kibe\.omniroute\storage.sqlite`
- **Call logs query**:
  ```sql
  SELECT timestamp, model, requested_model, provider, status, duration, error_summary, combo_name 
  FROM call_logs 
  WHERE combo_name='omni-free' OR provider='opencode' 
  ORDER BY timestamp DESC LIMIT 20;
  ```
- **Active Testing via Port 20129 (`http://127.0.0.1:20129/v1/chat/completions`)**:
  - `POST` JSON `{"model": "<target_model>", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5, "stream": false}`.
  - Test raw endpoints directly to separate upstream timeouts from router combo priority locks.
  - Note: models returning only reasoning fields (`reasoning` or `reasoning_content`) may return `content: null` in non-streaming mode if `max_tokens` is too small to complete thinking.

## 3. Known Upstream Delistings & Quirk States
- Delisted / Dead (401 / 400): `hy3-free` (401 Model not supported), `deepseek-v4-flash-free` (400 Upstream failed), `north-mini-code-free` (401 delisted).
- Congested / High-latency (often hits 250s-300s): `nemotron-3.5-lightning-free`.
- Fast / Stable alternatives in `omni-free`: `muse-spark-1.2-contributor-free`, `mimo-v2.5-free`, `big-pickle`.
