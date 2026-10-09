# OpenCode Free Tier Farm Proxy Integration & Fallback Ops (2026-09-27)

## 1. Upstream Barriers & Enforcement
- **403 External Block:** Upstream OpenCode Zen (`https://opencode.ai/zen/v1/...`) blocks non-CLI clients (403 FreeTierError: "OpenCode's free tier can only be used from within OpenCode").
- **Version Gating:** OpenCode CLI requires version `>= 1.18.0` (update via `npm i -g opencode-ai@latest`). Older versions (e.g. 1.17.19) reject free tier requests immediately.
- **Model Categories:**
  - *Free Tier (No subscription, 100% $0):* `opencode/muse-spark-1.3-contributor-free`, `opencode/nemotron-3-ultra-free`, `opencode/space-bunny-free`, `opencode/big-pickle`, `opencode/ling-3.0-flash-fin-free`, `opencode/nemotron-3.5-lightning-free`.
  - *Paid Tier (OpenCode Go - $5/mo):* `opencode-go/glm-5.3`, `opencode-go/deepseek-v4.1-flash`, `opencode-go/kimi-k3`.

## 2. 69 Farm Proxy Rotation Wrapper (`D:/Taadaa/tools/oc_farm.py`)
To prevent IP rate-limiting (`429 Too Many Requests / Daily Limit`), OpenCode CLI must be run via `oc_farm.py`:
- Rotates across 35 MikroTik (`10001..10035`), 32 Mobi (`5101..5138`), 2 Khoalee.
- Uses `shutil.which('opencode')` to resolve the Windows binary correctly on Windows / Git-Bash.
- Sets environment variables: `HTTPS_PROXY`, `HTTP_PROXY`, `ALL_PROXY`.
- **CRITICAL INVARIANT:** Must always set `NO_PROXY="localhost,127.0.0.1,::1"` to prevent internal IPC/TUI hanging.
- Caches cooldown state in `~/AppData/Local/hermes/oc_farm_cooldown.json` (300s backoff upon 429/timeout).

## 3. Hermes Gateway & Fallback Layering Architecture
- **Worker Level (Tầng 2):** When main workers (Codex Luna/Gemini) run out of quota, Hermes Coordinator delegates coding tasks directly to `python D:/Taadaa/tools/oc_farm.py run --model opencode/muse-spark-1.3-contributor-free "task..."`.
- **Session Fallback Level (Tầng 1 - `config.yaml`):**
  - Upstream OpenCode cannot serve as a raw HTTP completion provider for Hermes core loop due to agent-loop nature and tool-calling mismatch.
  - To enable a 100% free fallback chain for the Hermes main session when Antigravity / Gemini is exhausted:
    ```yaml
    fallback_providers:
      - model: gpt-5.6-luna
        provider: custom:9router
      - model: omni-free
        provider: custom:omni
      - model: cx/gpt-5.6-luna-high
        provider: custom:omni
    ```
  - `omni-free` routes to active, verified free models on OmniRoute (InclusionAI Ling Flash Free, Nvidia Nemotron Super 120B Free, Liquid LFM Free, Cohere North Mini Free) supporting native OpenAI SSE streaming and JSON tool calls.
- **Telegram /model Switch:**
  - Registered aliases in `config.yaml`: `free` and `omni-free` -> `custom:omni/omni-free`.
  - User can execute `/model free --session` directly in Telegram chat to switch to the free pool without restarting Gateway or modifying root configs.
