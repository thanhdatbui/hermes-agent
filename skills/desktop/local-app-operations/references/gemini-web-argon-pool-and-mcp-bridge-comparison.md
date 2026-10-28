# Gemini Web Argon Pool Architecture & MCP Bridge Comparison

## Overview

Gemini Web Argon (`gemini-web-argon-pool` on OmniRoute `:20129`) provides access to Google's advanced Gemini models using Google AI Pro accounts over dedicated 4G mobile proxies.

## Model Identity: Gemini 4 (Argon) vs. Legacy UI Label "gemini-3.1-pro"

Operators checking OmniRoute's `Available Models` dashboard often notice that `gemini-web` lists `gemini-3.1-pro`, `gemini-3.7-flash`, and `gemini-3.1-flash-lite`, without explicitly showing "Argon" or "Gemini 4":
- **Legacy UI Catalog Label**: `gemini-3.1-pro` is a static UI metadata label seeded in OmniRoute's database (`key_value` table).
- **Backend Model Resolution**: In `open-sse/executors/gemini-web.ts`, selecting `gemini-3.1-pro` sets `modelCategory = 3`:
  ```typescript
  const modelCategory = modelId === "gemini-3.1-pro" ? 3 : undefined;
  if (modelCategory !== undefined) inner[79] = modelCategory;
  ```
  `inner[79] = 3` on Google's internal `StreamGenerate` endpoint instructs Google to invoke the flagship **Gemini 4 (Argon)** model (Sparse MoE architecture, 1M context window, native multimodal, deep reasoning capabilities).
- When queried directly via the pool, the model self-identifies as the **Gemini 4 (Argon)** generation.

## MCP Browser Bridge vs. Native OmniRoute HTTP Reverse Proxy

Operators often encounter tutorials advocating "MCP Gemini Web Bridges" (connecting Antigravity or IDE agents to Gemini Web via MCP tools). The architectures differ fundamentally:

| Dimension | MCP Browser Bridge (DOM Scraping) | OmniRoute Native HTTP StreamGenerate |
| :--- | :--- | :--- |
| **Transport** | Playwright / Chrome CDP typing into `.ql-editor` DOM element. | Direct headless HTTP POST to `/BardChatUi/data/assistant.lamda.BardFrontendService/StreamGenerate`. |
| **Footprint** | High RAM & CPU (renders full browser DOM, layout engine, CSS/JS). | Minimal (<10 MB RAM, lightweight JSON/Protobuf payload). |
| **Proxy / Multi-account** | Fragile: managing multiple Chrome profiles concurrently often leaks IPs or triggers mass bot checkpoints. | Clean: 5 Google AI Pro accounts isolated with 1-1 dedicated 4G Mobi proxies in SQLite `storage.sqlite`. |
| **Session & Token Liveness** | Breaks whenever Google alters DOM selectors, dialogs, or survey popups. | Auto-refreshes session tokens (`SNlM0e` / `__Secure-1PSIDTS`) dynamically from response headers. |
| **API Compatibility** | Custom tool wrapper (IDE must invoke specific MCP tool). | Standard OpenAI `/v1/chat/completions` protocol; drop-in replacement for any agent or client. |

## Fundamental Constraint: Absence of Native Tool Calling

Regardless of transport (MCP DOM hook or native StreamGenerate HTTP):
- Gemini Web does NOT expose native structured function calling or JSON schemas on the wire.
- Tool use is strictly **prompt-emulated** (`open-sse/translator/webTools.ts`), instructing the model to output `<tool>{...}</tool>` tags that regex parsers extract.
- OpenAI parameters like `reasoning_effort` and forced `tool_choice` cannot be honored (`capabilities.ts`).
- **Operational Recommendation**: Use `gemini-web-argon-pool` for architectural consults, QA, and long reasoning prompts; prefer native CLI workers (Agy CLI, Claude Haiku CLI) for multi-turn code surgery and repository refactoring.

## Live Verification Recipe

To probe whether the pool is healthy without launching browser UI:

```python
import urllib.request, json, time

url = "http://127.0.0.1:20129/v1/chat/completions"
body = {
    "model": "gemini-web-argon-pool",
    "messages": [{"role": "user", "content": "Ping: trả lời đúng 2 từ: ĐANG CHẠY"}],
    "stream": False,
}
req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
t0 = time.time()
resp = urllib.request.urlopen(req, timeout=45)
data = json.loads(resp.read().decode())
print("STATUS:", resp.status, "LATENCY:", round((time.time() - t0) * 1000), "ms")
print("MODEL:", data.get("model"))
print("CONTENT:", data["choices"][0]["message"]["content"])
```
Expected output: HTTP 200, model `gemini-3.1-pro`, latency ~10-15s over mobile proxy.
