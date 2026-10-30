GPM Local API (19995): tạo profile payload bắt buộc dùng 'Profile_name' (tránh lỗi NOT NULL SQLite); raw_proxy cấm prefix 'http://'/'socks5://' kẻo Chromium lỗi net::ERR_NO_SUPPORTED_PROXIES; Playwright Next.js form click tọa độ gõ delay 50ms chống timeout. Meta/Muse OIDC timeout chuyển hướng oidc/error; IP datacenter chặn tạo tài khoản ở bước ngày sinh.
§
Nạp Web (:20129): trần 2 acc/IP; pre-validate Graph; cấm base64. Acc lỗi set rate_limited_until UTC; disableSessionStickiness=true & failoverBeforeRetry=true. Nạp Gemini Web CDP lấy __Secure-1PSID kẹp proxy 1:1; Argon 4 pool map 'gemini-web'. Worker timeout 360s.
§
Watchdog UNPROVEN & drift giải quyết dứt điểm bằng Zero-Drift Shim (-B, 0x08000000, buffer P1 15m). M17: @lyhoan.music. Check nhả follow vuốt reload 3.5s.
§
Nối xích unified_patch_pipeline.py là ENTRYPOINT DUY NHẤT khi có lệnh Fix Code / Fix lỗi: S0 Precheck RepoLock -> S1 Plan (Gate B) -> S2 Patch qua dispatch_worker -> S3 Test -> S4 Canary Gate 6 -> S5 Hold Awaiting User kèm MEDIA:. Lỗi tự full_rollback(). BỎ HẲN HMAC/SHA256 ký local; dùng TLIS v1 (Plain JSON, atomic os.replace, OS RepoLock). Chốt phiên User gõ 'Done' chạy closeout_v2.py (0.05s). Bị chặn/fail phải ném log thật. CẤM làm tay. Đổi acc reg/test web (Muse AI, Meta) BẮT BUỘC đổi cả profile GPM và proxy mới để cách ly sạch, cấm tái sử dụng profile dính vết; kiên định bám sát geolocation User chỉ định (Canada).
§
Đã chuyển đổi 100% dữ liệu Excel sang SQLite D:/Taadaa/data/farm_master.db (160 máy, 1.270 nick, 1.455 mail, 806 token). Flow chính dùng DAL farm_db.py; Web kibe:1905 có tab Sổ Cái riêng biệt ở đầu trang, phân định rõ 🔑 2FA TT (TikTok cột trái) và 🔑 2FA Mail (Mailbox cột phải, 160 acc), cấm nhãn 2FA chung chung.
§
Quy tắc đổi nick/proxy GPM: Đổi acc mới hoặc đổi proxy bắt buộc tạo profile mới toanh; cấm dùng lại profile cũ dính vết fingerprint/tokens tránh bị kích hoạt chối bỏ đăng ký tự động.
§
Farm có hơn 880 hòm thư Hotmail/Outlook trong bảng mailboxes (farm_master.db) có sẵn oauth_refresh_token; luôn tự động đổi access_token qua login.live.com và gọi Microsoft Graph API (inbox/junkemail) trích xuất OTP 6 số tự động trong 2 giây; cấm dừng lại hỏi xin mail cá nhân của user.