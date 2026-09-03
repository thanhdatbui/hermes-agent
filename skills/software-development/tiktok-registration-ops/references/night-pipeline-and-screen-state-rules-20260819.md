# TikTok Registration Night Pipeline & Operational Invariants (2026-08-19)

## 1. Chuỗi tự động Ban đêm (Chained Night Pipeline)
- **Lịch chạy:** 00:00 hàng ngày qua Hermes Cron (`night-chain-reg-gmail-tiktok`, ID: `38ea60c09825`).
- **Luồng:**
  1. `run_all.ps1` (`register gmail`): Chạy batch reg Gmail (áp dụng cooldown >= 5 ngày, max 15 máy).
  2. `_run_all_targets.py` (`Tiktok_Reg`): Tự động lấy danh sách Gmail mới từ `gmail_clean_v2.xlsx` gán cho các máy thiếu acc trên `taikhoan_dat_v2_updated .xlsx` để reg TikTok.
  3. Báo cáo tổng kết gửi thẳng vào nhóm Telegram **`Gmai reg`** (`-5139245637`).

## 2. Quy tắc về Trạng thái Thiết bị
- **SUCCESS:** Script tự động dọn dẹp app, đưa thiết bị về màn hình Home.
- **FAILED / Kẹt lỗi:** Giữ nguyên hiện trường trên màn hình máy, không tự ý bấm Home để phục vụ kiểm tra/debug sau.
- **Không chế bước dọn dẹp trước ca nuôi:** Ca nuôi acc (TikTok feed) 06:00 vốn đã có sẵn bước preflight tự động dọn app rác và đưa máy về Home trước khi swipe.

## 3. Lọc Nguồn Gmail Sạch
- `gmail_clean_v2.xlsx` chỉ chứa các mail đã đăng ký thành công và xác thực xong.
- Script `_detect_clean.py` chỉ việc so khớp bốc mail chưa có trong `taikhoan_dat_v2_updated .xlsx`, không cần kiểm tra Inbox rườm rà.
