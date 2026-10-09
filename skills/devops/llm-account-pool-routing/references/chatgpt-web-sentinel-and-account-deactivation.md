# ChatGPT-Web Sentinel 403, Account Deactivation & OAuth Checkpoint Triage

## 1. Triệu chứng & Phân loại lỗi (Evidence Classifications)

| Mã lỗi / Hiện tượng | Bằng chứng thực tế | Bản chất kỹ thuật | Hành động chuẩn |
| :--- | :--- | :--- | :--- |
| **Sentinel 403** | `[403]: ChatGPT blocked the request (Sentinel/Turnstile required)` | Cloudflare Turnstile / OpenAI Sentinel PoW (`/backend-api/sentinel/chat-requirements/prepare`) phát hiện bất thường về TLS fingerprint (JA3/JA4) hoặc thiếu token PoW. | **Quarantine >= 24h**. CẤM retry dồn dập khiến nick bị đưa vào danh sách đen. |
| **Payload 413** | `[413]: ChatGPT returned 413 — request payload too large` | Request gửi context vượt giới hạn Web UI (thường do agentic client xả system prompt / file lớn). | Bật context compression hoặc giới hạn max input tokens. |
| **Auth 401** | `[401]: ChatGPT auth failed — re-paste your session-token` | Session cookie `__Secure-next-auth.session-token` hết hạn tự nhiên hoặc bị OpenAI logout. | Mở GPM profile, thực hiện Google OAuth re-login để lấy cookie mới. |
| **Account Banned / Deactivated** | Redirect `https://auth.openai.com/error?payload=...` hiện: *"Bạn không có tài khoản vì tài khoản đã bị xóa hoặc vô hiệu hóa"* | OpenAI đã xóa hoặc khóa vĩnh viễn tài khoản do vi phạm ToS (lạm dụng reverse-engineered API / botting). | **Xóa dứt điểm khỏi OmniRoute** qua `DELETE /api/providers/{id}`, dọn combo, KHÔNG thử lại. |
| **Google Phone Checkpoint** | OCR trên `oauth_err_*.png` hiện: *"Enter a phone number to get a text message with a verification code"* | Google kích hoạt checkpoint bảo mật bắt xác minh SĐT khi OAuth Antigravity từ IP mới/bất thường. | **Dừng khẩn cấp (Fail-Safe)**, không spam nhập SIM bừa bãi, ngâm proxy 24-48h. |

---

## 2. Nguyên nhân cốt lõi khiến tài khoản ChatGPT Web bị khóa

1. **Ép tài khoản Free gánh model nặng liên tục:**
   - Các dòng model suy luận sâu như `gpt-5.6-sol-high` bị OpenAI giám sát rate-limit và gian lận khắt khe nhất.
   - Tài khoản Free nếu bị router dồn request reasoning liên tục sẽ bị gắn cờ lạm dụng tài nguyên.
2. **Kích thước request bất thường:**
   - Người dùng web thông thường chỉ gõ vài trăm ký tự.
   - Agentic pipelines gửi hàng chục ngàn tokens/turn liên tục làm thuật toán Anti-Abuse của OpenAI nhận diện bot ngay lập tức.
3. **Lệch vân tay trình duyệt & Nhân Chromium cũ:**
   - Các profile GPM chạy nhân Chromium cũ (ví dụ Chromium Core 127) mang User-Agent lỗi thời.
   - Khi kết hợp với proxy di động 4G và gọi backend ngầm, điểm tín nhiệm Cloudflare (Trust Score) bị hạ thấp nghiêm trọng.

---

## 3. Quy trình vận hành an toàn cho ChatGPT-Web Pool

1. **Phân cấp tải (Model Routing Policy):**
   - Tài khoản Free chỉ nên gánh các model nhẹ (`luna-free`, general task).
   - Hạn chế route các task audit/reasoning khổng lồ vào tài khoản Free đơn lẻ.
2. **Xử lý khi tài khoản DIE / Banned:**
   - **Bước 1 (Dọn Combo):** Lọc bỏ `connectionId` khỏi `models` trong bảng `combos` (`chatgpt-web-pool`, `gpt-web-sol`, `gpt-web-luna`).
   - **Bước 2 (Xóa Connection):** Gọi API `DELETE /api/providers/{id}` để xóa sạch khỏi `provider_connections`.
   - **Bước 3 (Ghi nhận Archive):** Cập nhật trạng thái vào `master_gmail_manager.xlsx` (sheet `Gmail_DIE_Archive`) để watchdog không quét rác.
3. **Reconcile Profile GPM trùng:**
   - Mở từng profile qua CDP, kiểm tra `myaccount.google.com` (xác thực email chính chủ) và `chatgpt.com` (kiểm tra cookie `has_session=True`).
   - Giữ lại duy nhất profile sống chuẩn + đúng proxy.
   - Xóa các profile rác còn lại bằng lệnh chuẩn: `GET /api/v3/profiles/delete/{id}?mode=1`.
