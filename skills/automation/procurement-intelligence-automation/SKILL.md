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

### Transitioning from Push Bot (Telegram) to Private MCP (ChatGPT)
- **Shared Bot Identity Pitfall (Doravo Bot / `doravo_stock_alert_bot`):**
  - In this infrastructure, the Telegram bot identity (`doravo_stock_alert_bot`, config `doravo_bot_config.json`) was historically shared across two distinct domains:
    1. *Tender Watchdog:* `muasamcong-daily-tender-watchdog` (cron `84cc7515bb88`, 08:00 daily), pushing medical tender alerts to partner chat `-1004418200690`.
    2. *Webshop Stock Checklive:* `daily-manual-stock-checklive` (cron `1cb63d617582`, 07:00 daily), reporting manual inventory on `doravo.net`.
- **Lifecycle Transition Rule:**
  - When the partner/client migrates to the Private MCP Server on ChatGPT (`https://doravo.net/mcp`), the daily Telegram push bot (`muasamcong-daily-tender-watchdog`) should be paused via `cronjob(action='pause', job_id='84cc7515bb88')` to prevent notification clutter in the group.
  - **Fail-Safe Disambiguation:** When requested to "tạm dừng bot doravo ở tele", pause the tender watchdog (`muasamcong-daily-tender-watchdog`) first, but verify before touching `daily-manual-stock-checklive` to keep ecommerce inventory operations intact.

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
- **Claude CLI Architecture & Plan Gate:** For non-trivial crawler pipelines or data sync modules, user requires Claude CLI (`claude -p "..."`) to author the implementation plan first before coordinator/workers execute code surgery.
- **Gate 6 Visual Proof Invariant (Deliverable vs Upstream Source):** When proving an MCP server works, NEVER substitute a screenshot of the source portal (e.g. Mua Sắm Công). That only proves the crawler is open, not that the MCP server is healthy. The visual evidence MUST directly capture the deliverable: the MCP server's HTTP 200 text/event-stream handshake, tool execution output, or a live diagnostic dashboard. Always verify with `browser_vision` before emitting `MEDIA:<path>`.

---

## 3. ChatGPT Plugin / MCP Configuration Pitfalls & Security

### Pitfall: Confusing Web Portal URLs with MCP Server Endpoints
- **Common Client Mistake:** Pasting the portal web address (e.g., `https://muasamcong.mpi.gov.vn`) into ChatGPT's `Connection / Server URL` field.
- **Error:** ChatGPT displays a red warning: *"Cannot automatically determine OAuth settings. Check server URL or enter settings manually."*
- **Root Cause:** A standard website is not an MCP (Model Context Protocol) server. ChatGPT expects a valid MCP SSE/JSON-RPC endpoint (e.g., `https://domain.com/mcp`).
- **Remedy:** Instruct the client to paste the exact MCP endpoint URL or provide a private server link.

### Operator Testing Discipline: Remote URL vs Local stdio Testing Trap
- **The Core Operator Frustration:** When an operator asks to test the MCP server on their desktop app (Antigravity, Claude Desktop) before delivering to a non-technical client, never force them into local stdio configuration (editing `claude_desktop_config.json`, hunting `python.exe` paths, relative CWD bugs) if their goal is to verify the client-side remote URL experience.
- **The Reality of Clients:**
  1. *ChatGPT Mobile / Web (Paid Plus/Team Only):* OpenAI restricts Developer Mode / Custom MCP Connectors to paid subscribers (Plus, Team, Enterprise). Free ChatGPT accounts cannot add custom MCP servers.
  2. *Testing Remote URLs on Desktop (Zero JSON Editing):* Antigravity CLI natively supports remote HTTP/SSE endpoints:
     ```bash
     agy mcp add <server_name> <https://domain.com/mcp>
     ```
     This allows the operator to test the exact remote production URL over the internet without running local Python subprocesses or editing JSON configuration files.
  3. *Claude Desktop:* Natively only supports local `stdio` subprocesses configured via JSON. Do not recommend Claude Desktop for rapid verification of remote HTTPS endpoints.
