GPM Local API (19995): tạo profile payload bắt buộc dùng 'Profile_name' (tránh lỗi NOT NULL SQLite); raw_proxy cấm prefix 'http://'/'socks5://' kẻo Chromium lỗi net::ERR_NO_SUPPORTED_PROXIES; Playwright Next.js form click tọa độ gõ delay 50ms chống timeout. Meta/Muse OIDC timeout chuyển hướng oidc/error; IP datacenter chặn tạo tài khoản ở bước ngày sinh.
§
Nạp Web (:20129): trần 2 acc/IP; pre-validate Graph; cấm base64. Acc lỗi set rate_limited_until UTC; disableSessionStickiness=true & failoverBeforeRetry=true. Nạp Gemini Web CDP lấy __Secure-1PSID kẹp proxy 1:1; Argon 4 pool map 'gemini-web'. Worker timeout 360s.
§
Watchdog UNPROVEN & drift giải quyết dứt điểm bằng Zero-Drift Shim (-B, 0x08000000, buffer P1 15m). M17: @lyhoan.music. Check nhả follow vuốt reload 3.5s.
§
Nối xích unified_patch_pipeline.py là ENTRYPOINT DUY NHẤT khi Fix Code: S0 RepoLock -> S1 Gate B Plan -> S2 Patch qua worker -> S3 Test -> S4 Canary Gate 6 -> S5 Hold MEDIA:. Rollback tự động; TLIS v1 plain JSON; closeout_v2.py (0.05s). Test web đổi cả GPM profile + proxy mới sạch; bám sát geo User chỉ định (Canada).
§
Khi user yêu cầu 'Fix đi' sau báo cáo cron/watchdog: Mặc định là SỬA SCRIPT qua unified_patch_pipeline (--no-canary bảo vệ ca nuôi); CẤM tự ý can thiệp soft-recovery/reboot máy thật.
§
Cấm tuyệt đối đọc openpyxl/Excel trong runner/scripts: 100% trích xuất mailbox/account/token qua DAL farm_db.py SQLite. Gate B Planner nạp full context <= 1500 dòng tránh Gemini Web ảo giác. Cấm nhận lỗi phân bua, tập trung cơ giới hóa.
§
Đổi Hotmail thay Gmail DIE cho TikTok S7: vào Settings > Account > User info > Thay đổi email (cấm Hủy liên kết), điền Hotmail sạch lấy OTP 2s; cấm đẩy >5 workers đồng thời kẻo TikTok bật Captcha trượt; tránh bẫy nhận nhầm Camera/LIVE overlay thành Captcha (bấm nút X đóng tại 102, 174); cập nhật DAL farm_db và mirror Excel trước khi gỡ Gmail DIE khỏi máy.
§
Proxy S7 Farm: S7 KO có Tailscale -> CẤM gán domain/IP Tailscale (tb.taadaa.click / 100.x) vào Excel kẻo rụng Wi-Fi; S7 bắt buộc trỏ LAN 192.168.110.2:10008..10035 (hoặc 202xx nếu R3G live). R3G OpenWrt: CẤM chạy trùng tailscaled ở cả init.d và rc.local đụng port 41641; CẤM đổi Excel trước khi WAN mở thật.