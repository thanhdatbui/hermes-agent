# GPMLogin & S7 ChatGPT Hybrid Login Architecture

## 1. Bản chất sự khác biệt: Google SSO vs Direct Email Password
- **Nick cũ (Legacy):** Được liên kết với OpenAI thông qua Google SSO ("Continue with Google"). Với nhóm này, khi mở profile GPM có sẵn Google Session Cookie (`SID`), Playwright chỉ cần chọn tài khoản trên Account Chooser là vào thẳng.
- **Nick mới (S7 Direct Reg):** Trên điện thoại Samsung S7, để chống Google ban tài khoản và khóa nick hàng loạt, hệ thống **TUYỆT ĐỐI CẤM Google SSO**. Thay vào đó, tài khoản được đăng ký với OpenAI bằng **Direct Email + Mật khẩu + Mã OTP gửi về hòm thư Gmail**.

## 2. Quy tắc Mật khẩu (Invariant Password Policy)
- **CẤM TUYỆT ĐỐI dùng mật khẩu cố định** (như `Taadaa@2026#` hay password mặc định): OpenAI dễ dàng nhận diện pattern mật khẩu giống nhau giữa các nick để quét ban hàng loạt.
- **DÙNG CHUNG EMAIL & PASSWORD GMAIL 100%:** Khi đăng ký ChatGPT trên S7 cũng như khi đăng nhập trên GPM, BẮT BUỘC lấy chính xác mật khẩu của Gmail đó từ Master Excel (Cột 3 / Password trong `master_gmail_manager.xlsx`).
- **Fail-Fast khi thiếu mật khẩu:** Nếu dữ liệu tài khoản không có mật khẩu, script phải dừng ngay với mã `MISSING_PASSWORD`, không được tự ý đặt mật khẩu ngẫu nhiên hoặc dùng fallback cố định.

## 3. Quy trình On-boarding & Hybrid Login trên PC (Playwright CDP)
Khi đưa tài khoản lên GPMLogin để lấy session ChatGPT-Web nạp vào OmniRoute `:20129`:

```text
               ┌──────────────────────────────────────────────┐
               │    Mở Profile GPM qua Remote Debugging CDP   │
               └──────────────────────┬───────────────────────┘
                                      │
                   Truy cập https://chatgpt.com/auth/login
                                      │
                 ┌────────────────────┴────────────────────┐
                 ▼                                         ▼
         [Tài khoản Cũ SSO]                        [Tài khoản Mới Direct]
                 │                                         │
        Continue with Google                     Nhập Email từ Excel
                 │                                         │
       Chọn tài khoản Google                               ▼
       (Account Chooser)                         Nhập Mật khẩu Gmail (Cột 3)
                 │                                         │
                 └────────────────────┬────────────────────┘
                                      │
                                      ▼
                        [Vào Dashboard ChatGPT.com]
                                      │
                     Trích xuất Session & Access Tokens:
               ├─ __Secure-next-auth.session-token (chatgpt-web)
               └─ /api/auth/session -> accessToken (codex)
                                      │
                                      ▼
                         Bắn POST lên OmniRoute API
                       (:20129/api/providers)
```

## 4. Phân vai độc lập giữa các Cron (Tránh chồng chéo)
1. **Ca tối (20:15 - 23:45) - `post_evening_gpm_login_watchdog.py`:**
   - Tập trung duy nhất vào việc **Đăng nhập Google & cấp quyền OAuth Antigravity** cho các nick chưa có trên OmniRoute.
   - Bỏ hoàn toàn logic tạo/xóa Profile (đã có `sync_gpm_lifecycle.py` lo vào 07:15 - 08:45).
   - Kiểm tra trực tiếp API OmniRoute `:20129` làm chuẩn duy nhất.
   - Ưu tiên cao nhất cho profile đã có sẵn Google Session Cookie (ăn ngay trong 10s, không checkpoint).
2. **05:00 AM mỗi sáng - `cron_chatgpt_web_pool_watchdog.py`:**
   - Chuyên trách kiểm tra sức khỏe và hồi sinh (self-healing) các connection đã nạp.
   - Nạp mới session ChatGPT-Web từ các profile đã có Google Session sang OmniRoute.
