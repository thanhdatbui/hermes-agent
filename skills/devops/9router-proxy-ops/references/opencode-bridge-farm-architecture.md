# OpenCode CLI HTTP Bridge & Farm Proxy Rotation Architecture

## 1. Context & Problem Statement
* OpenCode Zen upstream enforces strict protection on its Free Tier endpoints (`https://opencode.ai/zen/v1`):
  Direct external HTTP requests (e.g. from standard OpenAI clients, 9Router, or OmniRoute) trigger:
  `HTTP 403: {"type":"FreeTierError","message":"OpenCode's free tier can only be used from within OpenCode"}`
* To use OpenCode Free models (`muse-spark-1.3`, `nemotron-3-ultra`, etc.) as an autonomous fallback in Hermes without paying API fees, requests must be executed through the local OpenCode binary (`opencode run` CLI $\ge 1.18.0$) while rotating egress IPs across the 69 Farm Proxies to prevent HTTP 429 and daily quota blocks.

---

## 2. System Architecture

```
[Hermes Gateway / Telegram Bot]
             │
             │ (HTTP POST /v1/chat/completions)
             ▼
[opencode_bridge.py (:20130)]  <── ThreadingHTTPServer (Immediate SSE Heartbeat)
             │
             │ (Subprocess: python D:/Taadaa/tools/oc_farm.py run --format json)
             ▼
[oc_farm.py]  <── 69 Farm Proxies (35 MikroTik, 32 Mobi, 2 Khoalee) + Cooldown Cache
             │
             │ (HTTPS_PROXY=http://user:pass@proxy:port opencode run ...)
             ▼
[OpenCode Zen Upstream]
```

---

## 3. Critical Failure Modes & Fixes

### Pitfall 1: Single-Threaded HTTP Blocking & Client Timeout (15s)
* **Symptom:** In long conversations (400+ messages / ~200k tokens), Hermes gateway logs:
  `API call failed: APIConnectionError [HTTP connection error / timeout]`
  and fails over to subsequent fallbacks or errors out.
* **Root Cause:**
  1. Default Python `HTTPServer` is single-threaded; concurrent requests from multiple Telegram topics or health probes block each other.
  2. Hermes client sets a default `connect_timeout = 15.0s`.
  3. When routing through proxy farm + spinning up `opencode run`, the upstream model may take 18–25s to output the first character.
  4. If the HTTP server waits until `oc_farm.py` returns before writing HTTP headers, Hermes hits connection timeout at 15.0s and forcibly drops the connection.
* **Solution (ThreadingHTTPServer + Immediate SSE Flush):**
  * Use `socketserver.ThreadingMixIn` with `HTTPServer` (`daemon_threads = True`).
  * In streaming mode (`stream: True`), **immediately send HTTP 200 headers and an initial assistant role chunk (`{"delta": {"role": "assistant"}}`) within 10ms**.
  * This satisfies Hermes' connection handshake instantly; subsequent data chunks stream freely as `oc_farm.py` produces them.

### Pitfall 2: Model Picker Bloat vs Genuine Free Tier
* **Symptom:** Running `opencode models` returns 108+ models (including paid `opencode-go/*`, `freemodel/*`, etc.), flooding Hermes `/model` menu and confusing routing.
* **Rule:** Filter dynamically to ONLY genuine 100% Free models under the `opencode/*` namespace:
  - `opencode/muse-spark-1.3-contributor-free` $\to$ alias `muse-spark-1.3`
  - `opencode/nemotron-3-ultra-free` $\to$ alias `nemotron-3-ultra`
  - `opencode/nemotron-3.5-lightning-free` $\to$ alias `nemotron-3.5-lightning`
  - `opencode/mimo-v2.6-flash-free` $\to$ alias `mimo-v2.6-flash`
  - `opencode/big-pickle` $\to$ alias `big-pickle`
  - `opencode/space-bunny-free` $\to$ alias `space-bunny`
  - `opencode/ling-3.0-flash-fin-free` $\to$ alias `ling-3.0-flash-fin`
  - `opencode/longcat-2.5-preview-free` $\to$ alias `longcat-2.5-preview`

### Pitfall 3: Prompt Contamination in Non-Project Workspaces
* **Symptom:** Passing full conversation history or raw markdown headers (`[User]`, `[System]`) to `opencode run` in Windows user home (`C:\Users\Kibe`) causes OpenCode CLI to interpret the prompt as an empty instruction or trigger directory file tree inspection (`reading ~1597 entries`).
* **Fix:**
  * Extract only the latest relevant user query string for `opencode run`.
  * Strip empty arguments and pass clean text without confusing pseudo-code prefixes.

---

## 4. Verification Recipe
```bash
# 1. Verify Bridge Health and Model Discovery (should return 8 models)
curl -s http://127.0.0.1:20130/v1/models | jq '.data | length'

# 2. Verify Streaming SSE Response with Immediate Handshake
python -c "
import urllib.request, json
req = urllib.request.Request(
    'http://127.0.0.1:20130/v1/chat/completions',
    headers={'Content-Type': 'application/json'},
    data=json.dumps({'model': 'muse-spark-1.3', 'messages': [{'role': 'user', 'content': 'ping'}], 'stream': True}).encode('utf-8')
)
with urllib.request.urlopen(req, timeout=30) as resp:
    print(resp.readline().decode('utf-8'))
"
```
