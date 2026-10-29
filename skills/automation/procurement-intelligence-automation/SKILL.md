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

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
