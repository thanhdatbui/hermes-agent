# Free Tier LLM Harvesting (NVIDIA NIM, KiosAPI, Resellers)

## 1. Coding Agent Quota Exhaustion
Coding agents (OpenCode, CommandCode, Cline, Claude Code) consume 50k-200k tokens per loop. Official $10/mo tiers drain in 1-2 days.

## 2. NVIDIA NIM (`build.nvidia.com`)
- 1,000 free credits per account (no credit card).
- API Key: `nvapi-...`.
- Base URL: `https://integrate.api.nvidia.com/v1`.
- Models: DeepSeek V3/R1, Qwen 2.5 Coder 32B, Llama 3.1 405B/70B, Kimi K3, GLM.
- Route via 9Router `:20128` with key rotation.

## 3. KiosAPI (`kiosapi.com`)
- New-API v1.0.0-rc.41 hub.
- Free Groups: `Free` (5 RPM), `Free-Pro` (30 RPM). Requires Telegram verification.
- Live Free Models: `glm-5.3-free`, `deepseek-v4.1-flash-free`, `kimi-k3-free`, `grok-4.7-free`, `claude-opus-4-8-free`.
- Reseller groups: `Codex-Plus` (0.015 ratio / 98.5% off).
