# Architecture Comparison: 9Router vs OmniRoute vs Cockpit Tools vs CLIProxy

## 1. Overview & Port Mapping

| Component | Port | Process Name | Binary / Stack | Primary Purpose |
|---|---|---|---|---|
| **OmniRoute** | `20129` | `node.exe` | Next.js / Node.js | Primary multi-account router for Hermes (Antigravity pool, ChatGPT Web pool, combos) |
| **9Router** | `20128` | `node.exe` | Next.js / Node.js (same core as Omni) | Standalone LLM proxy, secondary router, Antigravity OAuth, OpenRouter |
| **Cockpit Tools** | `19530` (WS) | `cockpit-tools.exe` | Desktop GUI application | Account manager for Codex/ChatGPT accounts, proxy assignment per profile |
| **CLIProxy (Cockpit Sidecar)** | `60818` | `cockpit-cliproxy.exe` | Go binary (LuisPater `CLIProxyAPI` v7.2.66) | Local OpenAI-compatible REST API sidecar embedded inside Cockpit Tools |

---

## 2. Cockpit Tools vs CLIProxy Relationship

- **"Vỏ và Ruột" (Shell and Engine):**
  - Cockpit Tools (`cockpit-tools.exe`) is the desktop UI shell.
  - Inside `C:\Users\Kibe\AppData\Local\Cockpit Tools\`, Cockpit embeds `cockpit-cliproxy.exe`, which is an exact rename of `cli-proxy-api.exe` (CLIProxyAPI Go binary).
  - When Cockpit launches, it automatically spawns `cockpit-cliproxy.exe` as a child process listening on `localhost:60818` (`gatewayMode: sidecar`).
- **No Relationship with GPMLogin:**
  - Cockpit Tools has **zero code integration** with GPMLogin.
  - GPMLogin is solely an antidetect browser used manually to complete OAuth callbacks if accounts are logged in there. Cockpit itself is completely standalone.
- **Cockpit Egress Proxy Flaw & Pitfalls (CRITICAL ANTI-PATTERN):**
  - **No Per-Account Raw Proxy:** Cockpit's Go sidecar (`cockpit-cliproxy.exe`) only supports a single global `proxy-url`. It cannot route individual accounts through distinct egress proxies.
  - **`PROXY_RESOURCE_INVALID` Crash:** Injecting raw HTTP/SOCKS5 proxies (`http://mobi1:...@test.taadaa.click:5101`) into account records triggers `PROXY_RESOURCE_INVALID` and crashes the API service because Cockpit expects Clash/Mihomo catalog nodes.
  - **IP Leakage & `token_revoked` (401):** When Cockpit sends requests without proxy, traffic leaks through the host's direct IP (`1.53.55.190`). Since GPM profiles were authenticated through separate mobile 4G proxies (`test.taadaa.click:5101-5138`), OpenAI detects the direct IP jump and instantly revokes OAuth tokens (`401 token_revoked`).
  - **Do NOT Cluster Accounts Under 1 Global Proxy:** Pooling multiple free ChatGPT accounts through a single global proxy clusters traffic and causes OpenAI to ban the entire pool.
  - **9Router Architectural Advantage:** 9Router supports per-account proxy attachment via `proxyPools` and `providerConnections.data.providerSpecificData.proxyPoolId`. Each account dispatch uses its exact dedicated proxy, isolating IPs completely.

---

## 3. Phân Biệt Khái Niệm "Proxy" trong OmniRoute/9Router vs Network Egress Proxy (CRITICAL)

- **AI Reverse Proxy (Layer 7 API Gateway):**
  - Trong Dashboard OmniRoute/9Router, các mục `Proxy`, `CLIProxyAPI`, `9Router`, `Mux`, `Bifrost` là các **Cổng chuyển tiếp API AI** (AI Reverse Proxy).
  - Mục đích: Đóng vai trò máy chủ trung gian giả lập OpenAI/Claude API, dịch giao thức giữa các nhà cung cấp AI và chia tải/chống rate limit cho API keys.
  - **KHÔNG PHẢI** là network tunnel (Layer 3/4 SOCKS5/HTTP tunnel) để fake IP mạng hay đổi IP egress của máy duyệt web sang US.
- **Proxy Pools trong Database OmniRoute/9Router:**
  - Bảng `proxyPools` trong database chỉ lưu trữ danh sách proxy do chính User import vào để gắn cho từng tài khoản gọi LLM.
  - Bản thân OmniRoute/9Router **hoàn toàn không cấp sẵn proxy US miễn phí** cho duyệt web.

---

## 4. Model Compatibility & Constraints

