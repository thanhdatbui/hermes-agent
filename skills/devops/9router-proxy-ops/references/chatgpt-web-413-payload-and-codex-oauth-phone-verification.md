# ChatGPT Web HTTP 413 Payload Limit, Combo Fallback Hierarchy & Codex OAuth Phone Verification

## 1. Nguyên nhân sập chuỗi 4 tầng (Cascade Failure) và lỗi HTTP 413 trên ChatGPT Web
- **Bản chất trần Payload của ChatGPT Web (`chatgpt.com/backend-api/conversation`)**:
  - Giao thức web giả lập qua Cloudflare WAF giới hạn HTTP Request Body ở mức rất thấp (~500KB - 1MB hoặc vài chục nghìn ký tự).
  - Khi tác vụ Agentic (Hermes, Claude Code, Cline, OpenCode) mang vác System Prompt lớn, Tools schema đồ sộ và conversation context dài, payload JSON sẽ vượt ngưỡng này.
  - Khi đó, Cloudflare / OpenAI Web WAF chặn ngay lập tức từ rìa và trả về mã lỗi:
    `[413]: ChatGPT returned 413 — the request payload is too large for ChatGPT web's size limit...`
- **Tử huyệt khi đặt ChatGPT Web làm Fallback Tier 2 ngay sau Gemini Flash**:
  - Nếu Tier 1 (Gemini Flash) bị nghẽn Semaphore hoặc dính 429 rate limit, toàn bộ request agentic nặng sẽ tràn xuống Tier 2 (ChatGPT Web).
  - Kết quả: Hàng trăm đến hàng nghìn request dính 413 liên hoàn, gây nghẽn toàn bộ proxy và kéo theo các tier sau (OpenCode 403, Claude 429) sập theo.

## 2. Thứ tự phân tầng Combo chuẩn cho Worker (`omni-worker`)
Để tránh bão lỗi 413 làm sập proxy, combo `omni-worker` phải tuân thủ thứ tự:
1. **Tier 1 — `ag-gemini-pool-3` (AG Gemini Flash Pool)**: Xử lý nhanh, chi phí 0đ, tối ưu cho tác vụ thông thường.
2. **Tier 2 — `ag-claude` (AG Claude Sonnet 4.6)**: Bể hứng an toàn cho payload lớn. Claude Sonnet nuốt trọn context window dài, tool call phức tạp mà không bao giờ bị 413.
3. **Tier 3 — `chatgpt-web-pool` (ChatGPT Web Pool - Sol/Luna)**: Chỉ kích hoạt khi cả Gemini và Claude đều cạn quota. Tuyệt đối không để làm Tier 2 đón đầu payload agentic.
4. **Tier 4 — `omni-free` (Free Safety Net)**.

## 3. Phân biệt Codex CLI (Provider `codex`) vs ChatGPT Web (`chatgpt-web`)
- **Codex CLI (`api.openai.com` qua OAuth PKCE / refresh_token)**:
  - Dùng giao thức API chính thức, hỗ trợ context window 128K - 200K tokens, payload nhiều MB, không bao giờ bị lỗi 413.
  - **Cổng bắt buộc Phone Verification**: Khi chạy OAuth Codex trên tài khoản mới qua `https://auth.openai.com/oauth/authorize`, OpenAI chuyển hướng sang `https://auth.openai.com/add-phone`.
  - Tài khoản bắt buộc phải verify OTP SMS 1 lần mới được cấp quyền Developer OAuth Token (`offline_access`).
- **ChatGPT Web (`chatgpt-web`)**:
  - Dùng trực tiếp Google SSO trên web, không bắt buộc verify SĐT, lấy cookie `__Secure-next-auth.session-token`.
  - Phù hợp nhất cho: Review code ngắn (`review` combo), Audit scorecard (`sol_auditor.py`), lập plan kiến trúc (`sol_planner.py`).

## 4. Tự động hóa giải quyết Phone Verification bằng API 5sim
- **API 5sim (`https://5sim.net/v1/user/`)**:
  - Header: `Authorization: Bearer <API_KEY>`, `Accept: application/json`
  - Sản phẩm cho OpenAI: `openai`
  - Mua số: `GET /v1/user/buy/activation/{country}/{operator}/openai` (Ưu tiên: `usa/virtual63` giá ~0.15 RUB, success rate ~61%; hoặc `greece/virtual34`, `austria/virtual66`).
  - Polling SMS OTP: `GET /v1/user/check/{id}` -> trích xuất mã 6 số từ `sms[0].code`.
  - Hủy / Hoàn tiền nếu quá 2-3 phút không có code: `GET /v1/user/cancel/{id}`.
  - Báo số lỗi / bị OpenAI chặn: `GET /v1/user/ban/{id}`.
  - Hoàn tất giao dịch sau khi nhập code: `GET /v1/user/finish/{id}`.
