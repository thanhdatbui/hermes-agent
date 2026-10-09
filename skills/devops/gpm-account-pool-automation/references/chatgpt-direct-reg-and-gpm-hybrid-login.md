# ChatGPT Direct Email Registration on S7 & GPM Hybrid On-boarding

## 1. Bản chất kiến trúc & Bài học xương máu
- **CẤM DÙNG MẬT KHẨU CỐ ĐỊNH:** Tuyệt đối không dùng mật khẩu cố định (như `Taadaa@2026#`) khi đăng ký tài khoản ChatGPT qua hòm thư Gmail trên điện thoại Samsung S7. Dùng chung một mật khẩu cố định cho nhiều tài khoản sẽ tạo pattern cho OpenAI quét ban hàng loạt.
- **NGUYÊN TẮC BẮT BUỘC:** Mật khẩu ChatGPT **phải trùng khớp 100% với Mật khẩu của chính Gmail đó** (lấy từ Cột 3 / Password của `master_gmail_manager.xlsx`).
- **Fail-Fast Safety:** Nếu tài khoản không có mật khẩu trong Excel, script bắt buộc dừng ngay lập tức (`MISSING_PASSWORD`), không được tự sinh mật khẩu.

## 2. Quản lý dữ liệu Excel
- Không cần tạo thêm file hoặc thêm cột mật khẩu riêng cho ChatGPT. Mật khẩu Gmail chính là Mật khẩu ChatGPT.
- Đánh dấu tài khoản: Khi thiết bị S7 liên kết thành công qua OTP hòm thư Gmail, tự động ghi nhận cờ `CHATGPT_READY` vào Cột 14 (Ghi Chú) của `master_gmail_manager.xlsx` và cập nhật state JSON (`chatgpt_link_backlog_state.json`).

## 3. Luồng nạp Hybrid trên GPMLogin (PC)
Khi đưa tài khoản lên GPMLogin để lấy session token nạp vào OmniRoute (:20129):
1. **Nick cũ (Tạo bằng Google SSO từ trước):** Bấm nút "Continue with Google" -> chọn tài khoản Google trong Account Chooser -> vào thẳng dashboard.
2. **Nick mới (Tạo bằng Direct Email OTP trên S7):** 
   - Điền Email -> Bấm Tiếp tục.
   - Điền Password của Gmail -> Bấm Tiếp tục.
   - Tuyệt đối không bấm Google SSO để tránh tạo acc rác hoặc lệch phương thức đăng nhập.
3. **Trích xuất Token & Sync OmniRoute:**
   - Trích xuất `__Secure-next-auth.session-token` từ cookies -> sync `chatgpt-web` connection.
   - Gọi `/api/auth/session` lấy `accessToken` -> sync `codex` connection.

## 4. Phân vai độc lập giữa các Cronjob
- **Ca tối (20:15 - 23:45) - `post_evening_gpm_login_watchdog.py`:**
  - Tập trung 100% vào việc On-boarding: Đăng nhập Google trên GPM và OAuth Antigravity vào OmniRoute.
  - Phân loại 3 nhóm ưu tiên: (1) Sẵn Google Session Cookie -> Ăn ngay không checkpoint; (2) Có cờ `CHATGPT_READY` đã bồi trust; (3) Cooldown >= 24h.
  - KHÔNG gọi chéo luồng Dual OAuth nặng nề làm nghẽn tiến trình ca tối.
- **Sáng sớm (05:00 AM) - `cron_chatgpt_web_pool_watchdog.py`:**
  - Tự động quét kiểm tra liveness cho cả 2 pool: `antigravity` và `chatgpt-web`.
  - Tự động mở GPM hồi sinh các connection bị đứt session.
  - Tự động nạp mới các nick đã có Google Session từ ca tối hôm trước vào pool `chatgpt-web`.
