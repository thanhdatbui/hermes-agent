# OpenCode Bridge & Hermes Fallback Multi-threading Architecture

## Problem Statement
When primary LLM provider pools (Antigravity/Gemini, Claude, Codex) experience sudden concurrency bursts, proxy outages (e.g. mobile 4G cluster loss of power/signal), or 429 semaphore timeouts, Hermes triggers the configured `fallback_providers`.
If the fallback provider is an OpenCode CLI wrapper (such as `oc_farm.py` managing 69 farm proxies), naive HTTP adapters fail under multi-turn or high-concurrency loads.

## Failure Modes Observed
1. **Connect Timeout (15s):** Hermes has a hard default connection timeout of 15.0s (`connect=15.0`, `write=15.0`). If an adapter launches `subprocess.run(oc_farm ...)` *before* sending HTTP response headers, proxy rotation latency (15-20s) triggers `httpx.ConnectTimeout` / `APIConnectionError: Connection error.` in Hermes.
2. **Single-threaded Concurrency Block:** When multiple background agents (gateway message, cronjob, farm batch alert) fire simultaneously, a standard `HTTPServer` queues connections synchronously. Subagent 2 gets timed out while Subagent 1 is running.
3. **Context Truncation / Empty Prompts:** Passing whole conversation history to OpenCode CLI without extracting the latest user task results in OpenCode reading the cwd as a project and asking "Empty prompt — what do you want to do?".
4. **Model Pollution:** Upstream `opencode models` returns 100+ paid/internal models (`opencode-go/*`, `commandcode-direct/*`). Allowing all 100+ models clutters Telegram `/model` selector with models requiring payment or credentials.

## Architectural Solution (Implemented in `D:/Taadaa/tools/opencode_bridge.py`)

### 1. Multi-threaded Server Base
```python
import socketserver
from http.server import HTTPServer

class ThreadingHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True
```

### 2. Immediate SSE Handshake Flush (0.01s TTFB)
Never wait for `oc_farm.py` to return before answering Hermes. Send HTTP 200 and initial chunk immediately:
```python
self.send_response(200)
self.send_header("Content-Type", "text/event-stream")
self.send_header("Cache-Control", "no-cache")
self.send_header("Connection", "close")
self.end_headers()

# Send heartbeat/role chunk immediately
init_chunk = {
    "id": chat_id,
    "object": "chat.completion.chunk",
    "created": created_time,
    "model": model_id,
    "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
}
self.wfile.write(f"data: {json.dumps(init_chunk)}\n\n".encode("utf-8"))
self.wfile.flush()
```

### 3. Clean Prompt Extraction
Extract strictly the actual user task instead of dumping hundreds of system/tool dump lines into CLI arguments:
```python
def extract_prompt_from_messages(messages: list[dict[str, Any]]) -> str:
    user_msgs = []
    for msg in messages:
        if msg.get("role") == "user":
            c = msg.get("content") or ""
            if isinstance(c, list):
                c = " ".join([i.get("text", "") for i in c if isinstance(i, dict) and i.get("type") == "text"])
            if c:
                user_msgs.append(c)
    return user_msgs[-1] if user_msgs else "hello"
```

### 4. 100% Free Model Whitelist
Filter `opencode models` strictly to `opencode/*` (prefix stripped of `-contributor-free`):
- `muse-spark-1.3`
- `nemotron-3-ultra`
- `nemotron-3.5-lightning`
- `mimo-v2.6-flash`
- `big-pickle`
- `space-bunny`
- `ling-3.0-flash-fin`
- `longcat-2.5-preview`
Cache with TTL = 300s to avoid executing subprocess on every model check.

## Verification Checklist
1. `GET http://127.0.0.1:20130/v1/models` returns exactly 8 models.
2. `POST http://127.0.0.1:20130/v1/chat/completions` with 300+ messages starts streaming chunks within < 50ms.
3. Fallback configuration in `~/.hermes/config.yaml`:
   ```yaml
   fallback_providers:
     - model: muse-spark-1.3
       provider: custom:opencode
   ```
