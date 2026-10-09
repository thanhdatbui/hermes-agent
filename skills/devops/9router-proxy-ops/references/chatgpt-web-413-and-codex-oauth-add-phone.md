# ChatGPT-Web vs Codex OAuth (HTTP 413 & add-phone Gate Pitfalls)

## 1. Bản chất HTTP 413 trên ChatGPT-Web (`chatgpt.com`)
- **Nguyên nhân**: `chatgpt-web` chạy qua endpoint reverse-engineered (`/backend-api/conversation`). WAF/Cloudflare phía trước đặt trần payload request cứng ở mức **~500KB - 1MB**.
- **Kịch bản sự cố**: Khi các model ở tầng trước (ví dụ Antigravity Gemini Flash) bị nghẽn semaphore/rate-limit 429, hệ thống cascade sang `chatgpt-web`. Các client agentic (Hermes, Cline, subagent) gửi payload chứa system prompt lớn, full tool schemas và context file nhiều turn làm kích thước body vượt trần -> nổ hàng loạt lỗi **HTTP 413 (Payload Too Large)** với latency 11s-15s.
- **Biện pháp khắc phục**:
  1. **Hạ vị trí ưu tiên**: Không để `chatgpt-web-pool` làm tầng hứng tải trực tiếp ngay sau Flash cho các agentic worker. Phải xếp sau các model nuốt context lớn (như AG Claude Sonnet hoặc Codex).
  2. **Thứ tự chuẩn cho `omni-worker`**:
     - Tier 1: `ag-gemini-pool-3` (AG Gemini 3.7 Flash)
     - Tier 2: `ag-claude` (AG Claude Sonnet 4.6 - nuốt payload lớn không lỗi 413)
     - Tier 3: `chatgpt-web-pool` (12-17 Live Accounts - Safety Net)
     - Tier 4: `omni-free` (Dự phòng)
  3. **Bật Compression**: Nếu bắt buộc gọi qua `chatgpt-web`, phải kích hoạt Caveman / Context Compression trong OmniRoute để nén prompt trước khi gửi lên.

## 2. Rào cản Phone Verification (`add-phone`) khi OAuth Codex CLI
- **Nguyên nhân**: Codex CLI kết nối qua OAuth 2.0 PKCE Developer (`https://auth.openai.com/oauth/authorize` với scope `openid profile email offline_access`). OpenAI áp chính sách chống lạm dụng nghiêm ngặt cho Developer API.
- **Hiện tượng**:
  - Tài khoản Google/Gmail đã đăng nhập và hoạt động bình thường trên ChatGPT Web (`chatgpt.com`).
  - Khi thực hiện OAuth Codex (`start-callback-server` + click chọn tài khoản tại `choose-an-account`), OpenAI ngay lập tức chuyển hướng sang:
    `https://auth.openai.com/add-phone (Cần có số điện thoại - OpenAI)`
- **Quy tắc điều phối**:
  - **Không cố gắng auto-click mù quáng**: Trang `add-phone` yêu cầu nhận và nhập OTP SMS từ số điện thoại thật.
  - Phân loại rõ ràng:
    1. Tài khoản ChatGPT Web thường: Chỉ cần Google SSO, không bắt buộc SĐT.
    2. Tài khoản Codex CLI: Bắt buộc số điện thoại đã verify. Nếu muốn cấp thêm account vào Codex pool, cần chuẩn bị SIM/OTP dịch vụ để vượt checkpoint `add-phone`, hoặc tái sử dụng các profile/account đã từng kích hoạt Codex CLI thành công.
