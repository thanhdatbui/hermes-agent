---
name: procurement-intelligence-automation
description: "Use when automating tenders, MuaSamCong, or MCPs."
version: 1.0.0
author: Hermes Agent
tags: [procurement, tender, muasamcong, vneps, mcp, chatgpt-plugin, medical-bids]
---

# Public Procurement & Tender Intelligence Automation

Comprehensive guide for automating public e-procurement portals (e.g. Vietnam National E-Procurement System `muasamcong.gov.vn` / VNEPS), technical bid specification matching, crawler bots vs. MCP architectures, and client consulting discipline.

## 1. System Architecture & Portal Invariants

- **Public Portals (VNEPS / Mua Sắm Công):**
  - Search surfaces span 3 official scopes:
    1. **TBMT** (`notifyNo,bidName`): Thông báo mời thầu.
    2. **YCBG** (`ycbg`): Yêu cầu báo giá từ các cơ sở y tế / bệnh viện.
    3. **CGTTRG** (`cgttrg`): Chào giá trực tuyến rút gọn.
  - **Public Data Invariant:** Under national public bidding transparency laws, tender notices, quotation requests, and invitation dossiers (E-HSMT) are 100% public.

### Guest / Public Mode vs. Authenticated Session
- **Why Guest Mode is Superior for Recurring Watchdogs:**
  - Login sessions on modern government SSO portals (Keycloak/OAuth) have strict token lifespans (typically 24 hours). Expired sessions demand reCAPTCHA solving and SMS/TOTP 2FA.
  - Attempting to force automated login for routine crawlers creates constant fragility: 2FA prompts disrupt the client early in the morning, and reCAPTCHA increases proxy/solving costs.
  - **Rule:** Daily recurring tender monitoring MUST run in Guest/Public mode (`web/guest/...`). Authenticated login is ONLY required when submitting bids (E-HSDT) or accessing restricted corporate records.
  - **Honesty Rule:** Never claim to a client that a bot is running "directly logged into their account" when the crawler is operating in Guest mode. Explain clearly why Guest mode is more reliable and robust.

---

## 2. Crawler Bot (1-Way Push) vs. Private MCP Server (2-Way Interactive)

When clients request to "see data on their own app" or complain that Telegram reports are "hard to read / not interactive", clarify the two architectural paradigms:

| Feature | Crawler Bot (Telegram / Email) | Private MCP Server (ChatGPT Integration) |
| :--- | :--- | :--- |
| **Interaction** | 1-way Push (unidirectional) | 2-way Interactive Chat (bidirectional) |
| **User Experience** | Read-only text message summaries | Dynamic Markdown tables, deep queries, ad-hoc Q&A |
| **Execution Cost** | 0 LLM tokens (runs pure Python rule-engine) | Standard LLM chat tokens per prompt |
| **Automation** | Hands-free background cronjob at fixed hours | On-demand whenever user opens the ChatGPT mobile app |
| **Best Use Case** | Daily early-warning sentinel for new tenders | Ad-hoc technical dossier evaluation, BoQ breakdown |

### Decoupled CQRS Architecture & Dual-Cadence Data Freshness
- **Why VPS Must NOT Scrape Directly:**
  1. *WAF & SSL Blockade:* Portals block cloud datacenter IP ranges and trigger cipher negotiation issues (e.g. `SSL: DH_KEY_TOO_SMALL`); residential home connections browse cleanly.
  2. *SPA Resource Burden:* Dynamic client-rendered portals require Chrome CDP (1-2 GB RAM), which risks starving VPS production services (`doravo.net`).
  3. *ChatGPT Timeout (30-45s):* Multi-scope sweeps (42 queries) take ~2.8m, exceeding ChatGPT's strict timeout.
- **CQRS Separation:**
  - *Crawler (Home Machine):* Runs batch sweeps (08:00, 13:30, 17:00 ~2.5m/run) and on-demand pulls -> syncs clean data to VPS SQLite cache.
  - *Query Daemon (VPS FastMCP):* Reads SQLite in <50ms -> returns SSE stream to ChatGPT in <0.2s without timeout risk.
- **Freshness Cadence:** General queries read from the latest of 3 daily sweeps with timestamp labels; specific bid codes pull on-demand in 3-5 seconds.
- **Universal vs Tailored Scope:** Any public bid nationwide can be searched/parsed by code; specialized compliance rules (e.g. YCCMED 4 models) apply selectively to core product lines.

---

## 3. ChatGPT Plugin / MCP Configuration Pitfalls & Security

### Pitfall: Confusing Web Portal URLs with MCP Server Endpoints
- **Common Client Mistake:** Pasting the portal web address (e.g., `https://muasamcong.mpi.gov.vn`) into ChatGPT's `Connection / Server URL` field.
- **Error:** ChatGPT displays a red warning: *"Cannot automatically determine OAuth settings. Check server URL or enter settings manually."*
- **Root Cause:** A standard website is not an MCP (Model Context Protocol) server. ChatGPT expects a valid MCP SSE/JSON-RPC endpoint (e.g., `https://domain.com/mcp`).
- **Remedy:** Instruct the client to paste the exact MCP endpoint URL or provide a private server link.

