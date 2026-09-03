# OmniRoute & 9Router Free Providers Catalog & Routing

## Overview

OmniRoute (`:20129`) and 9Router (`:20128`) support 349+ LLM providers. This reference documents verified free tiers, zero-config providers, and configured free fallback combos.

---

## 1. Zero-Config & No-Auth Free Providers (No API Key Required)

* **OpenCode Free (`opencode` / `oc/` prefix):**
  * **Auth:** No key required; uses public free endpoint.
  * **Supported Free Models:** `oc/deepseek-v4-flash-free`, `oc/nemotron-3-ultra-free`, `oc/x-preview-f-free`, `oc/mimo-v2.5-free`, `oc/laguna-s-2.1-free`, `oc/hy3-free`, `oc/big-pickle`.
  * **Role in System:** Primary lightweight fallback in `opencode-free`, `worker`, `deepseek-v4-flash`, and `deepseek-v4-pro` combos.
* **DuckDuckGo AI Chat (`duckduckgo-web` / `ddgw`):** Anonymous free web chat backend.
* **Felo Web (`felo-web` / `felo`):** Free search & chat aggregator.
* **The Old LLM (`theoldllm`):** Auto-token generation via headless browser runtime.

---

## 2. Configured OAuth Pools on Local Host

* **Google Antigravity (`antigravity`):**
  * **Capacity:** Multi-account pool (7 active Google OAuth accounts on local runtime).
  * **Top Models:** `gemini-3.7-flash-high`, `claude-sonnet-4-6`, `claude-opus-4-6-thinking`.
  * **Best Use:** Heavy reasoning, coding, and primary agent tasks.
* **Google Gemini CLI (`gemini-cli`):**
  * **Capacity:** Direct Google Cloud CLI OAuth (`jinrakal@gmail.com`).
  * **Models:** `gemini-3.1-pro-preview`, `gemini-3-flash-preview`, `gemini-2.0-flash`.
* **OpenAI Codex (`codex`):**
  * **Capacity:** Plus subscription pool (`gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna`).

---

## 3. High-Value Free-Tier API Key Providers

Providers offering completely free tiers (no credit card required upon signup):

| Provider ID | Provider Name | Free Quota | Key Models & Highlights |
| :--- | :--- | :--- | :--- |
| `openrouter` | **OpenRouter** (`:free` suffix) | 20 RPM / 200 RPD ($0/token) | `nvidia/nemotron-3-ultra-550b-a55b:free`, `z-ai/glm-5.2:free`, `google/gemma-4-31b-it:free`, `nvidia/nemotron-3.5-lightning:free`, `cohere/north-mini-code:free`, `poolside/laguna-s-2.1:free` |
| `groq` | **Groq** | 30 RPM / 14,400 RPD | Ultra-fast inference (300-500 tok/s): Llama 3.3 70B, Qwen 2.5 32B, DeepSeek R1 Distill |
| `cerebras` | **Cerebras** | 1M tokens/day, 5 RPM | Highest generation speed (~1,500-2,000 tok/s): Llama 3.3 70B, Llama 3.1 8B |
| `gemini` | **Google AI Studio** | 15 RPM / 1,500 RPD | Official Gemini 2.0 Flash / Thinking / 1.5 Pro with dedicated API key |
| `nvidia` | **NVIDIA NIM** | ~40 RPM | 70+ models: Kimi K2.5, GLM 4.7, DeepSeek V3/R1, Nemotron, Llama 3.3 70B |
| `mistral` | **Mistral AI** | Free Experiment Tier | `codestral` (specialized coding model), `mistral-small`, `mistral-large` |
| `api-airforce` | **Api.airforce** | 55 Free Models | Claude 3.7, Grok-3, Qwen3, DeepSeek-V3, Gemini 2.5 Flash |
| `siliconflow` | **SiliconFlow** | Free $0 Catalog + $1 trial | Open-source $0 models (DeepSeek V3/R1, Qwen Coder) |

---

## 4. Configured Free Combos in Local Router

* **`openrouter-free`:**
  * Targets: Nemotron 3 Ultra 550B, Nemotron 3 Super 120B, GLM 5.2, Gemma 4 31B, Nemotron 3.5 Lightning, North Mini Code, Laguna S 2.1.
* **`opencode-free`:**
  * Targets: `oc/hy3-free`, `oc/x-preview-f-free`, `oc/nemotron-3-ultra-free`, `oc/nemotron-3.5-lightning-free`, `oc/mimo-v2.5-free`, `oc/laguna-s-2.1-free`, `oc/big-pickle`.