### A. Model `gpt-6-luna` & `gpt-5.6-luna`
- **Cockpit Tools (:60818):** **WORKS NATIVELY.**
  - `gpt-6-luna`: Thế hệ GPT-6 mới nhất, hoạt động trơn tru với tài khoản Free (200 OK, latency ~8s–22s, dynamic reasoning 42–271 tokens, tiêu thụ quota rất ít).
  - `gpt-5.6-luna`: Sub-second response, 0% quota consumed trên Free/Plus accounts.
- **OmniRoute & 9Router Catalog Reality:**
  - Cả 9Router (`GET /api/models`) và OmniRoute (`open-sse/config/providers/registry/codex/index.ts`) trong catalog tích hợp sẵn của provider `codex` (`cx`) hiện tại **MỚI CHỈ HỖ TRỢ ĐẾN DÒNG 5.6** (`cx/gpt-5.6-luna`, `cx/gpt-5.6-terra`, `cx/gpt-5.6-sol`).
  - **CHƯA CÓ `gpt-6-luna`** trong catalog mặc định của 9Router/OmniRoute. Muốn dùng `gpt-6-luna` qua 9Router, bắt buộc phải add Cockpit làm Custom OpenAI Provider (`http://127.0.0.1:60818/v1`).

### A.1. Benchmark: `gpt-6-luna` vs `gpt-5.6-terra` (Dữ liệu thực tế 51.600 request)
- **`gpt-6-luna` (Khuyên dùng cho Worker/Automation):** Latency 8s–22s, 100% success rate, sinh reasoning tokens linh hoạt theo độ khó, code sạch chuẩn PEP8 có type hints.
- **`gpt-5.6-terra` (Kiến trúc / Planning sâu):** Suy luận CoT sâu hơn (353 reasoning tokens/req), nhưng latency rất cao (30s–45s) và tỷ lệ tạch lịch sử 33.6% do timeout khi context lớn.
- **Quy tắc kiểm tra Model Support của Router khi chưa có Connection (CRITICAL):**
  - Khi kiểm tra 9Router hay OmniRoute có hỗ trợ một model cho một provider hay không, **TUYỆT ĐỐI KHÔNG chỉ nhìn bảng connection/database trống rồi vội kết luận là không hỗ trợ**.
  - BẮT BUỘC kiểm tra **Model Catalog của Router**: trên 9Router là `GET http://127.0.0.1:20128/api/models` (hoặc `/api/catalog`), trên OmniRoute là file registry định nghĩa model (`open-sse/config/providers/registry/codex/index.ts`).

### B. Model `gpt-6-sol` / `gpt-5.6-sol` & Huyền thoại "Sol 6.1"
- **Không tồn tại dòng "Sol 6.1" hay "gpt-6.1*":** Dòng OpenAI Codex và binary `cockpit-cliproxy.exe` chỉ có dòng 5.6 và dòng 6.0 (`gpt-6-sol`, `gpt-6-luna`, `gpt-6-astra`). Tên "Sol 6.1" thực chất là alias tự đặt trong cộng đồng.
- **Cockpit Tools (:60818) với Acc Free:** **FAILS (HTTP 400 / 503).**
  - Upstream OpenAI hard-block: `"The 'gpt-6-sol' / 'gpt-5.6-sol' model is not supported when using Codex with a ChatGPT account."`
  - Nếu cố gọi với context lớn (~25k tokens), chi phí Sol cao gấp hàng chục lần Luna, trừ 4–5% quota/lần và dẫn tới OpenAI revoke token (`token_revoked` / `auth_unavailable`).
- **9Router (:20128):** **WORKS.**
  - Combo `gpt-5.6-sol` is configured with `['cx/gpt-5.6-sol', 'ag/claude-opus-4-6-thinking']`.
  - When Codex fails, 9Router automatically falls back to **Antigravity Claude Opus Thinking**, delivering high-quality Sol High judgment in < 15s.

### B.1 ChatGPT Web Pool Support: OmniRoute vs 9Router
- **OmniRoute (:20129):** **HỖ TRỢ NATIVE `chatgpt-web`.**
  - Có driver nội bộ quản lý pool tài khoản session web (`chatgpt-web-pool`), xoay vòng qua 12 accounts ChatGPT Web live bằng access token / backend-api trực tiếp (`https://chatgpt.com/backend-api/conversation`).
- **9Router (:20128):** **KHÔNG HỖ TRỢ NATIVE `chatgpt-web`.**
  - Trong codebase router (`chunks/4953.js`), 9Router KHÔNG có provider slug `chatgpt-web`. Nó chỉ hỗ trợ `openai` (Official API Key), `openai-compatible` (Custom Base URL), và `codex` (Codex CLI OAuth `chatgpt.com/backend-api/codex/responses`).
  - Web scraping duy nhất 9Router hỗ trợ là `grok-web` và `perplexity-web` (Cookie SSO).
  - Không thể cấu hình trực tiếp tài khoản ChatGPT Web vào 9Router để làm fallback độc lập nếu không qua bridge proxy (OmniRoute làm upstream trung gian). Muốn fallback độc lập khi OmniRoute chết, 9Router phải dùng pool `antigravity` (Claude Opus 4.6 Thinking / Gemini) hoặc `deepseek`.

