# Free Provider Signup / Get-API-Key Links (verified 2026-08-13)

The user repeatedly asks for the literal signup links to create free API-tier providers
and add them to 9Router so Hermes routes through them. These are the **"Get API Key"**
external links pulled live from each provider's 9Router detail page
(`/dashboard/providers/<slug>` → `open_in_new Get API Key`). All five are
OpenAI-compatible → Add Connection (API key) in 9Router → Hermes uses them.

| Provider | Signup / Get API Key URL | Free model you get | Priority |
|---|---|---|---|
| **NVIDIA NIM** | https://build.nvidia.com/settings/api-keys | **DeepSeek V4 Pro/Flash** + Nemotron 3 Ultra (free for NVIDIA Developer Program members) | **1st** |
| **OpenRouter** | https://openrouter.ai/settings/keys | 27+ free models, 200 req/day (DeepSeek V4 Pro via cheap upstream e.g. Baidu) | **1st** |
| **Bazaarlink** | https://bazaarlink.ai/ | Auto Free + Claude Opus 4.7 / GPT-5.5 / Grok 4.3 | 2nd |
| **API.airforce** | https://api.airforce/ | Claude 3.7 Sonnet (Free), Kimi K2.6, Gemini 2.5 Flash | 2nd |
| **Kilo Gateway** | https://kilo.ai/dashboard?tab=apiKeys | Nemotron 3 Super/Ultra (Free), Kat Coder Pro v2.5 | last |

## How to pull the URL yourself (when a provider is added later)
1. `browser_navigate` to `http://127.0.0.1:20128/dashboard/providers/<slug>` (login 123456).
2. `browser_console`:
   ```js
   JSON.stringify(Array.from(document.querySelectorAll('a')).map(a=>({t:a.textContent.trim().replace(/\s+/g,' '),h:a.href})).filter(l=>l.h&&l.h.startsWith('http')&&!l.h.includes('127.0.0.1')))
   ```
3. The `open_in_newGet API Key` entry is the signup/key URL.

## Add to 9Router
After signup → copy API key → Providers → provider card → **Add Connection** → paste key →
**Test**. Green = Hermes can route through it. Do NOT add Gemini/Gemini CLI/Vertex AI
(free tier there is weak for coding per user's bar).

## User's coding bar (2026-08-13)
Wants free models ~ DeepSeek-v4-flash / GPT-5.6-Luna caliber, **ignores Gemini** (deems it
weak at code). 9Router free API tier that meets the bar: NVIDIA NIM (DeepSeek V4 Pro/Flash)
+ OpenRouter (DeepSeek V4 Pro). GPT-5.6 Luna is ONLY free via Freebuff (see
`references/freebuff-9router-compatibility.md`) and is NOT exposable to 9Router — substitute
DeepSeek V4 Pro (NVIDIA NIM) as the top free coding model in 9Router.
