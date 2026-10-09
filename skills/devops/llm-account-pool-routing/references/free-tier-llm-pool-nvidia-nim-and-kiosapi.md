# Free-Tier LLM Pool: NVIDIA NIM & KiosAPI Aggregation

## 1. Overview & Use Case
Coding agents (OpenCode, Claude Code, Cline, Roo Code, Hermes subagents) consume 50k–200k tokens per task iteration. Official paid tiers (e.g. OpenCode Go $10/mo, Go Plus $40/mo) deplete within days. Aggregating free/cheap tier providers into internal proxies (9Router `:20128`, OmniRoute `:20129`) provides high-throughput, zero-cost resilience.

---

## 2. Provider Breakdown

### A. NVIDIA NIM API (build.nvidia.com)
- **Nature**: Direct enterprise GPU catalog by NVIDIA (H100/B200 infrastructure).
- **Quota**: 1,000 free credits per account (format: `nvapi-...`).
- **Base URL**: `https://integrate.api.nvidia.com/v1`
- **Endpoint**: Standard OpenAI-compatible `/chat/completions`.
- **Top Coding & Reasoning Models**:
  - `qwen/qwen2.5-coder-32b-instruct` (Top open-source model for agentic coding & tool use)
  - `deepseek-ai/deepseek-r1` (Complex algorithmic reasoning, hard debugging)
  - `deepseek-ai/deepseek-v3` (Fast refactoring & codebase scanning)
  - `meta/llama-3.3-70b-instruct` (Long-context generalist)
- **Lifecycle & Farming**:
  - Requires email signup (Hotmail/Gmail via GPM profiles), no credit card or KYC.
  - Multi-account pool pattern: Generate batch of 10–20 `nvapi-...` keys and load into 9Router channel with automatic round-robin / 402-429 fallback.

### B. KiosAPI (kiosapi.com)
- **Nature**: New-API based LLM aggregator / reseller hub.
- **Quota / Rate Limits**:
  - `Free` group: 5 RPM.
  - `Free-Pro` group: 30 RPM.
- **Unlock Requirement**: Link account to Telegram bot and join official Telegram channel (`@kiosapi_official`).
- **Base URL**: `https://kiosapi.com/v1`
- **Key Models Available on Free Tiers**:
  - `glm-5.3-free`, `glm-5.3-flash-free`
  - `deepseek-v4.1-flash-free`, `deepseek-v4-flash-free`
  - `kimi-k3-free`
  - `grok-4.7-free`
  - `qwen3.8-flash-free`, `qwen3.8-27b-free`

---

## 3. Proxy Integration Pattern (9Router / OmniRoute)

```yaml
# 9Router Provider Routing Strategy
providers:
  nvidia-nim-pool:
    type: openai
    base_url: "https://integrate.api.nvidia.com/v1"
    keys:
      - "nvapi-key-1"
      - "nvapi-key-2"
      - "nvapi-key-3"
    strategy: round_robin
    failover_on: [402, 429, 503]

  kiosapi-free-fallback:
    type: openai
    base_url: "https://kiosapi.com/v1"
    keys:
      - "sk-kiosapi-token"
    strategy: fallback
```

---

## 4. Automation via GPM + CDP Pitfalls
1. **Hidden Submit / Next Buttons**: NVIDIA signin modal hides the `Next` button under certain responsive breakpoints (`hidden md:min-w-[100px] lg:inline-block`). Use keyboard `press("Enter")` on the email input field rather than clicking locator.
2. **Registration Redirect**: Submitting email routes to `https://login.nvgs.nvidia.com/v1/create-account` if account does not exist. Password fields require standard complex string (`TaadaaNvidia#2026!`) and terms checkbox checked.
