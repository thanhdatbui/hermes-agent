# Decoupled CQRS Architecture for Public Procurement MCP & Data Freshness Strategy

## 1. Why VPS Must NOT Scrape Government Portals Directly
When integrating public bidding data (e.g. Vietnam National E-Procurement System `muasamcong.gov.vn`) into a ChatGPT MCP Server, attempting to perform live web crawling directly from a cloud VPS (e.g., DigitalOcean, AWS, Linode) triggers three critical failure modes:

1. **Datacenter IP WAF Blockade & SSL Handshake Quirks:**
   - Government and public e-procurement firewalls actively detect and block or challenge traffic originating from cloud datacenter ASNs.
   - Legacy cipher suites or strict cipher requirements on government web servers (e.g. `SSL: DH_KEY_TOO_SMALL`) frequently cause standard server-side curl/urllib connections from Linux datacenters to fail.
   - Conversely, residential ISP connections (home machines) browse cleanly without triggering WAF countermeasures or Cloudflare challenges.

2. **Heavy Single Page Application (SPA) Rendering & Resource Starvation:**
   - Modern procurement portals render dynamic content client-side via JavaScript frameworks (Vue/React).
   - Direct HTTP GET requests return empty skeleton HTML (`<div id="root"></div>`). Crawling requires running a real headless Chromium instance via Chrome DevTools Protocol (CDP).
   - Running Chrome CDP instances on a live production VPS hosting existing web services (e.g., e-commerce shop `doravo.net`) consumes 1–2 GB of RAM and spikes CPU, risking downtime for existing services.

3. **ChatGPT Tool Call Latency Limits (30–45s Timeout):**
   - A full sweep across 14 medical keywords and 3 bidding scopes (TBMT, YCBG, CGTTRG) requires 42 separate page evaluations, taking ~2.5 to 2.8 minutes.
   - ChatGPT strictly cuts off MCP tool calls if execution exceeds 30–45 seconds, resulting in immediate `Gateway Timeout (504)` or client-side abort errors.

---

## 2. The Decoupled CQRS Architecture (Command Query Responsibility Segregation)

To resolve the conflict between heavy scraping and sub-second ChatGPT responsiveness, the system is separated into two decoupled pipelines:

```
[MÁY NHÀ (Residential IP / Crawler)]
   ├─ Batch Scheduled Sweep (08:00, 13:30, 17:00 ~2.5m/run)
   ├─ On-demand Single-Bid Crawler (pulls specific IB2600xxxx in 3-5s)
   └─ Clean Data Sync (Push to VPS SQLite via SCP / Secure REST API)
                                 │
                                 ▼
[VPS DORAVO (FastMCP Query Server)]
   ├─ SQLite Cache (bidding_cache.db, WAL mode, query latency < 50ms)
   ├─ Nginx HTTPS Reverse Proxy (SSE no-buffering, keepalive 15s)
   └─ FastMCP Python Daemon (uvicorn, port 8100)
                                 │ (Real-time SSE Stream)
                                 ▼
[CHATGPT (Mobile App / Web - Mr. Nguyen)]
   └─ "Hôm nay có gói nào mới?" -> Trả lời trong 0.2s kèm nhãn thời gian
```

---

## 3. Data Freshness & Sweep Frequency Strategy

When clients ask: *"Is the data only updated once every 24 hours at 8:00 AM?"*, explain the dual-cadence model:

1. **Three Golden Batch Sweeps per Day (Tender Publication Cadence):**
   - Hospitals and bidding units publish notices during administrative office hours.
   - **08:00 AM:** Catches tenders published late previous afternoon/evening.
   - **13:30 PM:** Catches tenders published during the morning session.
   - **17:00 PM:** Catches final day-end releases before closing.
   - General inquiries (e.g. *"Any new tenders today?"*) read from the latest sweep cache in **0.2 seconds**, displaying an explicit timestamp: `(⏱ Dữ liệu cập nhật lúc 13:30 hôm nay: Có 1 gói đang mở...)`.

2. **Real-time On-demand Query (Specific Bid Codes):**
   - When a client wants to inspect an ad-hoc bid code (e.g. `IB2600553497` or `RQ2600056970`), the system triggers an immediate targeted fetch for that single dossier in **3–5 seconds** without waiting for the next batch schedule.

---

## 4. Scope Breadth: Universal National Search vs. Tailored Compliance

Clarify the two distinct operational tiers to users:
- **Tier 1 — Universal Public Bidding:** Any public tender across all industries (construction, IT, pharmaceuticals, general hospital equipment) can be retrieved and parsed by bid code or keyword.
- **Tier 2 — Tailored Compliance Engine:** Specialized, rule-based qualification is applied to the company's core product catalog (e.g. Trocar YCCMED 4 models: `5X100-6.0`, `10X100-11.11`, `12X100-13.0`, `15X100-16.0`), automatically evaluating blade, balloon, and dimension criteria without requiring generic third-party data services.
