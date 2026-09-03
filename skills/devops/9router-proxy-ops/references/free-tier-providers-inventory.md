# 9Router Free Tier Providers — inventory (verified 2026-08-13, v0.5.50)

Read each via `/dashboard/providers/<slug>` (see SKILL.md "Providers dashboard" section).
Auth type / models / risk notes gathered live from the dashboard UI.

| Slug | Provider | Auth | Free models (highlight) | Notes |
|---|---|---|---|---|
| `opencode` | OpenCode Free | none (noAuth:true) | deepseek-v4-flash-free, mimo-v2.5-free, big-pickle, nemotron-3-ultra-free, hy3-free, north-mini-code-free | Already **Ready**. Routable via combo `opencode-free`. |
| `gemini-cli` | Gemini CLI | OAuth Google | Gemini 3.1 Pro, 3 Pro, 2.5 Pro + Flash | ⚠ Risk Notice: unofficial OAuth, ban risk |
| `kiro` | Kiro AI | OAuth (Amazon) | Claude Opus 5/4.8/4.7/4.5, Sonnet 5/4.5, Haiku 4.5, DeepSeek 3.2, Qwen3 Coder Next, GLM 5, MiniMax M2.5, GPT 5.6 Sol/Terra/Luna | ⚠ Risk Notice: unofficial OAuth, ban risk |
| `openrouter` | OpenRouter | API key (free) | 27+ free: nemotron-3.5-lightning, nemotron-3-ultra, gemma-4-26b/31b, laguna-s/xs, north-mini-code, lyria… | 200 req/day (1000 after $0 credit). Suggested free models listed as `add <model>` buttons. |
| `nvidia` | NVIDIA NIM | NVIDIA Dev account | nvidia/minimaxai/minimax-m2.7/m3, nvidia/z-ai/glm-5.2, nvidia/deepseek-ai/deepseek-v4-pro/flash, nvidia/moonshotai/kimi-k2.6, nvidia/nvidia/nemotron-3-ultra-550b-a55b | Free for NVIDIA Developer Program members. |
| `ollama` | Ollama Cloud | API key | GPT OSS 120B, Kimi K2.5, GLM 5, MiniMax M2.5/M3, GLM 4.7 Flash, Qwen3.5 | Light: 1 cloud model at a time, reset every 5h & 7d. |
| `vertex` | Vertex AI | GCP Service Account | Gemini 3.1 Pro, 3.1 Flash Lite, 3 Flash, 2.5 Flash | $300 free credit (new GCP); project + Vertex AI-enabled SA required. |
| `gemini` | Gemini (AI Studio) | API key | gemini-3.6/3.5/3.1/3/2.5 Pro+Flash, gemma-4-31b | Google AI Studio key. |
| `cloudflare-ai` | Cloudflare | API token + Account ID | Llama 3.2 1B/3B, Llama 3.1 8B/70B, Llama 3.3 70B, Mistral Small 3.1 24B, DeepSeek R1 Distill Qwen 32B, Kimi K2.5/2.6, GLM 4.7 Flash, QwQ 32B, Qwen 2.5 Coder 32B | Workers AI free tier. |
| `poolside` | Poolside | API key | Laguna S 2.1, Laguna XS 2.1 | |
| `byteplus` | BytePlus ModelArk | API key | Seed 2.0 Pro/Code Preview/Mini/Lite, Kimi K2 Thinking, GLM 4.7, GPT-OSS-120B | Free credits for new accounts. |
| `kimchi` | Kimchi | Sign up | MiniMax-M3, Kimi-K2.7/2.6/2.5, Nemotron 3 Ultra FP4, MiniMax-M2.7, Claude Opus/Sonnet 4.6 | |
| `api-airforce` | API.airforce | API key | Claude 3.7 Sonnet (Free), Kimi K2.6 (Free), Gemini 2.5 Flash (Free) | |
| `bazaarlink` | Bazaarlink | API key | **Auto Free (Zero Cost)** + Claude Opus 4.7, GPT-5.5, Grok 4.3, Gemini 3.1 Pro/Flash, Kimi K2.6/2.5, GLM 5.1/5, MiMo-V2.5-Pro/V2.5, MiniMax M3/M2.7/M2.5, Qwen 3.6 Plus, Nemotron 3 Super | Has an "Auto Free" zero-cost route. |
| `kilo-gateway` | Kilo Gateway | API key | Kilo Auto Free, Nemotron 3 Super 120B (Free), Nemotron 3 Ultra 550B (Free), Kat Coder Pro v2.5 (Free), Kilo Auto Frontier, Kilo Auto Balanced | |

## Recommendation tiers (for coding use)
- **No-risk, enable first (free keys, stable):** OpenRouter, NVIDIA NIM, Cloudflare, BytePlus ModelArk, Vertex AI (one-time $300), Gemini (AI Studio key).
- **Auto-Free aggregators (easiest to try):** Bazaarlink (Auto Free), API.airforce, Kilo Gateway — bật là có model xịn chạy free.
- **Risk Notice (unofficial OAuth, ban risk — NOT on main account):** Gemini CLI, Kiro AI. Models are top-tier but 9Router itself warns "account may be restricted or banned. Use at your own risk."
- **Already Ready:** OpenCode Free (no action needed).

## Gotchas
- Free-tier providers list their models as `<code>` chips (and, for aggregators like OpenRouter/Bazaarlink, also as `add <model>` buttons). Extract via the `browser_console` one-liner in SKILL.md — do NOT read full `browser_snapshot` (Kiro/Bazaarlink exceed 100+ AX elements).
- OpenCode Free behind `opencode` is the same `oc/*` pool the combos use — it is the only free-tier provider that is `noAuth` and pre-connected.
