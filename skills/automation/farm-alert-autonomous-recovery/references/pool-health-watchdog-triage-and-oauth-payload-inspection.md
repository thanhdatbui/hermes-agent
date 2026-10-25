# Pool Health Watchdog Triage, OAuth Payload Inspection & Visual Evidence

> Kinh nghiệm vận hành và triage tự động cho Pool Healer Watchdog (`chatgpt-web-pool-healer-watchdog`), xử lý sự cố ChatGPT-Web, Codex OAuth và Antigravity trên OmniRoute (:20129) và GPM (:19995).

---

## 1. Phân Loại Cảnh Báo Watchdog (Pool Healer Alert Categories)
Khi nhận cảnh báo từ watchdog `chatgpt-web-pool-healer-watchdog`, phân loại ngay theo 3 nhóm độc lập trước khi quyết định can thiệp:
1. **ChatGPT-Web (`Validate fail: EMPTY_SESSION_TOKEN`)**: Watchdog khởi động profile GPM qua CDP (`/api/v3/profiles/start/{pid}`), kiểm tra cookie `__Secure-next-auth.session-token`. Thất bại khi cookie rỗng, trang chưa đăng nhập hoặc gặp lỗi mạng.
2. **Codex OAuth (`Timeout OAuth sau 90s` / `401_token_revoked`)**: Token upstream bị thu hồi hoặc hết hạn, watchdog chạy quy trình cấp lại OAuth qua callback server cổng `1455`. Thất bại khi kẹt tại màn hình chuyển hướng bên thứ 3.
3. **Antigravity Pro Tier (`g1-pro-tier`)**: Tài khoản Pro bị rớt trạng thái active hoặc lỗi refresh token Google Cloud.

---

## 2. Trích Xuất & Giải Mã Base64 Payload Trên URL Lỗi OpenAI
Khi Codex OAuth chuyển hướng về URL lỗi của OpenAI:
```
https://auth.openai.com/error?payload=<base64_string>&...
```
- **Kỹ thuật trích xuất:** Tách lấy tham số `payload=`, chuẩn hóa padding `=` (bội số 4) và giải mã bằng `base64.b64decode(payload)`.
- **Ví dụ thực tế:**
  - Chuỗi: `eyJlcnJvckNvZGUiOiAiYWNjb3VudF9kZWFjdGl2YXRlZCJ9`
  - Giải mã JSON: `{"errorCode": "account_deactivated"}`
- **Phán quyết vận hành O(1):**
  - Khi gặp `account_deactivated`: Đây là bằng chứng xác thực từ upstream OpenAI rằng tài khoản đã bị đóng/banned vĩnh viễn.
  - **Hành động ngay:** Đánh dấu tài khoản `DEAD` trong database/lifecycle, xác nhận `is_active = 0` trên OmniRoute để loại bỏ hoàn toàn khỏi luồng điều phối routing.
  - **CẤM:** Không được tiếp tục retry OAuth lặp đi lặp lại vì sẽ gây lãng phí 90s timeout mỗi lần quét và sinh rác trong telemetry.

---

## 3. Phân Biệt Lỗi Vòng Đời (Lifecycle Staging) vs Mất Session Thật Sự
Khi tài khoản Hotmail/Gmail bị báo `Validate fail: EMPTY_SESSION_TOKEN`:
- **Kiểm tra trạng thái Supervisor:** Trước khi coi đây là lỗi session bị mất, BẮT BUỘC đọc file state của supervisor (`D:/Taadaa/runtime/kibe/cron-state/batch_gpm_5profiles_supervisor_state.json`).
- **Quy tắc đối soát:**
  - Nếu tài khoản đang ở `stage: "HOTMAIL_LOGIN"` và `status: "PENDING"`: Tài khoản này mới chỉ ở bước đăng nhập mail, **chưa từng thực hiện đăng ký ChatGPT Web** (`stage: CHATGPT_REG`).
  - Do chưa có tài khoản ChatGPT, việc watchdog báo `EMPTY_SESSION_TOKEN` là **hoàn toàn chính xác theo vòng đời**, không phải lỗi bất thường.
  - **Xử lý:** Giữ nguyên `is_active = 0` trên OmniRoute, để tiến trình supervisor cuốn chiếu tự động hoàn tất đăng ký ChatGPT khi đến lượt.

---

## 4. Invariant Soi Mắt Đọc Ảnh GPM (`browser_navigate` + `browser_vision`)
Trước khi gửi bất kỳ thẻ ảnh `MEDIA:<path>` nào cho User theo Invariant Soi Mắt Đọc Ảnh:
1. **Nạp ảnh cục bộ qua Browser:**
   - Dùng `browser_navigate(url="file:///D:/Taadaa/GPM%20auto/debug_screenshots/<screenshot_name>.png")`.
2. **Soi mắt bằng Native Vision:**
   - Gọi `browser_vision(annotate=false, question="...")` để đọc trực tiếp nội dung màn hình.
3. **Phân loại hiện trường:**
   - **Ảnh đen / rỗng (< 2.5 KB):** Trình duyệt Chromium chưa kịp render frame đầu tiên (thường gặp khi profile GPM chạy nền hoặc scale nhỏ `win_scale=0.8`). CẤM gửi ảnh này làm bằng chứng.
   - **Ảnh lỗi mạng (`ERR_CONNECTION_RESET` / `ERR_PROXY_CONNECTION_FAILED`):** Chứng minh trực quan cổng proxy của profile bị ngắt kết nối (ví dụ cổng proxy 5115 reset kết nối khi tải `chatgpt.com/auth/login`). Phản hồi rõ ràng nguyên nhân là mạng/proxy.
   - **Ảnh Challenge / Checkpoint:** Phát hiện màn hình captcha, số điện thoại hoặc yêu cầu xác thực bảo mật 2FA.

---

## 5. Phân Biệt Google SSO Federation vs Direct Auth Trong Codex OAuth
- Khi tài khoản OpenAI được đăng ký qua Google SSO, việc gõ email vào ô input của OpenAI sẽ tự động kích hoạt redirect sang Google:
  `https://accounts.google.com/v3/signin/identifier?opparams=...`
- **Tử huyệt của Automation Script:**
  - Các script chỉ tìm nút submit của OpenAI (`button:has-text("Continue")`, `button[type="submit"]`) sẽ không thể tương tác với form v3 của Google (nút `#identifierNext`, `#passwordNext` hoặc chữ tiếng Việt "Tiếp theo").
  - Dẫn đến việc browser dừng lại ở trang Google cho tới khi chạm trần timeout 90s.
- **Triage:** Phân loại đúng đây là sự cố chuyển hướng Google SSO cần bổ sung handler Google Sign-in / 2FA, không nhầm lẫn với lỗi crash mạng hay tài khoản bị khóa.