### C. Gemini Antigravity & Reasoning Configuration (`gemini-3.7-flash-tiered`)
- **OmniRoute (:20129):** Hosts the primary 22-account pool for `omni-worker` (`ag-gemini-pool-3`).
- **9Router (:20128):** **ACTIVE FALLBACK.** Contains 7 Antigravity OAuth accounts (including Google PRO `thanhdatbui19951` & `jinrakal`).
  - **Reasoning Architecture:** Calling `gemini-3.8-flash-medium` directly results in upstream 404 from Google Antigravity. In 9Router core (`chunks/915.js`), dynamic reasoning levels are mapped through `gemini-3.7-flash-tiered` via `generationConfig.thinkingConfig.thinkingLevel: ["high", "medium", "low"]` (defaulting to medium).
  - **Combo `omni-worker`:** Created in 9Router's SQLite DB (`combos` table) pointing to `["ag/gemini-3.7-flash-tiered"]`.
  - **Hermes Mapping:** `providers.9router.models.omni-worker` configured with `model_id: omni-worker` and `reasoning_effort: medium`. Verified live with HTTP 200 response in ~0.4s.
- **Cockpit Tools (:60818) — Antigravity Tab vs API Reality:**
  - **In GUI:** Cockpit Tools has an "Antigravity" tab that manages Google accounts (`thanhdatbui19951@gmail.com`, `jinrakal@gmail.com`) with PRO quotas for Gemini and Claude.
  - **In API (:60818):** Cockpit's local API sidecar (`cockpit-cliproxy`) is strictly bound to `codex_local_access.json`. It **DOES NOT expose Gemini or Claude** to external callers.
  - **Calling Gemini on :60818 returns `HTTP 404 Not Found`:** Antigravity credentials in Cockpit are solely for IDE injection/internal UI, not an external API gateway. Cockpit cannot serve Gemini to Hermes.

### D. Standalone CLIProxyAPI (LuisPater WinGet package)
- **Binary:** `C:\Users\Kibe\AppData\Local\Microsoft\WinGet\Packages\LuisPater.CLIProxyAPI_Microsoft.Winget.Source_8wekyb3d8bbwe\cli-proxy-api.exe` (v7.2.66).
- **Capabilities:** CLI protocol translator supporting `-antigravity-login`, `-claude-login`, `-codex-login`, and `-tui`.
- **State on Host:** Installed but **inactive/not running** (no listening port; token in `~/.cli-proxy-api/` expired). It lacks 9Router's combo routing and load balancing.

### E. 9Router SSE Streaming Quirk
- 9Router routes `gpt-5.6-sol` to `ag/claude-opus-4-6-thinking`.
- By default or when streaming, 9Router emits Server-Sent Events (`data: {...}`). Scripts querying 9Router programmatically must parse SSE chunks line-by-line rather than assuming a single JSON payload to avoid `JSONDecodeError`.

---

## 5. Fallback Hermes → 9Router Status: ENABLED & VERIFIED

**Status:** Hermes `fallback_providers` is configured and active.
```yaml
fallback_providers:
  model: omni-worker
  provider: 9router
```
- **Live Smoke Test:** Verified calling `http://127.0.0.1:20128/v1/chat/completions` with `model: omni-worker` successfully routes to `ag/gemini-3.7-flash-tiered` with `reasoning_effort: medium` and streams back response in ~0.4s.
- **Failover Behavior:** When OmniRoute (:20129) experiences rate limits, connection drops, or timeouts, Hermes automatically diverts traffic to 9Router (:20128) without session crashes.

---

## 6. Architectural Topology

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        LAYER 1: GATEWAY / ROUTER                       │
│                                                                        │
│   Hermes Agent                                                         │
│        ├── [PRIMARY]  ──►  OmniRoute (:20129)                          │
│        └── [FALLBACK] ──►  9Router (:20128) [Warm Standby]             │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
                                     ▼ Downstream Providers
┌────────────────────────────────────────────────────────────────────────┐
│                     LAYER 2: TOKEN PROVIDERS & SIDECARS                │
│                                                                        │
│   ├── Antigravity Direct OAuth (Google Cloud Code Assist)              │
│   ├── Cockpit Tools / CLIProxy (:60818) [Codex gpt-5.6-luna only]      │
│   └── OpenRouter / ChatGPT Web Pool                                    │
└────────────────────────────────────┴───────────────────────────────────┘
```
