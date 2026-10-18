# Gemini Web "4 Argon" CDP Daemon & AGY Multi-Account Pool Diagnosis

## 1. Protocol Architecture: Gemini Web "4 Argon" vs StreamGenerate
- **UI Label vs Network Wire Reality:**
  - `gemini.google.com/app` UI displays: `3.5 Flash-Lite`, `3.8 Flash`, `3.1 Pro`, `4 Argon`.
  - Endpoint `StreamGenerate` (used by reverse-engineered HTTP executors like `gemini-web.ts`) only accepts numeric enum categories for legacy Flash/Pro (`MODE_CATEGORY` 1: Flash, 2: Flash Thinking, 3: Pro, 4: Auto, 5: Dynamic Thinking, 6: Flash Lite).
  - Selecting "4 Argon" on live web triggers Google's new WebChannel streaming protocol: `POST https://geminiweb-pa.clients6.google.com/v1/processSession` (binary protobuf over duplex WebChannel).
  - **Rule:** Never claim HTTP REST `StreamGenerate` activates true "4 Argon" weights without verified wire payload evidence. Mapping slot 79 to a non-existent Argon enum causes Google to silently fall back to default consumer model weights.

## 2. CDP Headless Daemon Pattern for Web Models (Stateless Local API)
When upstream web features require true browser sessions without polluting host desktop or ceding mouse/keyboard focus:
- Run GPM Chromium profile via remote debugging port (`remote_debugging_address`).
- Wrap via Playwright CDP connection in an off-screen, headless-equivalent daemon server (e.g. port `20135`).
- Expose standard OpenAI endpoint: `POST /v1/chat/completions` (model: `gemini-4-argon`).
- **Selector Stability & Extraction Protocol:**
  - Input: `div[contenteditable="true"], rich-textarea p, rich-textarea div, div.ql-editor`.
  - Send button: `button[aria-label*="Gửi"], button[aria-label*="Send"], button.send-button, [data-test-id="send-button"]` (fallback: `input_el.press("Enter")`).
  - Stop button detection: wait until `button[aria-label*="Ngưng"], button[aria-label*="Stop"], [data-test-id="stop-button"], div[role="button"]:has-text("Ngưng")` disappears.
  - Mandatory floor wait: give 5s minimum thinking floor before probing stop button.
  - Response extraction: scroll conversation container (`.model-response-text, [data-test-id="conversation-turn"]`) into view, extract inner text, deduplicate repeated identical DOM text chunks.
- **Session Cleanliness (Anti-Hallucination & Anti-Ban):**
  - Do NOT accumulate chat history on web profiles (`Temporary Chat` mode or fresh tabs per task).
  - Persistent chat history contaminates LLM context across independent coding tasks and increases abuse-detection risk from Google Web.

## 3. Reasoning Effort Benchmarks on Google Pro (Medium vs High)
- Reasoning levels on Gemini Web wire:
  - `none`: `null` (raw reflex, ~1-2s, high hallucination rate for code/concurrency).
  - `low`: `[[4]]` (~2-4s, minimal edge-case reasoning).
  - `medium`: `[[2]]` (~10-15s, standard pragmatic code).
  - `high`: `[[0]]` (Deep Think, ~14-27s).
- **Benchmark Insight:** In complex binary/multi-threading tasks (e.g. 64-bit MP4 box parser, subnet ARP auditor), `high` often finishes **faster** than `medium` (e.g. 14s vs 48s) because deep search converges directly without conversational backtracking, while producing superior AST-valid defensive code (`__lt__` override on priority items, 2-stage DCT math, standard `NamedTuple`).
- **Rule for Coding Workers:** Always default to `reasoning_effort: "high"` for code synthesis, multi-threading, and systems engineering.

## 4. AGY Multi-Profile Pool: The "Dead Profile Starvation" Trap
- **Pool Inventory Verification:**
  - Before concluding accounts are duplicated, inspect `google_accounts.json` and `oauth_creds.json` inside each profile directory (`D:/Taadaa/agy_profiles/acc_*/.gemini/`).
  - Distinct active emails and distinct `refresh_token` strings (103 chars) prove independent Google accounts.
- **The LRU Starvation Bug:**
  - When `ag_cli.py` selects profiles by `last_used` timestamp (LRU):
  - A profile that fails or times out (e.g., due to a slow mobile proxy) never records a completed `last_used` timestamp (`last_used` remains `0`).
  - If timeout exceptions do not put the profile into a temporary cooldown or bump its timestamp, subsequent requests will repeatedly pick the same failing profile!
  - **Symptom:** Every request fails at the exact same timeout (e.g. 120s), making the entire pool appear "completely dead" even though other profiles (`acc_17`, etc.) are healthy and ready.
  - **Fix:** On `subprocess.TimeoutExpired` or network drop, the dispatch driver must immediately record a failure cooldown timestamp or penalize `last_used` so subsequent dispatches failover to healthy pool members.
