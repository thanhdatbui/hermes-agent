# Kiến Trúc Đổi Info Hotmail Farm Qua GPMLogin (PC Host) — 2026-09-25

## 1. Nguyên nhân dừng vận hành luồng cũ trên Samsung S7
- **Tranh chấp Device Lock**: Script cũ (`cron_night_hotmail_security_watchdog.py`) chạy lúc 03:00 sáng trên điện thoại S7. Khung giờ này trùng với Ca 4 đêm và batch dọn cache TikTok (`end-of-day-clear-tiktok-cache`). Watchdog kiểm tra thấy máy bận nên bị `DeviceLockUnavailable` và hủy phiên liên tục.
- **Phần cứng S7 (2016) quá tải**: S7 RAM chỉ 4GB, chip Exynos 8890. Khi mở Chrome mobile tải trang web bảo mật Microsoft (`account.live.com/proofs/manage/additional`) thường xuyên bị OOM, crash Chrome, hoặc timeout kết nối.

## 2. Kiến trúc mới: Chuyển 100% lên GPMLogin / Playwright (PC Host)
- **Giải phóng thiết bị Farm**: S7 được giải phóng hoàn toàn 100% để chuyên tâm nuôi feed và upload TikTok, không phải gánh tác vụ trình duyệt nặng nề.
- **Chạy cuốn chiếu tự do**: Không phụ thuộc vào Device Lock của điện thoại S7, có thể chạy cuốn chiếu 24/7 bất kỳ lúc nào giữa các khung giờ trống của PC.
- **Đồng nhất IP & Chống Checkpoint**: Profile GPMLogin được cấu hình proxy Singbox tương ứng với máy đó (`192.168.110.2:20000+N`), đảm bảo IP đăng nhập Microsoft trùng khớp hoàn toàn với IP mà máy S7 đang dùng.
- **Tốc độ & Ổn định**: Trình duyệt Chromium trên PC host load trang trong 1-2s, DOM desktop ổn định, click chính xác các nút:
  1. Đổi mật khẩu mạnh mới (`gen_strong_password()`).
  2. Gỡ bỏ mail khôi phục của bên bán (nếu có).
  3. Bấm **"Sign out of everywhere"** (Đăng xuất khỏi mọi thiết bị) để đá session cũ của bên bán.
  4. Cập nhật mật khẩu mới vào Cột G (PASS MAIL) trong `taikhoan_dat_v2_updated .xlsx`.