### Competitive Intelligence Leaks via 3rd-Party MCP Brokers
- **Third-Party MCP Risk:** Commercial bidding software vendors (e.g., Anovatech / `dauthau.info`) provide public MCP connectors.
- **The Intelligence Trap:**
  - All prompts, technical queries, candidate tender IDs, and proprietary specs flow through the third-party MCP host before reaching OpenAI/Anthropic.
  - In competitive markets (e.g. medical devices, consumables), the critical asset is **tactical intent**: which hospital the company is targeting, what price thresholds are considered, and what technical weaknesses exist in the candidate bid.
  - Third-party data brokers can aggregate this search behavior into market intelligence reports and commercialize it to larger competitors.
- **Remedy:** Deploy a lightweight **Private MCP Server** on company-controlled infrastructure (VPS or local gateway) connected directly to internal clean data scrapers.

---

## 4. Technical Bid Specification Matching (Hybrid Architecture)

To minimize token costs and eliminate latency:
1. **Tier 1 (Fast-Filter Python Sentinel):**
   - Pure Python crawler scans daily keywords (14+ medical terms: `trocar`, `trocal`, `cannula`, `stapler`, `cắt khâu`, `băng ghim`, `bảo vệ vết mổ`).
   - If zero open packages exist, emit summary *"Hôm nay chưa có gói mới"* in $< 15\text{s}$ with 0 tokens.
2. **Tier 2 (Targeted Technical Evaluation):**
   - When an active package is detected, extract the BoQ / Chapter V specifications.
   - Evaluate against strict company product profiles (e.g. YCCMED Trocar: 100mm length, bladeless, unballooned, threaded body, models 5/10/12/15mm).
   - Flag explicit mismatches immediately (e.g., 8mm robotic trocars required for da Vinci systems vs standard laparoscopic trocars).

---

## 5. Client Communication Discipline

- **Direct & Actionable:** When drafting messages for the user to forward to business partners, keep the copy under 3–5 bullet points.
- **Immediate Fix First:** Lead with the 10-second fix (e.g., the exact URL to replace) before explaining long-term architecture.
- **No Jargon Overload:** Avoid technical buzzwords ("OAuth handshakes", "JSON-RPC", "headless chromium"); explain in terms of business value: *"Server riêng bảo mật 100% không sợ lộ thầu cho bên thứ ba, hiển thị trực tiếp trên app ChatGPT cho anh dễ coi."*
- **Ready-to-Copy Delivery & Zero Unsolicited Architecture Pitch:**
  - When the user demands message drafts (*"Đưa tn đây"*, *"Soạn tn đi ngắn gọn thôi"*), deliver the clean text block immediately, strictly under 4–5 lines without verbose preamble, conversational meta-commentary, or fluff, ready for instant forwarding.
  - **Do NOT pitch unrequested architecture pivots in forwardable client copy:** If the user asks for a simple fix instructions draft for a third-party setup, NEVER bundle an unsolicited pitch ("em dựng server riêng cho anh") into that forwardable draft unless the user explicitly directed you to suggest it. When the user asks *"Chứ k gợi ý ổng dựng cái sever gì đó à"*, clarify and propose the architecture separately or provide the targeted message draft upon request, keeping the client copy clean and focused.

## References

- `references/decoupled-cqrs-bidding-mcp-and-freshness-strategy.md` — Decoupled CQRS architecture (residential IP crawler vs cloud VPS FastMCP query daemon), why VPS must not scrape government portals directly (WAF/SSL/RAM/timeout limits), dual-cadence data freshness (3 golden batch sweeps at 08:00, 13:30, 17:00 + 3-5s on-demand fetch), and universal vs tailored scope.
- `references/desktop-gui-mcp-integration-and-cwd-pitfall.md` — Desktop GUI MCP integration (Antigravity IDE & Claude Desktop), stdio CWD relative path trap (preventing agentic runaway recursive disk searches), and per-project permission allowlist vs global server registry.
- `references/mcp-configuration-and-intelligence-security.md` — Diagnostics for ChatGPT plugin/MCP URL errors, competitive intelligence security analysis (3rd-party vs private MCP), and partner messaging templates.
- `references/private-mcp-server-architecture-and-sse-specs.md` — Reverse-engineered ChatGPT MCP SSE/HTTP transport specifications, FastMCP streamable_http_app lifespan pattern (mcp v1.28+), dual stdio/HTTP transport, Antigravity CLI end-to-end verification, OAuth discovery metadata, Nginx zero-buffering stream proxy rules, and FastMCP SQLite decoupling architecture.