- **Verification Workflow:** Deploy to VPS -> verify Nginx reverse proxy and FastMCP DNS rebinding settings -> test remote URL via `agy mcp add <name> <URL>` -> deliver copy-paste instructions to the client.

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
   - **Evaluator Audit Invariants (Claude Review Hardening):**
     * *Word-boundary checks:* Use `(?<!\d)8\s*mm\b` instead of raw substring to prevent false UNFIT on `18mm` trocars.
     * *Negation clause handling:* Check preceding window for negative phrasing (`không yêu cầu robot`, `không dùng dao`) to avoid reversing legal intent.
     * *No Blind FIT on Missing Sizes:* If document mentions trocar generally without specifying 5/10/12/15mm, return status `NEEDS_REVIEW` (provisional models attached) rather than claiming full compatibility.
     * *Multi-Lot (Phân Lô) Isolation:* Extract structured `technical_specs` from `raw_json` rather than concatenating full tender blobs, preventing Lot 2/3 disqualifiers (robot, 8mm, blade) from poisoning Lot 1 trocar bids.
     * *SQLite WAL Production Sync Invariant:* Flush WAL with `PRAGMA wal_checkpoint(TRUNCATE)` locally; stop service and remove companion `-wal`/`-shm` files on VPS before SFTP upload to avoid SQLite serving stale cache pages.
     * *Null-Safe Ingestion:* Use `data.get("scope") or "Trong nước"` and guard against null/empty `bid_code` to prevent `sqlite3.IntegrityError` during bulk historical syncs.
     * *Date Normalization & Freshness SLA:* Convert all `DD/MM/YYYY` to ISO `YYYY-MM-DD` for SQLite `ORDER BY`, dynamic expiry check (`deadline_date >= date('now')`), and return `data_as_of` / `get_cache_status` for user auditability. (See `references/fastmcp-production-hardening-and-evaluator-audit.md`).

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
- `references/desktop-gui-mcp-integration-and-cwd-pitfall.md` — Desktop GUI MCP integration (Antigravity IDE & Claude Desktop), stdio CWD relative path trap (preventing agentic runaway recursive disk searches), per-project permission allowlist vs global server registry, and ChatGPT Free vs Plus tier gating for MCP testing.
- `references/offline-vps-mcp-deployment-and-remote-url-testing.md` — Offline Python FastMCP deployment on firewalled VPS (cross-platform manylinux wheel bundling without outbound internet), FastAPI vs Starlette compatibility trap (pinning `starlette==0.38.6`), safe Nginx reverse proxy placement before `listen 443 ssl;` in CMS monoliths, and testing remote URLs directly via `agy mcp add <name> <URL>` without editing JSON.
- `references/mcp-configuration-and-intelligence-security.md` — Diagnostics for ChatGPT plugin/MCP URL errors, competitive intelligence security analysis (3rd-party vs private MCP), and partner messaging templates.
- `references/private-mcp-server-architecture-and-sse-specs.md` — Reverse-engineered ChatGPT MCP SSE/HTTP transport specifications, FastMCP streamable_http_app lifespan pattern (mcp v1.28+), dual stdio/HTTP transport, Antigravity CLI end-to-end verification, OAuth discovery metadata, Nginx zero-buffering stream proxy rules, and FastMCP SQLite decoupling architecture.
- `references/fastmcp-production-hardening-and-evaluator-audit.md` — FastMCP production hardening behind Nginx: resolving 421 Misdirected Request (DNS rebinding protection & TransportSecuritySettings), avoiding 403 Forbidden via Nginx `^~` location priority, evaluator string matching hazards (regex word boundary, negation detection for robot/blade, NEEDS_REVIEW vs false FIT), ISO date normalization for SQLite ORDER BY, dynamic expiry gates, and `data_as_of` SLA transparency.
- `references/crawler-ingest-and-vps-atomic-sync-pipeline.md` — Automated crawler ingest & VPS atomic SQLite sync pipeline: safe standalone snapshot creation via SQLite Backup API (WAL checkpoint + DELETE journal mode), Row Count Guard preventing empty/truncated overwrite of VPS cache, atomic swap with companion `.prev` rollback, and Uvicorn health verification.
- `references/shared-host-dependency-audit-and-backup-parity.md` — Shared host dependency audit & backup parity protocol: 4-vector dependency audit (network proxy routing, client MCP vs internal farm scrapers, shared bot identities, notification disabling vs outbound 443 sync decoupling) and preventing the "Code in Git != Live Database" backup hazard before server decommission.

