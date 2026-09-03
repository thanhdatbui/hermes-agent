# Freebuff — CANNOT be a 9Router provider (verified 2026-08-13)

The user wanted Freebuff "nhét vào 9Router để bỏ cho Hermes chạy" (plug into 9Router so
Hermes routes through it). Investigation conclusion: **impossible** — Freebuff is an
agent-first product, not an OpenAI-compatible API endpoint.

## What Freebuff is (verified from source + web)
- `freebuff.com` / `freebuff.ai` — "the free coding agent". Repo `CodebuffAI/freebuff`
  (9.1k stars, very active). Free-only variant of the Codebuff CLI.
- Free model catalog: **GPT-5.6 Luna** (full), **DeepSeek V4 Pro** (full, default in full
  mode), **DeepSeek V4 Flash**, MiniMax M3, MiMo 2.5, GLM 5.2 (earned sessions), Gemini 3.1
  Flash Lite (specialist). No subscription / credits / API key; supported by text ads.
- Run as: `npm i -g freebuff` then `freebuff` in a project, or freebuff.com Web/Desktop/Cloud/Chat.

## Why it can't be a 9Router provider (from source grep)
- `SPEC.md`: Freebuff reuses `cli/` but strips paid features -> it's an **agent CLI that
  calls Freebuff's hosted backend** (`WEBSITE_URL` = codebuff.com). Requires **login**
  (`login-flow.ts`, `plain-login.ts`, API-key storage).
- No production HTTP server: the only `createServer().listen()` usages are in **test files**
  (release-server mocks). No Express/Fastify app serving `/v1/chat/completions`.
- `chat-completions` references in source are Freebuff's **internal cloud gate**, not a
  locally-exposed OpenAI-compatible endpoint.
- 9Router's "Custom Providers (OpenAI/Anthropic Compatible)" needs a base URL speaking
  `/v1/chat/completions` + API key. Freebuff exposes neither locally nor as a usable
  OpenAI-format endpoint.

-> Freebuff is a **standalone coding agent**, not a token/API source for 9Router. The FB
comment "Free 100tr token/ngay" is a paraphrase; real pitch = free & unlimited via text ads,
with session limits for VPN/unsupported regions (6 x 1h/day, DeepSeek V4 Flash + MiMo 2.5).

## Reusable technique — verify if ANY tool X can be a 9Router provider
When the user wants tool X plugged into 9Router/OmniRoute as a provider:
1. `git clone --depth 1 <repo>` (shallow; 75M is fine).
2. Grep for OpenAI-compatible server signals:
   - `chat/completions`, `from "openai"`, `@anthropic-ai/sdk`, `messages.create`
   - `listen(`, `express(`, `fastify`, `createServer` (EXCLUDE `*.test.ts` — tests fake servers)
   - `baseUrl`, login flow files (login = cloud-backed, not self-hostable)
3. If there's **no production OpenAI-compatible server** AND it **requires login/cloud** ->
   it's agent-only, NOT pluggable into 9Router. Tell the user to use it directly, not as a
   Hermes backend.
4. Confirmed pluggable providers expose an OpenAI-compatible `/v1` with a key
   (NVIDIA NIM, OpenRouter, Bazaarlink, API.airforce, Kilo Gateway — see
   `references/free-provider-signup-links.md`).

## User-facing takeaway
- Freebuff gives exactly the DeepSeek V4 Pro + GPT-5.6 Luna the user wanted, **for free**,
  but as its own agent — install `freebuff` and code directly; it does NOT feed Hermes via
  9Router.
- For Hermes-via-9Router, use NVIDIA NIM (DeepSeek V4 Pro) + OpenRouter as the free coding
  backbone. GPT-5.6 Luna free is the one gap (Freebuff-only, not exposable).
