# Quy Trình Chạy Batch Bật 2FA TikTok & Lưu Ý Vận Hành

## 1. Nguồn Dữ Liệu Avatar & Báo Cáo
- **Dashboard SQLite `tiktok_tracker.db`**: Là nguồn dữ liệu chuẩn xác duy nhất để đánh giá nick đã có avatar (`has_avatar == 1`) hay chưa.
- **Crawler Re-scan**: Vì cron quét toàn farm chỉ chạy 1 lần lúc 07:00 sáng, mọi watchdog sau khi chạy batch avatar ban đêm BẮT BUỘC phải gọi `tiktok_account_tracker.py --machines <list>` để cập nhật snapshot SQLite trước khi chốt số liệu báo cáo.
- **Phân tách Host ID**: Tránh nhầm lẫn dải máy giữa Kibe (`may < 200`) và Admin (`may >= 200`), luôn dùng parameterized query khi truy vấn SQLite.
