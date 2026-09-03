# OpenRouter Routing via 9Router

## 1. Authentication & Querying 9Router Locally
- 9Router API endpoint: `http://localhost:20128/v1/`
- Local requests require: `Authorization: Bearer <key>`
- Local API key is stored in SQLite DB:
  `%APPDATA%\9router\db\data.sqlite` -> table `apiKeys` (column `key`).

## 2. Upstream OpenRouter Configuration
- OpenRouter credentials & status are in table `providerConnections` where `provider = 'openrouter'`.
- Data JSON contains the upstream API key `apiKey` (`sk-or-v1-...`) and connection status `testStatus`.

## 3. Model ID Naming Convention
- OpenRouter models accessed via 9Router MUST use the `openrouter/` prefix followed by the upstream OpenRouter model ID:
  - Example: OpenRouter ID `stealth/ox-alpha` -> 9Router ID `openrouter/stealth/ox-alpha`.
  - Example: OpenRouter ID `google/gemma-4-26b-a4b-it:free` -> 9Router ID `openrouter/google/gemma-4-26b-a4b-it:free`.
- Model ID without prefix (e.g., `stealth/ox-alpha`) will return `404 Not Found`.

## 4. Reasoning Models & Streaming Behavior
- Models with deep reasoning (e.g. `stealth/ox-alpha` / Ox Alpha) return reasoning details in JSON.
- Non-streaming requests may time out or produce malformed JSON delimiter chunks if parsed naively.
- Always prefer `stream: true` (SSE) when inspecting or calling reasoning models.

## 5. Wiring into Hermes config.yaml
- Under `custom_providers` -> `name: 9router` -> `models:`
- Add model entry directly via python script edit with backup (avoid `hermes config set` to prevent dotted key corruption):
  ```yaml
  openrouter/stealth/ox-alpha:
    context_length: 1048576
  ```
