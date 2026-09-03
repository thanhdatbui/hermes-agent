# OmniRoute — sibling local AI gateway (localhost:20129)

OmniRoute v3.8.39 is a **separate product** from 9Router, also running locally on this
machine. The user runs both and often asks to check them together. It is a Next.js app
with a much larger feature set (Compression engines, Agent Bridge, Combo Studio, Traffic
Inspector, Cloud Agents…) than 9Router.

## Access
- URL: `http://localhost:20129/` → redirects to `/login`.
- **Password: `CHANGEME`** (the app's own default; it prints "Default password: CHANGEME
  (unless INITIAL_PASSWORD was set)" on the login page). The user's verbal "CHANGME" was
  wrong — use `CHANGEME`.
- After login the session cookie persists for the browser session.

## Browser-driving pitfalls (verified 2026-08-13)
- **First load shows a blank dark page / `about:blank`.** The SPA does not render on the
  first navigation. Fix: re-navigate explicitly to `http://localhost:20129/login`, then it
  renders fully (heading "Sign in", password field, "Continue" button).
- **Provider detail pages render as skeleton/loading and NEVER show the model list** in the
  headless browser. The `main` element's `innerText` stays at the header only (13 lines);
  `browser_vision` confirms two grey skeleton cards. This is because model lists are fetched
  from a backend that doesn't resolve in this context. **Do NOT rely on detail pages** — read
  the **list page** instead (`/dashboard/providers`), where every provider card is an `<a>` with
  text like `Name (Free)No connections` and `href="/dashboard/providers/<slug>"`.
- **`browser_console` `fetch()` is BLOCKED** by a safety guard ("tried to use sensitive
  browser JavaScript primitive (network request)"). You cannot pull the provider API JSON from
  the console. Extract from the rendered DOM via `browser_console` (DOM reads are allowed), or
  use `browser_snapshot` / `browser_vision`.

## Free providers inventory (verified 2026-08-13)
OmniRoute surfaces free providers two ways: a "Free Tier" category and a "Free Tier Providers"
section ("All providers with free tier (also shown in their native category)"). Unique free
providers found on the list page (slug → type):

| Provider | Slug | Type |
|---|---|---|
| Gemini Web (Free) | `gemini-web` | Web-UI free (gemini.com) — **user ignores gemini** |
| HuggingChat (Free) | `huggingchat` | Web-UI free (open models) |
| LMArena (Free) | `lmarena` | Arena benchmark chat |
| Phind (Free) | `phind` | Web-UI, coding-oriented search/LLM |
| Qwen Web (Free) | `qwen-web` | Web-UI free (Qwen) |
| t3.chat (Pro/Free) | `t3-web` | Web-UI chat |
| ZenMux Free (Web) | `zenmux-free` | Web-UI mux |
| Chipotle Pepper AI (Free) | `chipotle` | Web-UI |
| FreeModel.dev | `freemodel-dev` | Free API-model aggregator |
| MiMoCode (Free) | `mimocode` | API free — Xiaomi MiMo coding model |
| OpenCode Free | `opencode` | API free — same `oc/*` models as 9Router |
| The Old LLM (Free) | `theoldllm` | Web-UI |
| Veo AI Free | `veoaifree-web` | **Video** gen (not chat/code) |
| FreeAIAPIKey | `freeaiapikey` | Free API-key aggregator |

## Critical distinction vs 9Router free tier
OmniRoute's free tier is **mostly free WEB-UIs** (it proxies your requests to the free web
chat interfaces of gemini.com / qwen.com / huggingchat / phind / lmarena / t3.chat…). These:
- are **web-scraped, rate-limited, and less stable** than API free tiers;
- do **NOT expose selectable models like `deepseek-v4-flash` or `gpt-5.6-luna`** — those are
  API-tier models that simply aren't available through a web-UI proxy.

So for the user's coding bar ("~ DeepSeek v4 flash / GPT 5.6 Luna, not weak like Gemini"),
**OmniRoute free does NOT meet it** except for the few API-style ones:
- **OpenCode Free** — same `oc/deepseek-v4-flash-free`, `oc/nemotron-3-ultra-free`, etc. as 9Router.
- **MiMoCode (Free)** — MiMo is a real coding model.
- **FreeModel.dev / FreeAIAPIKey** — aggregators that may surface free API models (verify live).

**Recommendation pattern:** for API-free coding at DeepSeek-v4-flash / GPT-5.6-Luna caliber,
use **9Router's** free tier (NVIDIA NIM, OpenCode Free, Bazaarlink, Cloudflare, OpenRouter).
Treat OmniRoute free as a **backup web channel** when API quotas are exhausted, not a
replacement.

## Comparing the two gateways
- 9Router free = API free tiers (real model selection, key/NoAuth/OAuth).
- OmniRoute free = mostly Web-UI free proxies (no API-model selection, rate-limited).
- Exact model lists for OmniRoute free providers could NOT be confirmed this session (detail
  pages skeleton-load). Confirm by reading the provider card text on `/dashboard/providers`
  (the `(Free)` tag + type) rather than detail pages.
