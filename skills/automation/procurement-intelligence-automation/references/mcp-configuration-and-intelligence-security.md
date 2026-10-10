# MCP Integration, Security Analysis & Client Messaging Guide

## 1. ChatGPT Plugin / Custom MCP Configuration Diagnostics

### Symptom & Error
- When attempting to configure a custom plugin/MCP in ChatGPT (`chatgpt.com/plugins` / Settings -> Developer mode):
  - Field `Tên`: e.g. `Bid Intelligence`
  - Field `Kết nối (URL server)`: Filled with regular web domain `https://muasamcong.mpi.gov.vn`
  - Modal displays red error:
    > *"Không thể tự động xác định cài đặt OAuth. Hãy kiểm tra URL máy chủ hoặc nhập cài đặt theo cách thủ công"*
    > *(Cannot automatically determine OAuth settings. Check server URL or enter settings manually)*
  - Button `Tạo dưới dạng plugin` remains disabled / fails to submit.

### Root Cause
- The user/client confuses a standard website (`muasamcong.mpi.gov.vn`) with an MCP server endpoint.
- An MCP server implements JSON-RPC / Server-Sent Events (SSE) protocol (e.g. `https://dauthau.anovatech.vn/mcp`).
- Standard web portals lack MCP headers, manifest, and OAuth endpoints required by the MCP client.

### Immediate 10-Second Remediation
1. In `URL server`, replace `https://muasamcong.mpi.gov.vn` with the actual MCP endpoint: `https://dauthau.anovatech.vn/mcp` (or the private MCP endpoint).
2. Click `Tạo dưới dạng plugin`.
3. In the OAuth popup, log in with credentials from the service provider.

---

## 2. Competitive Intelligence & Security Assessment (3rd-Party MCP vs. Private)

### Why 3rd-Party Bidding MCPs (Anovatech / dauthau.info) Pose Severe Risks:
1. **Intelligence Interception:**
   - Commercial data vendors earn revenue selling tender data and market insights.
   - When a contractor feeds technical queries (e.g. Trocar diameters, stapler reloads, hospital names, target budgets) into ChatGPT via a 3rd-party MCP, the broker's proxy inspects all search intents.
   - The broker knows in real time which tenders the contractor is preparing to bid on.
2. **Commercialization of Bidding Intent:**
   - Competitors can purchase specialized reports showing active interest and bidding patterns.
   - In medical device procurement (e.g. Trocar YCCMED), leaking technical matching strengths/weaknesses gives competitors advance notice to challenge bid criteria.

---

## 3. Crawler Bot vs. Private MCP Server Comparison

- **Crawler Watchdog (Telegram push):**
  - Best for daily hands-free monitoring at 0 token cost.
  - Runs in Guest mode on `muasamcong.mpi.gov.vn` to avoid 24h token expiry and 2FA interruptions.
  - Drawback: 1-way text report; user cannot ask follow-up questions.
- **Private MCP Server (ChatGPT integration):**
  - Exposes an internal API via MCP protocol directly into the user's mobile ChatGPT app.
  - Enables 2-way conversational exploration: *"Hôm nay có gói nào mới?", "Lập bảng so sánh gói BV Nguyễn Trãi xem có khớp hàng YCCMED không?"*.
  - Keeps all business intent inside company-controlled servers.

---

## 4. Client Communication Playbook

When drafting messages for the operator to copy-paste to clients/partners:
- **Tone:** Direct, polite, concise (Vietnamese).
- **Format:** Maximum 3 bullet points. Step 1 (exact URL), Step 2 (action button), Step 3 (login popup).
- **Follow-up:** 1 concise sentence proposing the private MCP server alternative if they prefer interactive ChatGPT view.
