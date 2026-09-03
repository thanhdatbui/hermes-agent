# Quy định về Đặt tên tiếng Việt, Quản lý Kho Mail Live & Khóa máy

## 1. Đặt tên hiển thị TikTok (User Directive 2026-08-23)
- Khi reg tài khoản TikTok hoặc đặt biệt danh mới cho nick: **Bắt buộc dùng tên tiếng Việt** (viết hoa chữ đầu, theo mapping âm hoặc danh sách tên tiếng Việt phổ biến). Tuyệt đối không để tên tiếng Anh hoặc chuỗi vô nghĩa.

## 2. Quản lý kho `gmail_clean_v2.xlsx` và Tracking `taikhoan_dat_v2_updated .xlsx`
- `gmail_clean_v2.xlsx` là **kho mail live**, tuyệt đối không xóa mail sau khi vừa reg TikTok xong.
- Quét check-live chỉ xóa mail khi: mail die/quarantine VÀ **chưa có ID TikTok** trong file tracking. Nếu đã có ID TikTok thì bắt buộc giữ lại để nuôi nick.
- Ghi tracking: ID TikTok phải nằm **cùng hàng với Email gốc** đã reg trong `taikhoan_dat_v2_updated .xlsx`.

## 3. Tương tác giữa Batch Reg và Cron Nuôi Acc
- Cron nuôi acc có cơ chế Lock-Aware tự kiểm tra `.codex/device-locks`.
- Khi máy bị lock bởi tiến trình reg, cron nuôi sẽ ghi log `SKIPPED_DEVICE_LOCKED` và chỉ bỏ qua **đúng 1 phiên nuôi** đó của máy, không chạy đè và không gây xung đột tiến trình.
