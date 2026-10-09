# Kỷ Luật Tách Rời Workflow Cron: Gmail S7 -> GPM Login -> 2FA -> ChatGPT & TikTok (25/09/2026)

## 1. Bối cảnh & Các điểm nghẽn lịch sử đã xử lý
- **Mâu thuẫn 2FA trước Login GPM:** Từng có quan niệm ép bật 2FA trên S7 hoặc đòi hỏi tài khoản phải có 2FA mới cho login GPM. Thực tế chứng minh nhiều tài khoản Gmail chưa có 2FA vẫn login GPM thành công, trong khi cố bật 2FA trên S7 qua ADB hay dính WebView reCAPTCHA và timeout kéo dài.
- **Bẫy `NO_SESSION` khi bật 2FA trên GPM:** Gọi `setup_authenticator_for_profile()` khi profile GPM chưa từng đăng nhập Google thành công sẽ bị redirect về trang giới thiệu (`account/about/?hl=vi`), gây lỗi hàng loạt.
- **Bẫy ghép chuỗi sau ca trưa (`post_noon_chain_watchdog`):** Tự động gọi TikTok Add 2FA ngay sau Reg Gmail sau 15 giây khiến lỗi runner ở Phase 2 làm hỏng nhận diện trạng thái ca, đồng thời số liệu ChatGPT linked bị quy nạp sai vào kết quả Reg Gmail.

## 2. Kiến trúc State Machine & Luồng độc lập
```text
Reg Gmail trên S7
       ↓
Cooldown & Mailbox Health
       ↓
Login GPM (Proxy 4G tương ứng, CẤM bắt buộc 2FA)
       ↓
Verify Session Google trên GPM
       ├── Thành công → Bật Google Authenticator 2FA trên GPM
       └── Chưa có session → Đánh dấu PENDING_GPM_LOGIN_NO_SESSION, chờ ca tối
```

- **ChatGPT Link:** Xử lý độc lập qua `watchdog_link_chatgpt_idle.py`, ghi nhận telemetry riêng, không đánh đồng việc link fail là Gmail die.
- **TikTok Add 2FA:** Tách riêng thành lane độc lập (`--lane tiktok`), fail-fast khi runner khởi động lỗi, không nối đuôi tự động sau Reg Gmail.

## 3. Các quy chuẩn triển khai script
- `post_noon_chain_watchdog.py`:
  + Hỗ trợ tham số `--lane gmail|tiktok|all` (mặc định: `gmail`).
  + Không tự động gọi `run_tiktok_2fa_batch()` trong ca trưa mặc định.
  + Báo cáo ChatGPT linked tách biệt: `telemetry riêng, không suy ra từ Gmail`.
- `post_morning_gmail_2fa_watchdog.py`:
  + Kiểm soát qua `2FA-SOAK-GATE`: profile GPM phải có ít nhất 1 phiên nuôi thành công hoặc session hợp lệ mới được add 2FA.
  + Thiếu session: chuyển `PENDING_GPM_LOGIN_NO_SESSION`, không gọi setup 2FA.
- `post_evening_gpm_login_watchdog.py`:
  + Giữ nguyên `MAX_WORKERS = 5`.
  + Tuyệt đối không filter loại trừ account chưa có 2FA khỏi danh sách login.
