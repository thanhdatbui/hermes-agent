# OmniRoute Advanced Capabilities & Strategies

OmniRoute (port `:20129`, codebase `C:\Users\Kibe\OmniRoute`, storage `~/.omniroute/storage.sqlite`) & 9Router (`:20128`) contain advanced routing, resilience, compression, and agent orchestration features.

## 1. Advanced Combo Strategies (19 Routing Strategies)
Beyond basic `priority` (waterfall spillover) and `round-robin`, OmniRoute supports specialized strategies:
- **`fusion` (Multi-LLM Ensemble):** Fans out requests in parallel to multiple models (e.g. Claude Opus + GPT-5.6 + Gemini Flash), then uses a Judge model to evaluate, cross-check, and synthesize a single consolidated answer. Ideal for critical architecture reviews or G1 Plan-Review.
- **`pipeline` (Step-by-Step Chain):** Chains models sequentially — e.g. Fast reasoning model (Gemini Flash / DeepSeek) analyzes context -> Heavy coding model (Claude / GPT) produces code.
- **`cache-optimized` & `session-affinity`:** Binds requests from the same session/conversation to the same provider account to maximize upstream KV Cache / Prompt Caching hits (saving 50-80% token costs and latency).
- **`reset-aware`:** Tracks quota reset timers per provider account and prioritizes depleting accounts closest to reset.
- **`cost-optimized` & `p2c` (Power-of-Two-Choices):** Selects targets dynamically based on real-time latency and token pricing.

## 2. Context & Token Optimization Subsystems
- **RTK + Caveman Compression (`compression_combos`, `compression_analytics`):** Real-time compression of verbose tool outputs (git diff, grep, XML, terminal logs), reducing 20–40% input tokens.
- **`semantic_cache`:** Embedding-backed semantic prompt cache. Matches semantically identical requests to return instant cached responses (0ms, 0 tokens).
- **`context_handoffs`:** Auto-triggers conversation summarization and context relay when reaching threshold (e.g. 85% context window), preventing hard context overflow.

## 3. Built-in MCP Server Hub (Model Context Protocol)
- **Scopes & Transports:** 110 tools across 33 scopes; transports: `stdio`, `SSE`, and `Streamable HTTP` (`/api/mcp/[plugin]/sse`, `/api/mcp/[plugin]/message`).
- **Integrated Modules:** GitHub, Notion, Obsidian, Persistent Vector/FTS Memory, RTK Tool Control, Proxy Registry.
- Allows any CLI client (Claude Code, Cursor, Codex, Hermes) to consume unified MCP tools directly via OmniRoute endpoint.

## 4. Agent-to-Agent (A2A) Protocol
- **JSON-RPC 2.0 A2A Engine (`a2a_tasks`, `agentic_conversations`):** Router-level orchestration for spawning, dispatching, and synchronizing sub-agent tasks concurrently.

## 5. Serverless Edge Proxy Deployments
- **1-Click Deploy:** Automated deployment to Cloudflare Workers (`cloudflare-deploy`), Deno Deploy (`deno-deploy`), and Vercel Edge (`vercel-deploy`).
- **Zero-Cost Egress Rotation:** Auto-generates rotating egress proxy pools to bypass IP rate-limits (429) and geoblocks without paid residential proxies.
- **3-Layer Proxy Hierarchy:** Account-level sticky proxy -> Provider-level pool -> Direct failover.

## 6. Multimodal & Media Endpoints
- **Audio/TTS/STT:** `/v1/audio/speech`, `/v1/audio/transcriptions`, `/v1/audio/voices` (ElevenLabs, Deepgram, MiniMax, Inworld).
- **Video & Image Gen:** `/v1/videos/generations`, `/v1/videos/edits`, `/v1/images/generations` (xAI Video, Luma, Kling, Flux).
- **Web Fetch & Search:** `/v1/search`, `/v1/web/fetch` exposed directly as unified API endpoints.
