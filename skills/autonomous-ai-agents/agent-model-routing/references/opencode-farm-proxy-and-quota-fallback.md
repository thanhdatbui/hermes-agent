# OpenCode Free Tier Quota Exhaustion & oc_farm Fallback Guide

## 1. Context & Architecture (Free Tier Reality)
- **Model Tiers**:
  - OpenCode Free CLI models: `opencode/muse-spark-1.3-contributor-free`, `opencode/nemotron-3-ultra-free`, `opencode/mimo-v2.6-flash-free`, `opencode/space-bunny-free`, `opencode/big-pickle`, `opencode/ling-3.0-flash-fin-free`.
  - Paid models (`opencode-go/*` như `glm-5.3`, `deepseek-v4.1-flash`, `kimi-k3`): Cần subscription $5/mo.
- **Upstream Guard Enforcements (2026-09)**:
  - OpenCode Zen HTTP endpoint (`https://opencode.ai/zen/v1/...`) blocks direct external proxies (403 Forbidden: `OpenCode's free tier can only be used from within OpenCode`).
  - OpenCode CLI binary requires version `>= 1.18.0` (npm: `opencode-ai@latest`).
  - Rate limits are calculated both per-day (Daily Quota) and per-IP.

## 2. Farm Proxy Rotation Wrapper (`D:/Taadaa/tools/oc_farm.py`)
To bypass IP-based rate limiting and spread daily quota consumption:
- Uses 69 Taadaa Farm proxies (35 MikroTik `10001..10035`, 32 Mobi `5101..5138`, 2 Khoalee `16001..16002`).
- Automatically injects:
  - `HTTPS_PROXY="http://user:pass@host:port"` (with URL encoded `@` as `%40`).
  - `NO_PROXY="localhost,127.0.0.1,::1"` (CRITICAL: prevents OpenCode internal IPC/TUI from hanging).
- Persistent cooldown tracker: `~/AppData/Local/hermes/oc_farm_cooldown.json`.
- Automatic detection and retry for `429`, `rate limit`, `daily quota`, or proxy connection failure.

## 3. Fallback Hierarchy when Main Worker Quota Exhausts
When primary coordinator / worker pools (Antigravity 429, Codex Luna limits) are exhausted:
1. **Never force OpenCode CLI into HTTP `fallback_providers`**:
   - `opencode run` is an agent with tools/bash, NOT a raw completion endpoint. Wrapping it into an OpenAI HTTP mock causes severe tool-calling breakage and high process spawn overhead.
2. **Use as Autonomous Coding Worker via `oc_farm.py`**:
   - Coordinator invokes:
     ```bash
     python D:/Taadaa/tools/oc_farm.py run --format json --model opencode/muse-spark-1.3-contributor-free "task..."
     ```
   - OpenCode runs in an isolated git worktree, executes edits and local tests.
   - Text output / diff is captured and reviewed by the Coordinator / Reviewer (`closeout_gate.py`).
