# Codex OAuth Phone Verification, SMS Fallback & OmniRoute 48h Soak Strategy

## 1. Bản chất cơ chế OpenAI OAuth Codex CLI & Phone Challenge
- Khi gọi OAuth Authorize cho Codex CLI (`auth.openai.com/oauth/authorize?client_id=app_EMoamEEZ73f0CkXaXp7hrann...`), OpenAI áp dụng policy bảo mật cao hơn web thông thường.
- Ngay cả khi profile GPM đã đăng ký ChatGPT bằng Email + OTP và có session sống, khi bấm ủy quyền sang Codex CLI, OpenAI vẫn kích hoạt chốt chặn **Add Phone Number (`https://auth.openai.com/add-phone`)**.
- **Tuyệt đối cấm dùng Google SSO để đăng nhập:** Khi gặp form đăng nhập, cấm bấm "Continue with Google" vì OpenAI sẽ coi đây là liên kết tài khoản mới từ IP lạ và bắt buộc challenge phone/captcha nặng nề hơn. Bắt buộc 100% Direct Email + OTP/Password.

## 2. Chiến lược thuê số SMS 5sim tối ưu chi phí & tỉ lệ thành công
- **Khoảng giá chấp nhận:** Loanh quanh $0.05 - $0.12 (tỉ lệ nhận SMS trên 20% - 30% là đạt chuẩn kinh tế).
- **Thứ tự ưu tiên quốc gia / nhà mạng:**
  1. **Việt Nam (+84):** `virtual47` / `virtual34` (~0.10$ - 0.12$). Tỉ lệ ~28%.
  2. **Argentina (+54):** `virtual62` (~0.05$). Rất rẻ, tỉ lệ ~30%.
  3. **Philippines (+63):** `virtual58` (~0.10$ - 0.11$). Tỉ lệ ~26%.
  4. **Anh (England +44):** `virtual34` (~0.128$). Tỉ lệ ~39%.
  5. **Thái Lan (+66):** `virtual34` (~0.083$). Tỉ lệ ~17%.
- **Quy tắc thực thi (Loop retry không dừng báo vặt):**
  - Khi thuê một số, nếu OpenAI từ chối số ("Invalid / already linked") hoặc sau 90s không thấy SMS nhả về:
    - **Lập tức gọi API `cancel_number(order_id)`** để 5sim hoàn lại 100% tiền vào số dư.
    - **Tự động bốc tiếp số kế tiếp theo chuỗi fallback giá rẻ**, không dừng script để báo lỗi hay hỏi user khi chưa hết vòng lặp attempts.

## 3. Chiến thuật Deactivate trên OmniRoute & Kích hoạt sau 48h ngâm
- **Vấn đề:** Tài khoản mới reg vừa cấp OAuth token xong nếu đưa vào pool OmniRoute gọi API dồn dập ngay sẽ bị OpenAI quét bất thường (Velocity / Risk Score check), dễ bị revoke token hoặc khóa session.
- **Giải pháp tối ưu:**
  1. Ngay khi nhận được `connection_id` từ callback port 1455:
     ```python
     # Tự động tạm tắt trong C:\Users\Kibe\.omniroute\storage.sqlite
     cur.execute("UPDATE provider_connections SET is_active = 0 WHERE id = ?", (connection_id,))
     ```
  2. Lưu timestamp `codex_oauth_at` vào file trạng thái `batch_gpm_5profiles_supervisor_state.json`.
  3. Cronjob định kỳ mỗi giờ (`cron_omni_activate_soaked_codex.py`):
     - Quét các connection Codex có `is_active = 0`.
     - Nếu đã ngâm đủ $\ge 48$ tiếng từ `codex_oauth_at` $\rightarrow$ Tự động chạy `UPDATE provider_connections SET is_active = 1 WHERE id = ?`.
     - Tài khoản gia nhập pool làm việc bền vững và ổn định lâu dài.
