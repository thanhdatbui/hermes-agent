# Quy hoạch Cuốn Chiếu Ban Đêm (Bỏ Ca 4 Nuôi Acc), Chạy Avatar & 2FA Tới 05:15 Sáng và Trọng Tài Dọn Cache (15/10/2026)

## 1. Bối cảnh & Thay đổi Kiến Trúc Lịch Nuôi (Bỏ Ca 4 Đêm)
- **Lịch nuôi acc TikTok chính thức:** Đã bỏ hoàn toàn Ca 4 ban đêm (00:00 - 02:00). Farm vận hành theo chu kỳ 3 Ca x 2 Phiên/ngày:
  * Ca 1 (Sáng): Phiên 1 lúc `06:00`, Phiên 2 lúc `08:00` (kết thúc toàn bộ trước `09:30`).
  * Ca 2 (Trưa): Phiên 1 lúc `12:00`, Phiên 2 lúc `14:00` (kết thúc toàn bộ trước `15:30`).
  * Ca 3 (Tối): Phiên 1 lúc `18:00`, Phiên 2 lúc `20:00` (kết thúc toàn bộ trước `21:30`).
- **Khoảng rảnh khổng lồ ban đêm:** Từ `21:30` tối hôm trước đến `05:15` sáng hôm sau (~8 tiếng) được giải phóng toàn bộ tài nguyên thiết bị cho các tác vụ phụ trợ (Upload Avatar, Add 2FA TikTok).

## 2. Quy Tắc Cuốn Chiếu Liên Tục Né Giờ Nuôi (Rolling Continuous Window)
- **Hàm kiểm tra khung giờ an toàn (`is_safe_rolling_window`):**
  * Né 3 ca nuôi chính thức: `05:15 - 09:30`, `11:45 - 15:30`, `17:45 - 21:30`.
  * Khung rảnh ban ngày: `09:30 - 11:45` và `15:30 - 17:45`.
  * Khung rảnh ban đêm: `21:30 - 05:15` (chạy trọn vẹn qua mốc 5h sáng, dừng lúc 05:15 để tạo đệm 30-45 phút làm mát thiết bị trước Ca 1).

## 3. Trọng Tài Chống Va Chạm Với Cron Dọn Cache TikTok Cuối Ngày
- **Cron dọn cache (`cron_clear_tiktok_cache.py`):**
  * Chạy lúc `04:00` sáng (`0 4 * * *`).
  * Kiểm tra điều kiện: Ca 3 tối hôm trước đã xong (`yesterday_ca3_phien2` hoặc `yesterday_ca3`).
  * Khóa thiết bị qua `DeviceLock(serial, machine, project="clear-cache")`, hoàn tất sau 10-15 phút.
- **Hai tầng bảo vệ chống đụng độ cho Avatar & 2FA:**
  1. *Tầng 1 (Time-based Window):* `is_safe_rolling_window` chặn khung giờ `04:00 - 04:30`, nhường tuyệt đối cho dọn cache.
  2. *Tầng 2 (Process-liveness Lockout):* Hàm `is_clear_cache_active()` quét psutil tìm process `clear-tiktok-cache` hoặc `cron_clear_tiktok_cache`. Nếu phát hiện đang chạy ở bất kỳ thời điểm nào $\rightarrow$ lập tức return 0 / nhả khóa, cấm chạy đè.

## 4. Báo Cáo Định Kỳ 6H Về Farm Alert (Chống Spam & Xóa Nhãn Sai)
- **Nhịp báo cáo:** Thay vì báo lắt nhắt từng batch hoặc ngắt ca lúc 23:30, hệ thống chuyển sang nhịp định kỳ **mỗi 6H** (`00:00`, `06:00`, `12:00`, `18:00`) hoặc khi **hoàn tất 100%**.
- **Cấm gán nhãn gây hiểu nhầm:** Tuyệt đối không dùng cụm từ `"nhường lịch nuôi TikTok / lock tiến trình khác"` cho các tài khoản chưa kịp xử lý khi hết giờ. Thay bằng số liệu rõ ràng: `"• Còn lại: N tài khoản chưa up"`.
- **Silent Batch:** Giữa các khung 6H, cron chạy ngầm cuốn chiếu hoàn toàn im lặng trên stdout để giữ sạch kênh thông báo Telegram.
