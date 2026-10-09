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

## 7. ChatGPT-Web Emulated Tool Calling & Agent Capabilities
- **Architecture vs Codex Desktop Harness (`codex-chatgpt-web`):**
  - Tool ngoài (`codex-chatgpt-web`) dùng app Electron gắn trình duyệt ảo + MCP Tunnel vào web UI (chậm, 1 acc, dễ nghẽn DOM).
  - OmniRoute (`chatgpt-web` provider) là **Headless Reverse-Proxy**: bắn HTTP/SSE trực tiếp vào backend OpenAI với Auth Token + gắn cố định MobiProxy 4G 1-1 qua pool 17+ tài khoản.
- **Function / Tool Calling Support (`#5240` / `#7679`):**
  - `chatgpt-web` hỗ trợ đầy đủ OpenAI tool-calling contract qua cơ chế prompt-emulation shim (injected `<tool>` contract + parse thẻ `<tool>{...}</tool>` thành `tool_calls`).
  - Đã verify thực tế 2-turn conversation: Model trả về `tool_calls` hợp lệ (ví dụ `[{"id": "cgpt-...", "function": {"name": ...}}]`) và xử lý tiếp kết quả từ role `tool`.
  - **Khả năng làm Fallback Worker:** Hoàn toàn có "tay chân" đầy đủ để làm fallback khi các provider chính (Gemini Pool / Claude) bị nghẽn quota, cả ở tầng Hermes (`fallback_providers` trong `config.yaml`) lẫn tầng router combo (`omni-worker` trong OmniRoute).

## 8. ChatGPT Web Multi-Account Pool & Round-Robin Operational Rules
- **Pool Architecture (`chatgpt-web-pool`):**
  - Quản lý pool 12+ tài khoản LIVE chạy chiến lược `round-robin`, `stickyRoundRobinLimit: 1`, `failoverBeforeRetry: true`.
  - Thay vì để combo gọi model đơn lẻ `chatgpt-web/gpt-5.6-sol-high` (bị dồn tải vào 1 acc theo Priority đến khi nghẽn), gói toàn bộ tài khoản thành combo `chatgpt-web-pool` với từng `connectionId` cụ thể (`kind: "model"`).
  - Tích hợp vào Combo `review` (Tier 0: `combo-ref: chatgpt-web-pool`) và Combo `omni-worker` (Tier 2: Fallback sau `ag-gemini-pool-3`).
- **Phân biệt Lỗi Quota (502) vs Sentinel / Cloudflare (403) vs Ban:**
  - **429 / 502 `You've hit your limit`:** Tài khoản chỉ chạm trần quota 5h của OpenAI Web, KHÔNG PHẢI BỊ BAN. Khi hết chu kỳ rolling 3–5h, quota tự động hồi phục 100%.
  - **403 Sentinel Turnstile:** Khi bị spam dồn dập sau khi dính limit 502, Cloudflare / Sentinel yêu cầu captcha. OmniRoute gắn cờ `test_status: 'banned'` nội bộ để bảo vệ IP, và cookie session có thể chuyển sang `expired`.
  - **Cách xử lý acc bị báo 'banned' do expired session:** Mở profile GPM tương ứng, đăng nhập lại chatgpt.com và cập nhật session cookie mới vào `provider_connections`, không vội kết luận tài khoản bị khóa vĩnh viễn.
- **SQLite Hot-Patch Invariant:**
  - Khi cập nhật `data` JSON trong bảng `combos` trực tiếp trên SQLite (`~/.omniroute/storage.sqlite`), nhớ xuất bản snapshot dự phòng ra `combos_backup.json` để tránh mất dữ liệu khi restart hoặc migration.


