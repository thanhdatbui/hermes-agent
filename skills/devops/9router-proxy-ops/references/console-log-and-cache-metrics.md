# 9Router Console Log & Metrics Guide

## 1. Console Log UI & Endpoints
* **Web UI:** `http://localhost:20128/dashboard/console-log`
* **Local Database:** `%APPDATA%\9router\db\data.sqlite` (table: `usageHistory`, `requestDetails`, `settings`)
* **API Endpoints:** `/api/translator/console-logs`, `/api/usage/request-logs`

## 2. Console Log Metrics Explained
In the live stream console log (`/dashboard/console-log`), requests output:
`POST <model_alias> -> <provider>/<model> · FMT: <format> · MSG: <n> · <k> TOOL · THINK:<mode> · ACC:<email>`
Followed by completion stats:
`DONE <total_ms>ms · TTFT <first_token_ms>ms · IN <input_tokens> (CACHE <cached_tokens>) · OUT <output_tokens>`

* **IN (Input Tokens):** Total context tokens sent (system prompt + active tools schema + conversation history + memory).
* **CACHE (Cached Tokens):** Number of prompt tokens served directly from the upstream provider's prompt cache (e.g. Google Gemini Context Caching via Antigravity). High cache hits (>85–95%) drastically reduce latency and cost.
* **OUT (Output Tokens):** Tokens generated in the response (including thinking/reasoning traces when enabled).
* **TTFT (Time To First Token):** Latency until the first stream chunk arrives. When CACHE is high, TTFT remains low (1.5s–3.5s) even with 100k+ input tokens.

## 3. Sequential Routing vs Round-Robin for Cache & Safety
* **Prompt Cache Preservation:** Gemini/Antigravity caches prompts per-account/project. Sequential (fill-first) execution retains 85–95% cache hit. Round-robin causes 100% cache miss per request and increases TTFT to 10–20s+.
* **Auto-cooldown on 429 Quota:** For Antigravity/Google OAuth, quota exhaustion is model-scoped. `%APPDATA%\9router\quota_manager.py` must preserve `providerConnections.isActive=1`, extend only `modelLock_<gemini-model>` for 5h, and keep Claude Sonnet usable on the same account. Legacy account-level cooldown keys are normalized to `<connection_id>::<gemini-model>`. 9Router's own short `modelLock_<model>` backoff remains separate.
