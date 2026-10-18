# Gemini Web 4 Argon: Architecture, Wire Protocols & CDP Daemon Bridge

## 1. Wire Protocol Divergence: StreamGenerate vs. processSession

When reverse-engineering Google Gemini Web accounts (Google AI Pro / Advanced tier):

### StreamGenerate (Legacy HTTP REST)
- Endpoint: `https://gemini.google.com/_/BardChatUi/data/assistant.lamda.BardFrontendService/StreamGenerate`
- Model Selection Slot `[79]` enum (`MODE_CATEGORY`):
  - `1`: Flash
  - `2`: Flash Thinking
  - `3`: Pro
  - `4`: Auto
  - `5`: Dynamic Thinking
  - `6`: Flash Lite
- Slot `[17]`: `thinkMode` (`[[0]]` High Thinking, `[[2]]` Medium, `[[4]]` Low).
- **CRITICAL ANTI-PATTERN**: `StreamGenerate` does NOT have an enum or slot for "4 Argon". Any attempt to claim slot `[79]` activates 4 Argon without network wire proof is false ("giả cầy"). Mapping slot `[79]=3` only activates Gemini 3.1 Pro.

### processSession (Modern WebChannel / Protobuf)
- Endpoint: `https://geminiweb-pa.clients6.google.com/v1/processSession`
- Full bidirectional WebChannel streaming.
- Triggered exclusively when selecting "4 Argon" on the live UI model switcher.

---

## 2. Headless CDP Daemon Bridge Pattern (`gemini_argon_server.py`)

To serve genuine 4 Argon weights without running an interactive browser window:

1. **Profile Storage via GPM**:
   - Accounts run inside GPM profiles with dedicated 4G mobile proxies (`test.taadaa.click:5101-5136`).
   - GPM API (`http://127.0.0.1:19995/api/v3/profiles/start/{id}`) returns `remote_debugging_address`.

2. **Playwright CDP Daemon Lifecycle**:
   - Run a single background worker thread connecting via `chromium.connect_over_cdp(f"http://{addr}")`.
   - Maintain persistent page at `https://gemini.google.com/app` offscreen (window size 1280x900, zero cursor/keyboard theft).
   - Ensure "4 Argon" model is selected from `[role="menuitem"]:has-text("4 Argon")`.

3. **Request/Response Loop**:
   - Expose local OpenAI-compatible endpoint: `POST http://127.0.0.1:20135/v1/chat/completions` (model: `gemini-4-argon`).
   - Focus input container `div[contenteditable="true"], rich-textarea p`, insert prompt text, trigger send button.
   - Generation detection: poll stop button (`button:has-text("Ngưng"), [data-test-id="stop-button"]`) until hidden (timeout ~75-180s).
   - Extraction: scroll `.model-response-text, [data-test-id="conversation-turn"]` into view, collect text blocks, deduplicate repeating stream lines.

---

## 3. Benchmark Insights: Argon Medium vs. Argon High

Measured across 5 production farm problem sets (UI XML parsing, Proxy pool circuit breaker, Atomic file state, pHash calculation, Task queue):
- **Latency**: Minimal difference on Google infrastructure (~15.25s Medium vs. ~15.87s High).
- **Code Quality**: High achieves superior runtime defensiveness:
  - Implements `__lt__` on task objects to prevent `TypeError` under equal priority queues.
  - Decomposes 2D DCT into 1D row/column passes reducing complexity from $\mathcal{O}(N^4)$ to $\mathcal{O}(N^3)$.
  - Provides recursive traversal with optional exact matching flags.
- **Role Assignment**:
  - Worker code implementation: Default to `high`.
  - Batch translation / summarization throughput: Default to `medium`.
