# Local LLM Adapter Gateway Timeout & Immediate SSE Handshake Pattern

## Context
When running local model adapters (e.g. `opencode_bridge.py`, custom proxy bridges, or local worker wrappers) as a fallback or custom provider for Hermes Gateway on Telegram:
* Hermes default HTTP client sets `connect_timeout = 15.0s`.
* Upstream execution via rotating proxies, heavy local CLI inference, or subprocess bootstrapping often takes >15s before the first token is generated.

## The Connection Error Failure Mode
* Single-threaded HTTP servers (`http.server.HTTPServer`) block concurrent health checks or incoming messages.
* Delaying the HTTP response headers until upstream generation starts causes Hermes to hit `APIConnectionError: Connection error.` exactly at 15.0s.
* Gateway triggers: `⚠️ The model provider failed after retries.`

## The Fix: ThreadingHTTPServer + Immediate SSE Handshake
1. Always use `socketserver.ThreadingMixIn` with `HTTPServer`:
```python
class ThreadingHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True
```
2. When `stream=True`, send HTTP 200 headers and an initial assistant role chunk immediately (within 10ms), before waiting on upstream processing:
```python
self.send_response(200)
self.send_header("Content-Type", "text/event-stream")
self.send_header("Cache-Control", "no-cache")
self.send_header("Connection", "close")
self.end_headers()

# Immediate handshake satisfies Hermes connect timeout (15s)
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
3. Deliver subsequent content chunks as they arrive from upstream, and conclude with `finish_reason: "stop"` and `data: [DONE]`.
