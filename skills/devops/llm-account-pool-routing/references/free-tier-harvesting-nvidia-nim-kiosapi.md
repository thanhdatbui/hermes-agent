# Free Tier Harvesting & Aggregator Routing for AI Coding Agents

## 1. Context & Problem Statement
AI Coding Agents (OpenCode, CommandCode / cmdc, Claude Code, Cline, Aider) consume 50k–200k tokens per tool loop (repo maps, test runs, diffs). Fixed monthly subscriptions (e.g. OpenCode Go $10/mo, Go Plus $40/mo) exhaust quota within 1–2 days under heavy development. Devs scale throughput via free tier harvesting, token reseller pools, and custom proxy endpoints.

## 2. NVIDIA NIM API Catalog (`build.nvidia.com`)
- **Account Mechanics**:
  - Sign-up at `build.nvidia.com` (Email / Google / MS). No credit card required.
  - Grants **1,000 free inference credits** per account.
  - API Key prefix: `nvapi-...`.
  - Base URL: `https://integrate.api.nvidia.com/v1` (OpenAI-compatible).
- **High-Value Agentic Models**:
  - `deepseek-ai/deepseek-v3`, `deepseek-ai/deepseek-r1`
  - `qwen/qwen2.5-coder-32b-instruct`
  - `meta/llama-3.1-405b-instruct`, `meta/llama-3.1-70b-instruct`
  - `nvidia/llama-3.1-nemotron-70b-instruct`
  - Moonshot Kimi / Zhipu GLM models
- **Farm / Pool Implementation**:
  - Pool 10–30 `nvapi-...` keys into 9Router (`:20128`) or local One-API/New-API instance.
  - Configure spillover on 402/429 (out of credits / rate-limited) to rotate to next key.

## 3. KiosAPI (`kiosapi.com`)
- **Platform Architecture**: Multi-model aggregator running New-API (`v1.0.0-rc.41`).
- **Free Groups (`Free`, `Free-Pro`)**:
  - Ratio: `0` (100% free).
  - Rate Limits: `Free` = 5 RPM; `Free-Pro` = 30 RPM.
  - Verification: Requires Telegram bot verification + joining official Telegram channel to prevent clone abuse.
  - Endpoint: `https://kiosapi.com/v1` (supports `/v1/chat/completions`, Anthropic `/v1/messages`, Gemini native).
- **Available Free Models (Verified Live)**:
  - `deepseek-v4.1-flash-free`, `deepseek-v4-flash-free`, `deepseek-v4-flash-vision-exp-free`
  - `glm-5.3-free`, `glm-5.3-flash-free`
  - `kimi-k3-free`
  - `grok-4.7-free`
  - `claude-opus-4-8-free`
  - `nemotron-3-ultra-550b-a55b`, `nemotron-3.5-lightning`
  - `qwen3.8-flash-free`, `qwen3.8-27b-free`
- **Paid / Reseller Groups**:
  - `Codex-Plus` / `Discount`: 0.015 ratio (98.5% discount) for GPT-6 Sol / Claude Sonnet / Opus tiers.

## 4. Alternative High-Volume Free Tiers
- **Google AI Studio**: 15 RPM / 1M TPM / 1,500 RPD per key for `gemini-2.5-flash` and `gemini-3-flash`. Best for context size (1M+) and zero cost when pooled with farm Gmails.
- **SiliconCloud / SiliconFlow**: Free initial credits + perpetual free tier for open-source models (`Qwen2.5-Coder`, `DeepSeek-V3`).
- **Groq Cloud**: 300–500 tokens/sec for fast unit testing / syntax checking steps.

## 5. Agent Integration Pattern
Point coding agents (OpenCode / CommandCode / Cline) away from default provider endpoints to local router or harvested endpoint:
```json
{
  "openai": {
    "baseURL": "http://localhost:20128/v1", // or https://integrate.api.nvidia.com/v1
    "apiKey": "nvapi-..." // or 9Router proxy key
  }
}
```
